"""
Item-Based Collaborative Filtering 영화 추천 시스템 파이프라인
"""
import pickle
import logging
import time
import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, lil_matrix
from sklearn.metrics.pairwise import cosine_similarity

import sys

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data_scraping.common.data_loader import load_ratings_data, load_movie_data
from modeling.utils.data import filter_by_min_counts, preprocess_id_mapping
from modeling.utils.file_utils import format_file_size

# Logger 설정
logger = logging.getLogger(__name__)


@dataclass
class ItemBasedConfig:
    """Item-Based 모델 설정"""
    min_user_ratings: int = 30
    min_movie_ratings: int = 10
    top_k: int = 50  # 각 영화당 유지할 상위 K개의 유사 영화
    verbose: bool = True
    
    # 데이터 통합 설정
    use_integrated_data: bool = False
    
    def __str__(self):
        return f"""
=== Item-Based CF 설정 ===
최소 사용자 평점 수: {self.min_user_ratings}
최소 영화 평점 수: {self.min_movie_ratings}
Top-K 유사도: {self.top_k}
"""
    
    @classmethod
    def from_yaml(cls, yaml_path: Optional[str] = None) -> 'ItemBasedConfig':
        """
        YAML 파일에서 설정을 로드하여 ItemBasedConfig 객체 생성
        
        Args:
            yaml_path: YAML 파일 경로 (None이면 기본 경로 사용)
            
        Returns:
            ItemBasedConfig 객체
        """
        # 기본 경로 설정
        if yaml_path is None:
            yaml_path = Path(__file__).parent / 'config.yaml'
        else:
            yaml_path = Path(yaml_path)
        
        # YAML 파일 읽기
        logger.info(f"📄 설정 파일 로드: {yaml_path}")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        # item_based 섹션 추출
        if 'item_based' not in config_dict:
            raise ValueError("config.yaml 파일에 'item_based' 섹션이 없습니다.")
        
        item_based_config = config_dict['item_based']
        
        # 데이터 통합 설정 추출 (item_based 섹션에서 직접 읽기)
        use_integrated_data = item_based_config.get('use_integrated_data', False)
        
        # 데이터 통합 설정을 item_based_config에 추가
        item_based_config.update({
            'use_integrated_data': use_integrated_data
        })
        
        logger.info("✅ 설정 로드 완료")
        return cls(**item_based_config)


class ItemBasedRecommender:
    """
    Item-Based Collaborative Filtering 추천 시스템
    
    주요 기능:
    - 아이템 간 유사도 행렬 계산 (코사인 유사도)
    - Top-K 유사도 최적화 (메모리 효율성)
    - 유사한 영화 추천
    - 모델 저장/로드
    """
    
    def __init__(self, config: Optional[ItemBasedConfig] = None):
        """
        Args:
            config: 모델 설정 (None이면 기본값 사용)
        """
        self.config = config or ItemBasedConfig()
        self.item_similarity_matrix = None
        self.id_mapping = None
        
        if self.config.verbose:
            logger.info("✅ ItemBasedRecommender 초기화 완료")
            logger.info(str(self.config))
    
    def fit(self, df_filtered:pd.DataFrame = None):
        """
        학습 데이터로 아이템 유사도 행렬 생성
        
        Args:
            df_filtered: 평점 데이터프레임 (None이면 자동 로드)
        """
        logger.info("\n" + "="*50)
        logger.info("📊 Item-Based CF 학습 시작")
        logger.info("="*50)
                        
        logger.info("ID 매핑 중...")
        df_mapped, self.id_mapping = preprocess_id_mapping(
            df_filtered,
            verbose=self.config.verbose
        )
        
        # 4. 유사도 행렬 생성
        logger.info("아이템 유사도 행렬 생성 중...")
        self._build_similarity_matrix(df_mapped)
        
        logger.info("\n" + "="*50)
        logger.info("✅ 학습 완료!")
        logger.info("="*50)
    
    def _build_similarity_matrix(self, df_mapped: pd.DataFrame):
        """아이템 간 유사도 행렬 생성"""
        n_users = df_mapped['user_idx'].nunique()
        n_movies = df_mapped['movie_idx'].nunique()

        logger.info(f"사용자-아이템 행렬 생성 중... ({n_users} x {n_movies})")
        
        # User-Item 행렬 생성 (Sparse Matrix)
        user_item_matrix = csr_matrix(
            (
                df_mapped['rating'].values,
                (df_mapped['user_idx'].values, df_mapped['movie_idx'].values)
            ),
            shape=(n_users, n_movies)
        )
        
        # Item-User 행렬 (전치)
        item_user_matrix = user_item_matrix.T
        
        logger.info("코사인 유사도 계산 중...")
        start_time = time.time()
        
        # 아이템 간 코사인 유사도 계산
        item_similarity = cosine_similarity(item_user_matrix, dense_output=False)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ 유사도 계산 완료 (소요 시간: {elapsed:.2f}초)")
        
        # Top-K 최적화
        self.item_similarity_matrix = self._build_topk_similarity(
            item_similarity,
            k=self.config.top_k
        )
    
    def _build_topk_similarity(self, similarity_matrix, k: int):
        """
        Top-K 유사도 행렬 생성 (메모리 최적화)
        
        Args:
            similarity_matrix: 전체 유사도 행렬 (sparse matrix)
            k: 각 아이템당 유지할 상위 K개
        
        Returns:
            Top-K만 포함하는 sparse matrix
        """
        # 변환 전 크기 출력
        original_memory = similarity_matrix.data.nbytes / (1024**2)
        original_nnz = similarity_matrix.nnz
        
        if self.config.verbose:
            logger.info("\n=== 변환 전 크기 ===")
            logger.info(f"  Non-zero 요소 수: {original_nnz:,}")
            logger.info(f"  메모리 크기: {original_memory:.2f} MB")
            logger.info(f"  행렬 크기: {similarity_matrix.shape}")
        
        n_items = similarity_matrix.shape[0]
        topk_similarity = lil_matrix(similarity_matrix.shape)
        
        logger.info(f"\nTop-{k} 유사도 행렬 생성 중...")
        start_time = time.time()
        
        for i in range(n_items):
            if i % 1000 == 0 and self.config.verbose:
                logger.info(f"  진행: {i}/{n_items} ({100*i/n_items:.1f}%)")
            
            row = similarity_matrix.getrow(i).toarray().flatten()
            row[i] = -1  # 자기 자신 제외
            
            # Top-K 선택
            if len(row) > k:
                top_k_indices = np.argpartition(row, -k)[-k:]
                top_k_indices = top_k_indices[row[top_k_indices] > 0]
            else:
                top_k_indices = np.where(row > 0)[0]
            
            if len(top_k_indices) > 0:
                topk_similarity[i, top_k_indices] = row[top_k_indices]
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ 완료! (소요 시간: {elapsed_time:.2f}초)")
        
        # CSR로 변환
        topk_similarity_csr = topk_similarity.tocsr()
        
        # 변환 후 크기 출력
        if self.config.verbose:
            optimized_memory = topk_similarity_csr.data.nbytes / (1024**2)
            optimized_nnz = topk_similarity_csr.nnz
            logger.info("\n=== 변환 후 크기 ===")
            logger.info(f"  Non-zero 요소 수: {optimized_nnz:,}")
            logger.info(f"  메모리 크기: {optimized_memory:.2f} MB")
            logger.info(f"  행렬 크기: {topk_similarity_csr.shape}")
            
            # 절감률 출력
            memory_reduction = (1 - optimized_memory / original_memory) * 100
            nnz_reduction = (1 - optimized_nnz / original_nnz) * 100
            logger.info("\n=== 최적화 효과 ===")
            logger.info(f"  메모리 절감률: {memory_reduction:.2f}%")
            logger.info(f"  Non-zero 요소 감소율: {nnz_reduction:.2f}%")
        
        return topk_similarity_csr
    
    def recommend(
        self,
        movie_id: str,
        top_n: int = 10,
        return_scores: bool = False,
        filters: dict = None
    ) -> pd.DataFrame:
        """
        특정 영화와 유사한 영화 추천
        
        Args:
            movie_id: 영화 ID
            top_n: 추천할 영화 개수
            return_scores: 유사도 점수 포함 여부
            filters: 필터 조건 딕셔너리 (선택사항)
                - genre: 장르 리스트, 예: ["로맨스", "액션"]
                - min_year: 최소 제작연도, 예: 1988
                - max_year: 최대 제작연도, 예: 2026
        
        Returns:
            추천 영화 정보 DataFrame
        """
        if self.item_similarity_matrix is None:
            raise ValueError("모델이 학습되지 않았습니다. fit()을 먼저 실행하세요.")
        
        # movie_id를 movie_idx로 변환
        if movie_id not in self.id_mapping.movie_to_idx:
            logger.warning(f"❌ 영화 ID '{movie_id}'를 찾을 수 없습니다.")
            return None
        
        movie_idx = self.id_mapping.movie_to_idx[movie_id]
        
        # 유사도 추출
        similarities = self.item_similarity_matrix[movie_idx].toarray().flatten()
        
        # 유사도가 0보다 큰 영화들만 선택 (자기 자신 제외)
        similar_items = []
        for idx, sim in enumerate(similarities):
            if idx != movie_idx and sim > 0:
                similar_items.append((idx, sim))
        
        # 유사도 기준으로 정렬 (높은 순)
        similar_items.sort(key=lambda x: x[1], reverse=True)
        
        if len(similar_items) == 0:
            logger.warning("\n⚠️ 유사한 영화를 찾을 수 없습니다.")
            return None
        
        # 모든 유사 영화의 ID 추출
        movie_indices = [idx for idx, _ in similar_items]
        scores = [score for _, score in similar_items]
        recommended_movie_ids = [self.id_mapping.idx_to_movie[idx] for idx in movie_indices]
        
        # 영화 정보 로드
        movie_df = load_movie_data()
        result_df = movie_df[movie_df['movie_id'].isin(recommended_movie_ids)].copy()
        
        # 유사도 점수 추가
        if return_scores:
            score_dict = dict(zip(recommended_movie_ids, scores))
            result_df['similarity_score'] = result_df['movie_id'].map(score_dict)
        
        # 필터링 적용
        if filters is not None:
            # 장르 필터링
            if 'genre' in filters and filters['genre']:
                genres = filters['genre']
                if isinstance(genres, list) and len(genres) > 0:
                    def matches_genre(genre_str):
                        """영화의 장르가 필터 조건과 일치하는지 확인"""
                        if pd.isna(genre_str) or not isinstance(genre_str, str):
                            return False
                        movie_genres = [g.strip() for g in genre_str.split(' ')]
                        return any(genre in movie_genres for genre in genres)
                    
                    result_df = result_df[result_df['genre'].apply(matches_genre)]
                    
            
            # 연도 필터링
            if 'min_year' in filters and filters['min_year'] is not None:
                if 'year' in result_df.columns:
                    result_df = result_df[pd.to_numeric(result_df['year'], errors='coerce') >= filters['min_year']]
            
            if 'max_year' in filters and filters['max_year'] is not None:
                if 'year' in result_df.columns:
                    result_df = result_df[pd.to_numeric(result_df['year'], errors='coerce') <= filters['max_year']]

            # 국가 필터링
            if 'country' in filters and filters['country']:
                countries = filters['country']
                if isinstance(countries, list) and len(countries) > 0:
                    def matches_country(country_str):
                        if pd.isna(country_str) or not isinstance(country_str, str):
                            return False
                        movie_countries = [c.strip() for c in country_str.split(',')]
                        return any(country in movie_countries for country in countries)
                    if 'country' in result_df.columns:
                        result_df = result_df[result_df['country'].apply(matches_country)]
        
        # 유사도 기준으로 정렬 후 top_n만큼만 반환
        if return_scores:
            result_df = result_df.sort_values('similarity_score', ascending=False)
        else:
            # 유사도 점수가 없으면 원래 순서 유지 (이미 정렬되어 있음)
            pass
        
        result_df = result_df.head(top_n)
        
        return result_df.reset_index(drop=True)
    
    def save(self, filepath: str):
        """
        학습된 모델 저장
        
        Args:
            filepath: 저장할 파일 경로 (.pkl)
        """
        if self.item_similarity_matrix is None:
            raise ValueError("저장할 모델이 없습니다. fit()을 먼저 실행하세요.")
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'config': self.config,
            'item_similarity_matrix': self.item_similarity_matrix,
            'id_mapping': self.id_mapping
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        # 파일 크기 출력
        file_size = format_file_size(filepath)
        logger.info(f"✅ 모델 저장 완료: {filepath}")
        logger.info(f"📦 파일 크기: {file_size}")

    @classmethod
    def load(cls, filepath: str) -> 'ItemBasedRecommender':
        """
        저장된 모델 로드
        
        Args:
            filepath: 로드할 파일 경로 (.pkl)
        
        Returns:
            ItemBasedRecommender 객체
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {filepath}")
        
        # 파일 크기 출력
        file_size = format_file_size(filepath)
        logger.info(f"📂 모델 로드 중: {filepath}")
        logger.info(f"📦 파일 크기: {file_size}")
        
        # pickle 파일의 모듈 경로 호환성을 위한 alias 추가
        import sys
        import modeling.models.svd as svd_module
        import modeling.models.item_based as item_based_module
        sys.modules['models.svd'] = svd_module
        sys.modules['models.item_based'] = item_based_module
        sys.modules['models'] = sys.modules['modeling.models']
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        # 새 인스턴스 생성
        recommender = cls(config=model_data['config'])
        recommender.item_similarity_matrix = model_data['item_similarity_matrix']
        recommender.id_mapping = model_data.get('id_mapping', None)
        
        logger.info("✅ 모델 로드 완료")
        return recommender


# 사용 예시
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # 1. YAML 파일에서 설정 로드
    config = ItemBasedConfig.from_yaml()
    
    # 2. 추천 시스템 초기화 및 학습
    recommender = ItemBasedRecommender(config=config)
    recommender.fit()
    
    # 3. 영화 추천
    print("\n" + "="*50)
    print("🎬 영화 추천 테스트")
    print("="*50)
    
    # 영화 제목으로 추천
    movie_title = "기생충"
    print(f"\n'{movie_title}'와 유사한 영화 추천:")
    recommendations = recommender.recommend_by_title(
        movie_title,
        top_n=10,
        return_scores=True
    )
    
    if recommendations is not None:
        display_cols = ['movie_id', 'movie_title', 'similarity_score']
        print(recommendations[display_cols].to_string(index=False))
    
    # 4. 모델 저장
    save_path = Path(__file__).parent / 'pkls' / 'trained_item_based.pkl'
    recommender.save(save_path)
    
    # 5. 모델 로드 테스트
    print("\n" + "="*50)
    print("📂 모델 로드 테스트")
    print("="*50)
    loaded_recommender = ItemBasedRecommender.load(save_path)
    
    # 로드된 모델로 추천
    print(f"\n'{movie_title}'와 유사한 영화 추천 (로드된 모델):")
    recommendations = loaded_recommender.recommend_by_title(
        movie_title,
        top_n=5,
        return_scores=True
    )
    
    if recommendations is not None:
        display_cols = ['movie_id', 'movie_title', 'similarity_score']
        print(recommendations[display_cols].to_string(index=False))
