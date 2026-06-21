"""
자연어 검색 파이프라인 (BM25).
텍스트 쿼리로 영화를 검색하고 cast 정보까지 포함한 응답을 반환합니다.
"""

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from core.db.data_access import load_cast_data, load_movie_data
from core.modeling.models.query_search.query_search import QuerySearchPipeline as _BM25Pipeline
from core.modeling.utils.cast import build_cast_info

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "modeling.yaml"


class NaturalLanguageSearchPipeline:
    """BM25 기반 자연어 검색 파이프라인."""

    def __init__(self):
        self._pipeline: _BM25Pipeline | None = None
        self._cast_df: pd.DataFrame | None = None
        self._movie_id_to_imdb: dict | None = None

    def _ensure_loaded(self):
        if self._pipeline is not None:
            return
        logger.info("NaturalLanguageSearchPipeline: BM25 인덱스 생성 중...")
        if not _CONFIG_PATH.exists():
            raise FileNotFoundError(f"검색 설정 파일을 찾을 수 없습니다: {_CONFIG_PATH}")
        self._pipeline = _BM25Pipeline(yaml_path=str(_CONFIG_PATH))
        self._pipeline.fit(load_movie_data())
        logger.info("NaturalLanguageSearchPipeline: BM25 인덱스 생성 완료")

    def _ensure_cast_loaded(self):
        if self._cast_df is not None:
            return
        self._cast_df = load_cast_data()
        df_movies = load_movie_data()
        self._movie_id_to_imdb = dict(
            zip(df_movies["movie_id"].astype(str), df_movies["imdb_id"])
        )

    def search(
        self,
        query: str,
        top_n: int = 20,
        min_score: float = 0.0,
        min_rating: float = 0.0,
        min_vote_count: int = 0,
        genre_filter: Optional[List[str]] = None,
        language_filter: Optional[List[str]] = None,
        include_cast: bool = True,
    ):
        """
        자연어 쿼리로 영화를 검색합니다.

        Returns:
            QuerySearchResponse (query, total_results, results, session_id=None)
        """
        self._ensure_loaded()
        response = self._pipeline.search_to_response(
            query=query,
            top_k=top_n,
            min_score=min_score,
            min_rating=min_rating,
            min_vote_count=min_vote_count,
            genre_filter=genre_filter,
            language_filter=language_filter,
        )

        if include_cast and response.results:
            self._ensure_cast_loaded()
            for result in response.results:
                imdb_id = self._movie_id_to_imdb.get(result.movie_id)
                if imdb_id:
                    movie_cast = self._cast_df[self._cast_df["imdb_id"] == imdb_id]
                    result.cast_info = build_cast_info(movie_cast)

        return response
