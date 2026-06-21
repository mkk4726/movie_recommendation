"""
포스터 의미 검색 파이프라인 (CLIP + Qdrant).
텍스트 쿼리와 시각적으로 유사한 포스터를 가진 영화를 검색합니다.
"""

import logging
from typing import List, Optional

import pandas as pd

from core.db.data_access import load_cast_data, load_movie_data
from core.modeling.utils.cast import build_cast_info
from core.modeling.utils.filters import apply_movie_filters

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
        top_n: int = 10,
        filters: Optional[dict] = None,
        include_cast: bool = True,
    ) -> List[dict]:
        """
        텍스트 쿼리로 포스터를 검색하고 영화 메타데이터를 포함하여 반환합니다.

        Args:
            query: 검색 텍스트 (한국어 자동 번역 지원)
            top_n: 반환할 결과 수
            filters: {'min_rating', 'min_vote_count', 'genre', 'language'}
            include_cast: 출연진 정보 포함 여부

        Returns:
            영화 메타데이터 dict 리스트 (PosterSearchResultMovie 필드와 호환)
        """
        self._ensure_clip_loaded()
        df_movies = load_movie_data()

        if filters:
            filtered_df = apply_movie_filters(
                df_movies,
                genre=filters.get("genre"),
                language=filters.get("language"),
                min_rating=filters.get("min_rating", 0.0),
                min_vote_count=filters.get("min_vote_count", 0),
            )
            filter_ids = filtered_df["movie_id"].astype(str).tolist()
            if not filter_ids:
                return []
        else:
            filter_ids = None

        raw = self._clip.search(query=query, top_k=top_n, filter_movie_ids=filter_ids)

        if include_cast:
            self._ensure_cast_loaded()

        return _enrich(raw, df_movies, self._cast_grouped if include_cast else None)


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
                try:
                    movie_cast = cast_grouped.get_group(imdb_id)
                    cast_info = build_cast_info(movie_cast)
                except KeyError:
                    pass

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
