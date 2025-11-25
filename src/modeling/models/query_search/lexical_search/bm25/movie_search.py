"""
영화 검색에 특화된 BM25 모듈

여러 필드(제목, 장르, 태그 등)에 대해 가중치를 적용한 검색을 지원합니다.
"""

import logging
import pickle
from collections import defaultdict
from pathlib import Path
from typing import List, Optional

from .config import BM25Config
from .core import BM25
from .models import BM25SearchResult

logger = logging.getLogger(__name__)


class MovieBM25:
    """
    영화 검색에 특화된 BM25 래퍼 클래스
    여러 필드(제목, 장르, 태그 등)에 대해 가중치를 적용한 검색을 지원합니다.
    """

    def __init__(self, config: Optional[BM25Config] = None, yaml_path: Optional[str] = None):
        """
        MovieBM25 초기화

        Args:
            config: BM25Config 객체 (None이면 YAML에서 로드)
            yaml_path: YAML 파일 경로 (config가 None일 때 사용)
        """
        # 설정 로드
        if config is None:
            self.config = BM25Config.from_yaml(yaml_path)
        else:
            self.config = config

        # 각 필드별 BM25 인스턴스 생성
        self.bm25_instances = {}
        for field in self.config.field_weights.keys():
            self.bm25_instances[field] = BM25(config=self.config)

        logger.info(f"✅ MovieBM25 초기화 완료 (필드: {list(self.config.field_weights.keys())})")

    def fit(self, movies_df):
        """
        영화 데이터프레임으로 색인 생성

        Args:
            movies_df: 영화 데이터프레임 (movie_id, title, genres 등 포함)
        """
        logger.info(f"🔄 영화 데이터 색인 생성 중... ({len(movies_df)}개 영화)")

        # 문서 ID 및 메타데이터 준비
        # movie_id 또는 movieId 컬럼 지원
        id_col = "movie_id" if "movie_id" in movies_df.columns else "movieId"
        doc_ids = movies_df[id_col].tolist()
        metadata = []

        # genres_tmdb 컬럼이 있으면 우선 사용
        genres_col = "genres_tmdb" if "genres_tmdb" in movies_df.columns else "genres"

        for _, row in movies_df.iterrows():
            # total_title이 있으면 사용, 없으면 title 사용
            title_value = row.get("total_title", "") or row.get("title", "")
            meta = {
                "title": title_value,
                "genres": row.get(genres_col, ""),
                "overview": row.get("overview", ""),
                "vote_average": row.get("vote_average", 0.0),
                "vote_count": row.get("vote_count", 0),
                "language": row.get("language", ""),
            }
            metadata.append(meta)

        # 각 필드별로 색인 생성
        for field, bm25 in self.bm25_instances.items():
            # title 필드는 total_title을 우선 사용
            actual_field = field
            if field == "title":
                if "total_title" in movies_df.columns:
                    actual_field = "total_title"
                elif "title" not in movies_df.columns:
                    logger.warning("  ⚠️ 'title' 또는 'total_title' 필드가 데이터프레임에 없습니다.")
                    continue

            if actual_field in movies_df.columns:
                corpus = movies_df[actual_field].fillna("").astype(str).tolist()
                bm25.fit(corpus, doc_ids, metadata)
                logger.info(f"  ✓ '{field}' 필드 색인 완료 (실제 컬럼: '{actual_field}')")
            else:
                logger.warning(f"  ⚠️ '{field}' 필드가 데이터프레임에 없습니다.")

        logger.info("✅ 모든 필드 색인 생성 완료")

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        min_rating: float = 0.0,
        min_vote_count: int = 0,
        genre_filter: Optional[List[str]] = None,
        language_filter: Optional[List[str]] = None,
    ) -> List[BM25SearchResult]:
        """
        여러 필드를 통합하여 영화 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 개수
            min_score: 최소 스코어 임계값
            min_rating: 최소 평점 임계값
            min_vote_count: 최소 평가 수 임계값
            genre_filter: 장르 필터 리스트 (선택한 장르 중 하나라도 포함하면 통과)
            language_filter: 언어 필터 리스트 (선택한 언어 중 하나와 일치하면 통과)

        Returns:
            BM25SearchResult 리스트 (통합 스코어 내림차순 정렬)
        """
        top_k = top_k if top_k is not None else self.config.top_k
        min_score = min_score if min_score is not None else self.config.min_score

        logger.info(f"🔍 영화 검색 중: '{query}' (장르 필터: {genre_filter}, 언어 필터: {language_filter})")

        # 각 필드별 검색 결과를 통합
        combined_scores = defaultdict(lambda: {"score": 0.0, "fields": {}, "metadata": {}})

        # 필터가 있으면 검색 범위를 대폭 늘림
        search_k = top_k * 3
        if genre_filter or language_filter or min_rating > 0 or min_vote_count > 0:
            search_k = max(top_k * 50, 1000)  # 최소 1000개는 검색

        for field, bm25 in self.bm25_instances.items():
            weight = self.config.field_weights.get(field, 1.0)
            results = bm25.search(query, top_k=search_k, min_score=0.0)  # 더 많이 가져와서 통합

            for result in results:
                movie_id = result.movie_id
                weighted_score = result.score * weight

                combined_scores[movie_id]["score"] += weighted_score
                combined_scores[movie_id]["fields"][field] = weighted_score
                combined_scores[movie_id]["metadata"] = {
                    "title": result.title,
                    "genres": result.genres,
                    "overview": result.overview,
                    "vote_average": result.vote_average if hasattr(result, "vote_average") else 0.0,
                    "vote_count": result.vote_count if hasattr(result, "vote_count") else 0,
                    "language": result.language if hasattr(result, "language") else "",
                }

        # 통합 스코어로 정렬
        sorted_results = sorted(combined_scores.items(), key=lambda x: x[1]["score"], reverse=True)

        # BM25SearchResult 객체로 변환 (필터 적용 후 top_k개 수집)
        final_results = []
        for movie_id, data in sorted_results:
            # 평점 필터링
            vote_average = data["metadata"].get("vote_average", 0.0)
            if vote_average < min_rating:
                continue

            # 평가 수 필터링
            vote_count = data["metadata"].get("vote_count", 0)
            if vote_count < min_vote_count:
                continue

            # 장르 필터링
            if genre_filter:
                movie_genres = str(data["metadata"].get("genres", ""))
                if not any(g in movie_genres for g in genre_filter):
                    continue

            # 언어 필터링
            if language_filter:
                movie_language = data["metadata"].get("language", "")
                if movie_language not in language_filter:
                    continue

            if data["score"] >= min_score:
                result = BM25SearchResult(
                    movie_id=movie_id,
                    score=data["score"],
                    title=data["metadata"]["title"],
                    genres=data["metadata"]["genres"],
                    matched_fields=data["fields"],
                    overview=data["metadata"].get("overview", ""),
                    vote_average=data["metadata"].get("vote_average", 0.0),
                    vote_count=data["metadata"].get("vote_count", 0),
                    language=data["metadata"].get("language", ""),
                )
                final_results.append(result)

            if len(final_results) >= top_k:
                break

        logger.info(f"✅ 검색 완료: {len(final_results)}개 결과 반환")
        return final_results

    def save(self, dirpath: str):
        """
        모든 필드의 BM25 색인을 디렉토리에 저장

        Args:
            dirpath: 저장할 디렉토리 경로
        """
        dirpath = Path(dirpath)
        dirpath.mkdir(parents=True, exist_ok=True)

        for field, bm25 in self.bm25_instances.items():
            filepath = dirpath / f"bm25_{field}.pkl"
            bm25.save(str(filepath))

        # 설정 저장
        config_path = dirpath / "config.pkl"
        with open(config_path, "wb") as f:
            pickle.dump(self.config, f)

        logger.info(f"💾 MovieBM25 색인 저장 완료: {dirpath}")

    @classmethod
    def load(cls, dirpath: str) -> "MovieBM25":
        """
        디렉토리에서 모든 필드의 BM25 색인 로드

        Args:
            dirpath: 로드할 디렉토리 경로

        Returns:
            MovieBM25 객체
        """
        dirpath = Path(dirpath)

        # 설정 로드
        config_path = dirpath / "config.pkl"
        with open(config_path, "rb") as f:
            config = pickle.load(f)

        # MovieBM25 객체 생성
        movie_bm25 = cls(config=config)

        # 각 필드별 BM25 로드
        for field in config.field_weights.keys():
            filepath = dirpath / f"bm25_{field}.pkl"
            if filepath.exists():
                movie_bm25.bm25_instances[field] = BM25.load(str(filepath))
            else:
                logger.warning(f"⚠️ '{field}' 필드 색인 파일을 찾을 수 없습니다: {filepath}")

        logger.info(f"📂 MovieBM25 색인 로드 완료: {dirpath}")
        return movie_bm25
