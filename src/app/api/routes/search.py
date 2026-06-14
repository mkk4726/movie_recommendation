"""
Natural Language Search API endpoints using QuerySearchPipeline.
자연어 검색 파이프라인 - BM25 기반 검색을 사용하여 영화를 검색합니다.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from app.services.data_access import load_movie_data, load_cast_data

from app.api.schemas import CastMember, MovieCastInfo, QuerySearchResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# QuerySearchPipeline 전역 변수 (지연 로딩)
_search_pipeline = None
_search_pipeline_error = None
_cast_df = None


def get_search_pipeline():
    """QuerySearchPipeline을 지연 로딩합니다."""
    global _search_pipeline, _search_pipeline_error

    if _search_pipeline is not None:
        return _search_pipeline

    if _search_pipeline_error is not None:
        raise _search_pipeline_error

    try:
        logger.info("🔄 QuerySearchPipeline 로딩 중...")

        # src/config/modeling.yaml 경로
        src_root = Path(__file__).parent.parent.parent.parent
        config_path = src_root / "config" / "modeling.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"검색 설정 파일을 찾을 수 없습니다: {config_path}")

        # QuerySearchPipeline import 및 초기화
        query_search_path = str(src_root / "core" / "modeling" / "models")
        if query_search_path not in sys.path:
            sys.path.insert(0, query_search_path)

        from query_search import QuerySearchPipeline  # type: ignore

        # 영화 데이터 로드
        df_movies = load_movie_data()
        logger.info(f"📊 영화 데이터 로드 완료: {len(df_movies)}개")

        # 파이프라인 생성 및 학습
        _search_pipeline = QuerySearchPipeline(yaml_path=str(config_path))
        _search_pipeline.fit(df_movies)

        logger.info("✅ QuerySearchPipeline 로딩 완료")
        return _search_pipeline

    except Exception as e:
        logger.error(f"❌ QuerySearchPipeline 로딩 실패: {e}", exc_info=True)
        _search_pipeline_error = e
        raise HTTPException(status_code=500, detail=f"검색 파이프라인 로딩 실패: {str(e)}")


def get_cast_data():
    """Cast 데이터를 지연 로딩합니다 (캐시 사용)."""
    global _cast_df

    if _cast_df is not None:
        return _cast_df

    try:
        logger.info("🔄 Cast 데이터 로딩 중...")
        _cast_df = load_cast_data()  # 캐시된 함수 사용
        logger.info(f"✅ Cast 데이터 로드 완료: {len(_cast_df)}개 항목")
        return _cast_df
    except Exception as e:
        logger.error(f"❌ Cast 데이터 로딩 실패: {e}", exc_info=True)
        return None


def get_movie_cast_info(imdb_id: str, cast_df: pd.DataFrame) -> MovieCastInfo:
    """
    특정 영화의 출연진 및 제작진 정보를 가져옵니다.

    Args:
        imdb_id: 영화 IMDB ID
        cast_df: Cast 데이터프레임

    Returns:
        MovieCastInfo 객체
    """
    if cast_df is None or imdb_id is None:
        return MovieCastInfo()

    # 해당 영화의 cast 데이터 필터링
    movie_cast = cast_df[cast_df["imdb_id"] == imdb_id]

    if movie_cast.empty:
        return MovieCastInfo()

    # 배우 정보 (Acting, cast_id로 정렬, 상위 5명)
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

    # 감독 정보 (Directing, cast_id로 정렬)
    directors_data = movie_cast[movie_cast["known_for_department"] == "Directing"].sort_values("cast_id")
    directors = [
        CastMember(
            name=row["name"],
            original_name=row["original_name"],
            character=None,  # 감독은 character 없음
            profile_path=row["profile_path"] if pd.notna(row["profile_path"]) else None,
        )
        for _, row in directors_data.iterrows()
    ]

    # 작가 정보 (Writing, cast_id로 정렬)
    writers_data = movie_cast[movie_cast["known_for_department"] == "Writing"].sort_values("cast_id")
    writers = [
        CastMember(
            name=row["name"],
            original_name=row["original_name"],
            character=None,  # 작가는 character 없음
            profile_path=row["profile_path"] if pd.notna(row["profile_path"]) else None,
        )
        for _, row in writers_data.iterrows()
    ]

    return MovieCastInfo(actors=actors, directors=directors, writers=writers)


@router.get("/search/natural-language", response_model=QuerySearchResponse)
def natural_language_search(
    request: Request,
    query: str = Query(..., min_length=1, description="자연어 검색 쿼리"),
    limit: int = Query(20, ge=1, le=100, description="반환할 최대 결과 수"),
    min_score: float = Query(0.0, ge=0.0, description="최소 검색 스코어 임계값"),
    min_rating: float = Query(0.0, ge=0.0, le=10.0, description="최소 평균 평점 (vote_average)"),
    min_vote_count: int = Query(0, ge=0, description="최소 평가 수 (vote_count)"),
    genre: Optional[List[str]] = Query(None, description="장르 필터 (중복 선택 가능)"),
    language: Optional[List[str]] = Query(None, description="언어 필터 (중복 선택 가능)"),
    include_cast: bool = Query(True, description="출연진/제작진 정보 포함 여부"),
):
    """
    자연어 검색 API (BM25 기반)

    QuerySearchPipeline을 사용하여 자연어 쿼리로 영화를 검색합니다.
    BM25 알고리즘을 사용하여 제목, 장르, 줄거리 등에서 관련 영화를 찾습니다.

    예시:
    - "toy story animation"
    - "action movies with robots"
    - "romantic comedy 2020"
    - "thriller directed by christopher nolan"
    """
    try:
        # 1. QuerySearchPipeline 로드
        pipeline = get_search_pipeline()

        # 2. 검색 실행 (Pydantic 모델 반환) - 필터를 파이프라인에 전달
        logger.info(
            f"🔍 자연어 검색: '{query}' (limit={limit}, min_score={min_score}, min_rating={min_rating}, min_vote_count={min_vote_count}, genre={genre}, language={language})"
        )
        response = pipeline.search_to_response(
            query=query,
            top_k=limit,
            min_score=min_score,
            min_rating=min_rating,
            min_vote_count=min_vote_count,
            genre_filter=genre,
            language_filter=language,
        )

        # 3. Cast 정보 추가 (옵션)
        if include_cast:
            cast_df = get_cast_data()
            if cast_df is not None:
                # 영화 데이터 로드하여 imdb_id 매핑
                df_movies = load_movie_data()
                movie_id_to_imdb = dict(zip(df_movies["movie_id"].astype(str), df_movies["imdb_id"]))

                # 각 검색 결과에 cast 정보 추가
                for result in response.results:
                    imdb_id = movie_id_to_imdb.get(result.movie_id)
                    if imdb_id:
                        result.cast_info = get_movie_cast_info(imdb_id, cast_df)

        # 5. 활동 로깅 및 세션 ID 생성
        session_id = None
        try:
            from app.api.user_activity_logger import get_activity_logger

            activity_logger = get_activity_logger()

            # 결과 영화 ID 리스트 추출
            result_movie_ids = [r.movie_id for r in response.results]

            # 검색 로깅 (IP 자동 추출, 세션 ID 반환)
            # 검색 로깅 (IP 자동 추출, 세션 ID 반환)
            filters = {"min_rating": min_rating, "min_vote_count": min_vote_count, "genre": genre, "language": language}

            session_id = activity_logger.log_search(
                request=request,
                query=query,
                result_count=response.total_results,
                result_movie_ids=result_movie_ids,
                search_type="natural_language",
                filters=filters,
            )
            logger.info(f"✅ 검색 로깅 완료: session_id={session_id}")
        except Exception as log_error:
            # 로깅 실패는 치명적이지 않으므로 경고만 출력
            logger.warning(f"검색 로깅 실패 (계속 진행): {log_error}")

        # 6. 응답에 세션 ID 추가
        response.session_id = session_id

        logger.info(f"✅ 검색 완료: {response.total_results}개 결과")
        return response

    except FileNotFoundError as exc:
        logger.error(f"파일을 찾을 수 없습니다: {exc}")
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"자연어 검색 실패: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"자연어 검색 중 오류가 발생했습니다: {str(exc)}")
