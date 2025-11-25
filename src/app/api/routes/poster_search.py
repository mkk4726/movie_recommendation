"""
Poster Search API endpoints using CLIP and FAISS.
텍스트로 포스터 검색 - CLIP 임베딩 및 FAISS 벡터 검색을 사용합니다.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
import pandas as pd

from app.modules.services.clip_service import get_clip_search_service, ClipServiceError
from modules.services.data_access import load_all_data, load_cast_data
from app.api.models import PosterSearchResponse, PosterSearchResultMovie, MovieCastInfo, CastMember

logger = logging.getLogger(__name__)

router = APIRouter()

# Cast 데이터 전역 변수 (지연 로딩)
_cast_df = None
_cast_by_imdb_id = None  # imdb_id로 그룹화된 딕셔너리 (빠른 조회용)


def get_cast_data():
    """Cast 데이터를 지연 로딩합니다 (캐시 사용)."""
    global _cast_df, _cast_by_imdb_id
    
    # 이미 로드되어 있으면 바로 반환 (로그 없이)
    if _cast_df is not None:
        return _cast_df, _cast_by_imdb_id
    
    try:
        # 처음 로드하는 경우에만 로그 출력
        logger.info("🔄 Cast 데이터 로딩 중...")
        _cast_df = load_cast_data()  # 캐시된 함수 사용 (이미 로드되었다면 캐시에서 가져옴)
        logger.info(f"✅ Cast 데이터 로드 완료: {len(_cast_df)}개 항목")
        
        # imdb_id로 그룹화하여 빠른 조회를 위한 딕셔너리 생성
        logger.info("🔄 Cast 데이터 인덱싱 중...")
        _cast_by_imdb_id = _cast_df.groupby('imdb_id')
        logger.info(f"✅ Cast 데이터 인덱싱 완료: {len(_cast_by_imdb_id)}개 영화")
        
        return _cast_df, _cast_by_imdb_id
    except Exception as e:
        logger.error(f"❌ Cast 데이터 로딩 실패: {e}", exc_info=True)
        return None, None


def get_movie_cast_info(imdb_id: str, cast_grouped) -> MovieCastInfo:
    """
    특정 영화의 출연진 및 제작진 정보를 가져옵니다.
    
    Args:
        imdb_id: 영화 IMDB ID
        cast_grouped: imdb_id로 그룹화된 Cast 데이터
    
    Returns:
        MovieCastInfo 객체
    """
    if cast_grouped is None or imdb_id is None:
        return MovieCastInfo()
    
    # 그룹화된 데이터에서 해당 영화의 cast 데이터 가져오기 (O(1) 조회)
    try:
        movie_cast = cast_grouped.get_group(imdb_id)
    except KeyError:
        return MovieCastInfo()
    
    if movie_cast.empty:
        return MovieCastInfo()
    
    # 배우 정보 (Acting, cast_id로 정렬, 상위 5명)
    actors_data = movie_cast[movie_cast['known_for_department'] == 'Acting'].sort_values('cast_id').head(5)
    actors = [
        CastMember(
            name=row['name'],
            original_name=row['original_name'],
            character=row['character'] if pd.notna(row['character']) else None,
            profile_path=row['profile_path'] if pd.notna(row['profile_path']) else None
        )
        for _, row in actors_data.iterrows()
    ]
    
    # 감독 정보 (Directing, cast_id로 정렬)
    directors_data = movie_cast[movie_cast['known_for_department'] == 'Directing'].sort_values('cast_id')
    directors = [
        CastMember(
            name=row['name'],
            original_name=row['original_name'],
            character=None,  # 감독은 character 없음
            profile_path=row['profile_path'] if pd.notna(row['profile_path']) else None
        )
        for _, row in directors_data.iterrows()
    ]
    
    # 작가 정보 (Writing, cast_id로 정렬)
    writers_data = movie_cast[movie_cast['known_for_department'] == 'Writing'].sort_values('cast_id')
    writers = [
        CastMember(
            name=row['name'],
            original_name=row['original_name'],
            character=None,  # 작가는 character 없음
            profile_path=row['profile_path'] if pd.notna(row['profile_path']) else None
        )
        for _, row in writers_data.iterrows()
    ]
    
    return MovieCastInfo(actors=actors, directors=directors, writers=writers)


def enrich_search_results(
    search_results: list,
    df_movies: pd.DataFrame,
    include_cast: bool = True
) -> list:
    """
    검색 결과에 영화 메타데이터를 추가합니다.
    
    Args:
        search_results: CLIP 검색 결과 [{"movie_id": str, "score": float}, ...]
        df_movies: 영화 데이터프레임
        include_cast: 출연진 정보 포함 여부
    
    Returns:
        enriched_results: PosterSearchResultMovie 객체 리스트
    """
    enriched_results = []
    
    # Cast 데이터 로드 (옵션)
    cast_grouped = None
    if include_cast:
        _, cast_grouped = get_cast_data()
    
    # movie_id를 인덱스로 하는 딕셔너리 생성 (빠른 조회)
    # 기존 컬럼이 있으면 재사용, 없으면 생성
    if 'movie_id_str' not in df_movies.columns:
        df_movies = df_movies.copy()
        df_movies['movie_id_str'] = df_movies['movie_id'].astype(str)
    movies_dict = df_movies.set_index('movie_id_str').to_dict('index')
    
    for result in search_results:
        movie_id = result.get("movie_id")
        score = result.get("score", 0.0)
        
        if movie_id not in movies_dict:
            logger.warning(f"영화 ID {movie_id}를 데이터에서 찾을 수 없습니다.")
            continue
        
        movie_data = movies_dict[movie_id]
        
        # 포스터 URL 생성
        poster_url = None
        if pd.notna(movie_data.get('poster_path')):
            poster_url = f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}"
        
        # Cast 정보 추가 (옵션)
        cast_info = None
        if include_cast and cast_grouped is not None:
            imdb_id = movie_data.get('imdb_id')
            if imdb_id and pd.notna(imdb_id):
                cast_info = get_movie_cast_info(imdb_id, cast_grouped)
        
        # PosterSearchResultMovie 객체 생성
        enriched_result = PosterSearchResultMovie(
            movie_id=movie_id,
            score=score,
            title=movie_data.get('total_title') or movie_data.get('title'),
            genres=movie_data.get('genres_tmdb') or movie_data.get('genres'),
            year=int(movie_data['year']) if pd.notna(movie_data.get('year')) else None,
            overview=movie_data.get('overview') if pd.notna(movie_data.get('overview')) else None,
            poster_url=poster_url,
            cast_info=cast_info,
            # 추가 메타데이터
            imdb_id=movie_data.get('imdb_id') if pd.notna(movie_data.get('imdb_id')) else None,
            release_date=movie_data.get('release_date') if pd.notna(movie_data.get('release_date')) else None,
            vote_average=float(movie_data['vote_average']) if pd.notna(movie_data.get('vote_average')) else None,
            vote_count=int(movie_data['vote_count']) if pd.notna(movie_data.get('vote_count')) else None,
            adult=bool(movie_data['adult']) if pd.notna(movie_data.get('adult')) else None,
            language=movie_data.get('language') if pd.notna(movie_data.get('language')) else None
        )
        
        enriched_results.append(enriched_result)
    
    return enriched_results


@router.get("/search/poster", response_model=PosterSearchResponse)
def poster_search_by_text(
    request: Request,
    query: str = Query(..., min_length=1, description="텍스트 검색 쿼리 (영어 또는 한국어)"),
    limit: int = Query(10, ge=1, le=50, description="반환할 최대 결과 수"),
    include_cast: bool = Query(True, description="출연진/제작진 정보 포함 여부"),
    min_rating: float = Query(0.0, ge=0.0, le=10.0, description="최소 평균 평점"),
    min_vote_count: int = Query(0, ge=0, description="최소 평가 수"),
    genre: Optional[List[str]] = Query(None, description="장르 필터 (중복 선택 가능)"),
    language: Optional[List[str]] = Query(None, description="언어 필터 (중복 선택 가능)"),
):
    """
    텍스트로 포스터 검색 API (CLIP 기반)
    
    CLIP 모델을 사용하여 텍스트 쿼리와 유사한 포스터를 가진 영화를 검색합니다.
    영어 검색이 더 정확하지만, 한국어도 지원됩니다 (자동 번역).
    
    예시 (영어):
    - "action movie with explosions"
    - "romantic sunset scene"
    - "dark thriller atmosphere"
    - "colorful animation"
    - "space adventure with stars"
    
    예시 (한국어):
    - "폭발이 있는 액션 영화"
    - "로맨틱한 석양 장면"
    - "어두운 스릴러 분위기"
    - "화려한 애니메이션"
    """
    try:
        # 1. 영화 데이터 로드 (필터링을 위해 먼저 로드)
        df_movies, _, _ = load_all_data()
        
        # 2. 메타데이터 필터링 (먼저 수행)
        filter_movie_ids = None
        if min_rating > 0 or min_vote_count > 0 or genre or language:
            filtered_df = df_movies.copy()
            
            # 평점 필터
            if min_rating > 0:
                filtered_df = filtered_df[filtered_df['vote_average'] >= min_rating]
            
            # 평가 수 필터
            if min_vote_count > 0:
                filtered_df = filtered_df[filtered_df['vote_count'] >= min_vote_count]
            
            # 장르 필터
            if genre:
                # genres_tmdb 컬럼 우선 사용
                genre_col = 'genres_tmdb' if 'genres_tmdb' in filtered_df.columns else 'genres'
                filtered_df = filtered_df[
                    filtered_df[genre_col].apply(
                        lambda x: any(g in str(x) for g in genre) if pd.notna(x) else False
                    )
                ]
            
            # 언어 필터
            if language:
                if 'language' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['language'].isin(language)]
            
            # 필터링된 영화 ID 목록 추출
            filter_movie_ids = filtered_df['movie_id'].astype(str).tolist()
            logger.info(f"🔍 메타데이터 필터링: {len(df_movies)} -> {len(filter_movie_ids)}개 영화")
            
            if not filter_movie_ids:
                logger.info("⚠️ 필터링 결과가 없습니다.")
                return PosterSearchResponse(
                    query_type="text",
                    query=query,
                    total_results=0,
                    results=[],
                    session_id=None
                )

        # 3. CLIP 검색 서비스 가져오기
        clip_service = get_clip_search_service()
        
        # 4. 텍스트 검색 실행 (필터링된 ID 내에서 검색)
        logger.info(f"🔍 포스터 텍스트 검색: '{query}' (limit={limit}, filter_ids={len(filter_movie_ids) if filter_movie_ids else 'All'})")
        search_results = clip_service.search_by_text(
            text=query, 
            k=limit,
            filter_movie_ids=filter_movie_ids
        )
        
        # 5. 검색 결과에 메타데이터 추가
        enriched_results = enrich_search_results(
            search_results=search_results,
            df_movies=df_movies,
            include_cast=include_cast
        )
        
        # 6. 활동 로깅 추가
        session_id = None
        try:
            from app.api.user_activity_logger import get_activity_logger
            activity_logger = get_activity_logger()
            
            # 결과 영화 ID 리스트 추출
            result_movie_ids = [r.movie_id for r in enriched_results]
            
            # 검색 로깅 (세션 ID 생성)
            # 검색 로깅 (세션 ID 생성)
            filters = {
                "min_rating": min_rating,
                "min_vote_count": min_vote_count,
                "genre": genre,
                "language": language
            }
            
            session_id = activity_logger.log_search(
                request=request,
                query=query,
                result_count=len(enriched_results),
                result_movie_ids=result_movie_ids,
                search_type="poster",
                filters=filters
            )
            logger.info(f"✅ 포스터 검색 로깅 완료: session_id={session_id}")
        except Exception as log_error:
            logger.warning(f"포스터 검색 로깅 실패 (계속 진행): {log_error}")
        
        # 7. 응답 생성
        response = PosterSearchResponse(
            query_type="text",
            query=query,
            total_results=len(enriched_results),
            results=enriched_results,
            session_id=session_id
        )
        
        logger.info(f"✅ 포스터 텍스트 검색 완료: {response.total_results}개 결과")
        return response
        
    except ClipServiceError as exc:
        logger.error(f"CLIP 서비스 오류: {exc}")
        raise HTTPException(
            status_code=503,
            detail=f"포스터 검색 서비스를 사용할 수 없습니다: {str(exc)}"
        )
    except FileNotFoundError as exc:
        logger.error(f"파일을 찾을 수 없습니다: {exc}")
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"포스터 텍스트 검색 실패: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"포스터 검색 중 오류가 발생했습니다: {str(exc)}"
        )

