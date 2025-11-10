"""
Natural Language Search API endpoints using NER.
자연어 검색 파이프라인 - NER을 사용하여 쿼리에서 엔티티를 추출하고 영화를 검색합니다.
"""
import logging
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
import pandas as pd

from modules.services.data_access import load_all_data
from app.api.models import SearchResponse
from app.api.utils import from_dataframe

logger = logging.getLogger(__name__)

router = APIRouter()

# # NER 모델 전역 변수 (지연 로딩)
# _ner_model = None
# _ner_model_error = None


# def get_ner_model():
#     """NER 모델을 지연 로딩합니다."""
#     global _ner_model, _ner_model_error
    
#     if _ner_model is not None:
#         return _ner_model
    
#     if _ner_model_error is not None:
#         raise _ner_model_error
    
#     try:
#         logger.info("🔄 NER 모델 로딩 중...")
#         # modeling/models/config.yaml 경로 찾기
#         project_root = Path(__file__).parent.parent.parent.parent
#         config_path = project_root / "modeling" / "models" / "config.yaml"
        
#         if not config_path.exists():
#             raise FileNotFoundError(f"NER 설정 파일을 찾을 수 없습니다: {config_path}")
        
#         # NER 모델 import 및 초기화
#         import sys
#         sys.path.insert(0, str(project_root / "modeling" / "models" / "query_search"))
        
#         from NER import QwenBasedNER
        
#         _ner_model = QwenBasedNER(yaml_path=str(config_path))
#         logger.info("✅ NER 모델 로딩 완료")
#         return _ner_model
        
#     except Exception as e:
#         logger.error(f"❌ NER 모델 로딩 실패: {e}", exc_info=True)
#         _ner_model_error = e
#         raise HTTPException(
#             status_code=500,
#             detail=f"NER 모델 로딩 실패: {str(e)}"
#         )


# def filter_movies_by_ner(df_movies: pd.DataFrame, ner_result) -> pd.DataFrame:
#     """
#     NER 결과를 기반으로 영화를 필터링합니다.
    
#     Args:
#         df_movies: 영화 데이터프레임
#         ner_result: NERResult 객체
        
#     Returns:
#         필터링된 영화 데이터프레임
#     """
#     filtered_df = df_movies.copy()
    
#     # 1. 영화 제목으로 필터링
#     if ner_result.movie_titles:
#         logger.info(f"🎬 영화 제목 필터: {ner_result.movie_titles}")
#         title_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
#         for title in ner_result.movie_titles:
#             # title 또는 total_title 컬럼에서 검색
#             if 'total_title' in filtered_df.columns:
#                 title_mask |= filtered_df['total_title'].str.contains(title, case=False, na=False)
#             if 'title' in filtered_df.columns:
#                 title_mask |= filtered_df['title'].str.contains(title, case=False, na=False)
#         filtered_df = filtered_df[title_mask]
    
#     # 2. 장르로 필터링
#     if ner_result.genres:
#         logger.info(f"🎭 장르 필터: {ner_result.genres}")
#         genre_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
#         for genre in ner_result.genres:
#             # genre 또는 genres_tmdb 컬럼에서 검색
#             if 'genre' in filtered_df.columns:
#                 genre_mask |= filtered_df['genre'].str.contains(genre, case=False, na=False)
#             if 'genres_tmdb' in filtered_df.columns:
#                 genre_mask |= filtered_df['genres_tmdb'].str.contains(genre, case=False, na=False)
#         filtered_df = filtered_df[genre_mask]
    
#     # 3. 연도로 필터링
#     if ner_result.years:
#         logger.info(f"📅 연도 필터: {ner_result.years}")
#         if 'year' in filtered_df.columns:
#             year_mask = filtered_df['year'].isin(ner_result.years)
#             filtered_df = filtered_df[year_mask]
    
#     # 4. 배우로 필터링 (overview에서 검색)
#     if ner_result.actors:
#         logger.info(f"👤 배우 필터: {ner_result.actors}")
#         if 'overview' in filtered_df.columns:
#             actor_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
#             for actor in ner_result.actors:
#                 actor_mask |= filtered_df['overview'].str.contains(actor, case=False, na=False)
#             # 배우 정보가 없을 수 있으므로 결과가 없으면 필터링하지 않음
#             if actor_mask.any():
#                 filtered_df = filtered_df[actor_mask]
#             else:
#                 logger.warning(f"⚠️ 배우 '{ner_result.actors}'로 필터링된 결과가 없습니다. 배우 필터를 무시합니다.")
    
#     # 5. 감독으로 필터링 (overview에서 검색)
#     if ner_result.directors:
#         logger.info(f"🎬 감독 필터: {ner_result.directors}")
#         if 'overview' in filtered_df.columns:
#             director_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
#             for director in ner_result.directors:
#                 director_mask |= filtered_df['overview'].str.contains(director, case=False, na=False)
#             # 감독 정보가 없을 수 있으므로 결과가 없으면 필터링하지 않음
#             if director_mask.any():
#                 filtered_df = filtered_df[director_mask]
#             else:
#                 logger.warning(f"⚠️ 감독 '{ner_result.directors}'로 필터링된 결과가 없습니다. 감독 필터를 무시합니다.")
    
#     # 6. 스토리 키워드로 필터링 (overview에서 검색)
#     if ner_result.story_keywords:
#         logger.info(f"📝 스토리 키워드 필터: {ner_result.story_keywords}")
#         if 'overview' in filtered_df.columns:
#             keyword_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
#             for keyword in ner_result.story_keywords:
#                 keyword_mask |= filtered_df['overview'].str.contains(keyword, case=False, na=False)
#             # 키워드 정보가 없을 수 있으므로 결과가 없으면 필터링하지 않음
#             if keyword_mask.any():
#                 filtered_df = filtered_df[keyword_mask]
#             else:
#                 logger.warning(f"⚠️ 키워드 '{ner_result.story_keywords}'로 필터링된 결과가 없습니다. 키워드 필터를 무시합니다.")
    
#     return filtered_df


# def rank_movies_by_relevance(df_movies: pd.DataFrame, ner_result) -> pd.DataFrame:
#     """
#     NER 결과를 기반으로 영화의 관련성을 점수화하고 정렬합니다.
    
#     Args:
#         df_movies: 영화 데이터프레임
#         ner_result: NERResult 객체
        
#     Returns:
#         관련성 점수로 정렬된 영화 데이터프레임
#     """
#     if df_movies.empty:
#         return df_movies
    
#     # 관련성 점수 초기화
#     df_movies = df_movies.copy()
#     df_movies['relevance_score'] = 0.0
    
#     # 1. 영화 제목 매칭 (가장 높은 점수)
#     if ner_result.movie_titles:
#         for title in ner_result.movie_titles:
#             if 'total_title' in df_movies.columns:
#                 mask = df_movies['total_title'].str.contains(title, case=False, na=False)
#                 df_movies.loc[mask, 'relevance_score'] += 100
#             if 'title' in df_movies.columns:
#                 mask = df_movies['title'].str.contains(title, case=False, na=False)
#                 df_movies.loc[mask, 'relevance_score'] += 100
    
#     # 2. 장르 매칭
#     if ner_result.genres:
#         for genre in ner_result.genres:
#             if 'genre' in df_movies.columns:
#                 mask = df_movies['genre'].str.contains(genre, case=False, na=False)
#                 df_movies.loc[mask, 'relevance_score'] += 50
#             if 'genres_tmdb' in df_movies.columns:
#                 mask = df_movies['genres_tmdb'].str.contains(genre, case=False, na=False)
#                 df_movies.loc[mask, 'relevance_score'] += 50
    
#     # 3. 연도 매칭
#     if ner_result.years and 'year' in df_movies.columns:
#         mask = df_movies['year'].isin(ner_result.years)
#         df_movies.loc[mask, 'relevance_score'] += 30
    
#     # 4. 배우 매칭
#     if ner_result.actors and 'overview' in df_movies.columns:
#         for actor in ner_result.actors:
#             mask = df_movies['overview'].str.contains(actor, case=False, na=False)
#             df_movies.loc[mask, 'relevance_score'] += 40
    
#     # 5. 감독 매칭
#     if ner_result.directors and 'overview' in df_movies.columns:
#         for director in ner_result.directors:
#             mask = df_movies['overview'].str.contains(director, case=False, na=False)
#             df_movies.loc[mask, 'relevance_score'] += 40
    
#     # 6. 스토리 키워드 매칭
#     if ner_result.story_keywords and 'overview' in df_movies.columns:
#         for keyword in ner_result.story_keywords:
#             mask = df_movies['overview'].str.contains(keyword, case=False, na=False)
#             df_movies.loc[mask, 'relevance_score'] += 20
    
#     # 7. TMDB 평점 보너스 (인기도 반영)
#     if 'vote_average' in df_movies.columns and 'vote_count' in df_movies.columns:
#         # 평점이 높고 투표 수가 많은 영화에 보너스
#         df_movies.loc[
#             (df_movies['vote_average'] >= 7.0) & (df_movies['vote_count'] >= 1000),
#             'relevance_score'
#         ] += 10
    
#     # 관련성 점수로 정렬 (내림차순)
#     df_movies = df_movies.sort_values('relevance_score', ascending=False)
    
#     return df_movies


@router.get("/search/natural-language", response_model=SearchResponse)
def natural_language_search(
    query: str = Query(..., min_length=1, description="자연어 검색 쿼리"),
    limit: int = Query(10, ge=1, le=100, description="반환할 최대 결과 수"),
    use_ranking: bool = Query(True, description="관련성 점수로 정렬할지 여부"),
):
    """
    자연어 검색 API
    
    NER을 사용하여 자연어 쿼리에서 엔티티를 추출하고,
    추출된 엔티티를 기반으로 영화를 검색합니다.
    
    예시:
    - "이병헌이 출연한 액션 영화 추천해줘"
    - "2020년 로맨스 영화"
    - "박찬욱 감독의 스릴러 영화"
    """
    try:
        # # 1. NER 모델 로드
        # ner_model = get_ner_model()
        
        # # 2. 쿼리에서 엔티티 추출
        # logger.info(f"🔍 자연어 검색 쿼리: {query}")
        # ner_result = ner_model.run(query, verbose=True)
        # logger.info(f"📊 추출된 엔티티: {ner_result}")
        
        # # 3. 영화 데이터 로드
        # df_movies, _, _ = load_all_data()
        
        # # 4. NER 결과로 영화 필터링
        # filtered_df = filter_movies_by_ner(df_movies, ner_result)
        # logger.info(f"📊 필터링 결과: {len(filtered_df)}개 영화")
        
        # # 5. 관련성 점수로 정렬 (옵션)
        # if use_ranking and not filtered_df.empty:
        #     filtered_df = rank_movies_by_relevance(filtered_df, ner_result)
        #     logger.info("✅ 관련성 점수로 정렬 완료")
        
        # # 6. 결과 제한
        # result_df = filtered_df.head(limit)
        
        # # 7. 응답 생성
        # results = from_dataframe(result_df)
        
        return SearchResponse(
            query=query,
            results=query
        )
        
    except FileNotFoundError as exc:
        logger.error(f"파일을 찾을 수 없습니다: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error(f"자연어 검색 실패: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"자연어 검색 중 오류가 발생했습니다: {str(exc)}"
        )


# @router.get("/search/extract-entities")
# def extract_entities(query: str = Query(..., min_length=1, description="자연어 쿼리")):
#     """
#     쿼리에서 엔티티만 추출하는 API (디버깅/테스트용)
    
#     NER 모델을 사용하여 쿼리에서 엔티티를 추출하고 반환합니다.
#     """
#     try:
#         # NER 모델 로드
#         ner_model = get_ner_model()
        
#         # 엔티티 추출
#         logger.info(f"🔍 엔티티 추출 쿼리: {query}")
#         ner_result = ner_model.run(query, verbose=True)
        
#         return {
#             "query": query,
#             "entities": ner_result.to_dict()
#         }
        
#     except Exception as exc:
#         logger.error(f"엔티티 추출 실패: {exc}", exc_info=True)
#         raise HTTPException(
#             status_code=500,
#             detail=f"엔티티 추출 중 오류가 발생했습니다: {str(exc)}"
#         )

