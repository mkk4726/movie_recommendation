"""
포스터 의미 검색 파이프라인 (CLIP + Qdrant).
텍스트 쿼리와 시각적으로 유사한 포스터를 가진 영화를 검색합니다.
"""

import logging
from typing import List, Optional

import pandas as pd

from core.db.data_access import load_movie_data, load_cast_data

logger = logging.getLogger(__name__)


class PosterSearchPipeline:
    """CLIP 기반 포스터 검색 파이프라인."""

    def __init__(self):
        self._clip = None
        self._cast_grouped = None

    def _ensure_clip_loaded(self):
        if self._clip is not None:
            return
        logger.info("PosterSearchPipeline: CLIP 파이프라인 로딩 중...")
        from core.modeling.models.clip.text_to_poster_search import TextToPosterSearchPipeline
        from core.vector_store.utils.config import (
            get_clip_enable_translation,
            get_clip_model_key,
            load_config,
        )
        config = load_config()
        self._clip = TextToPosterSearchPipeline(
            model_key=get_clip_model_key(config),
            enable_translation=get_clip_enable_translation(config),
        )
        logger.info("PosterSearchPipeline: CLIP 파이프라인 로딩 완료")

    def _ensure_cast_loaded(self):
        if self._cast_grouped is not None:
            return
        cast_df = load_cast_data()
        self._cast_grouped = cast_df.groupby("imdb_id")

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[dict] = None,
        include_cast: bool = True,
    ) -> List[dict]:
        """
        텍스트 쿼리로 포스터를 검색하고 영화 메타데이터를 포함하여 반환합니다.

        Args:
            query: 검색 텍스트 (한국어 자동 번역 지원)
            top_k: 반환할 결과 수
            filters: {'min_rating', 'min_vote_count', 'genre', 'language'}
            include_cast: 출연진 정보 포함 여부

        Returns:
            영화 메타데이터 dict 리스트 (PosterSearchResultMovie 필드와 호환)
        """
        self._ensure_clip_loaded()
        df_movies = load_movie_data()

        filter_ids = _build_filter_ids(df_movies, filters) if filters else None
        if filter_ids is not None and len(filter_ids) == 0:
            return []

        raw = self._clip.search(query=query, top_k=top_k, filter_movie_ids=filter_ids)

        if include_cast:
            self._ensure_cast_loaded()

        return _enrich(raw, df_movies, self._cast_grouped if include_cast else None)


def _build_filter_ids(df: pd.DataFrame, filters: dict) -> Optional[List[str]]:
    if not filters:
        return None
    result = df.copy()

    if filters.get("min_rating", 0) > 0 and "vote_average" in result.columns:
        result = result[result["vote_average"] >= filters["min_rating"]]
    if filters.get("min_vote_count", 0) > 0 and "vote_count" in result.columns:
        result = result[result["vote_count"] >= filters["min_vote_count"]]
    if filters.get("genre"):
        genre_col = "genres_tmdb" if "genres_tmdb" in result.columns else "genres"
        result = result[
            result[genre_col].apply(
                lambda x: any(g in str(x) for g in filters["genre"]) if pd.notna(x) else False
            )
        ]
    if filters.get("language") and "language" in result.columns:
        result = result[result["language"].isin(filters["language"])]

    return result["movie_id"].astype(str).tolist()


def _enrich(raw_results: list, df_movies: pd.DataFrame, cast_grouped) -> List[dict]:
    movies_index = df_movies.copy()
    movies_index["movie_id_str"] = movies_index["movie_id"].astype(str)
    movies_dict = movies_index.set_index("movie_id_str").to_dict("index")

    results = []
    for item in raw_results:
        movie_id = item.get("movie_id")
        score = item.get("score", 0.0)
        data = movies_dict.get(movie_id)
        if not data:
            logger.warning(f"영화 ID {movie_id}를 데이터에서 찾을 수 없습니다.")
            continue

        poster_url = None
        if pd.notna(data.get("poster_path")):
            poster_url = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"

        cast_info = None
        if cast_grouped is not None:
            imdb_id = data.get("imdb_id")
            if imdb_id and pd.notna(imdb_id):
                cast_info = _get_cast_info(imdb_id, cast_grouped)

        results.append({
            "movie_id": movie_id,
            "score": score,
            "title": data.get("total_title") or data.get("title"),
            "genres": data.get("genres_tmdb") or data.get("genres"),
            "year": int(data["year"]) if pd.notna(data.get("year")) else None,
            "overview": data.get("overview") if pd.notna(data.get("overview")) else None,
            "poster_url": poster_url,
            "cast_info": cast_info,
            "imdb_id": data.get("imdb_id") if pd.notna(data.get("imdb_id")) else None,
            "release_date": data.get("release_date") if pd.notna(data.get("release_date")) else None,
            "vote_average": float(data["vote_average"]) if pd.notna(data.get("vote_average")) else None,
            "vote_count": int(data["vote_count"]) if pd.notna(data.get("vote_count")) else None,
            "adult": bool(data["adult"]) if pd.notna(data.get("adult")) else None,
            "language": data.get("language") if pd.notna(data.get("language")) else None,
        })

    return results


def _get_cast_info(imdb_id: str, cast_grouped):
    """MovieCastInfo Pydantic 객체 반환 (lazy import)."""
    from app.api.schemas import CastMember, MovieCastInfo

    try:
        movie_cast = cast_grouped.get_group(imdb_id)
    except KeyError:
        return MovieCastInfo()

    if movie_cast.empty:
        return MovieCastInfo()

    actors_data = movie_cast[movie_cast["known_for_department"] == "Acting"].sort_values("cast_id").head(5)
    actors = [
        CastMember(
            name=row["name"],
            original_name=row["original_name"],
            character=row["character"] if pd.notna(row["character"]) else None,
            profile_path=row["profile_path"] if pd.notna(row["profile_path"]) else None,
        )
        for _, row in actors_data.iterrows()
    ]

    directors_data = movie_cast[movie_cast["known_for_department"] == "Directing"].sort_values("cast_id")
    directors = [
        CastMember(
            name=row["name"],
            original_name=row["original_name"],
            character=None,
            profile_path=row["profile_path"] if pd.notna(row["profile_path"]) else None,
        )
        for _, row in directors_data.iterrows()
    ]

    writers_data = movie_cast[movie_cast["known_for_department"] == "Writing"].sort_values("cast_id")
    writers = [
        CastMember(
            name=row["name"],
            original_name=row["original_name"],
            character=None,
            profile_path=row["profile_path"] if pd.notna(row["profile_path"]) else None,
        )
        for _, row in writers_data.iterrows()
    ]

    return MovieCastInfo(actors=actors, directors=directors, writers=writers)
