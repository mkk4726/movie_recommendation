"""
SVD 기반 영화 추천 시스템 파이프라인
"""
import pickle
import logging
import yaml
from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass

import pandas as pd
from surprise import SVD, Dataset, Reader, accuracy
from surprise.model_selection import train_test_split

import sys

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data_scraping.common.data_loader import load_ratings_data, load_movie_data
from modeling.utils.data import filter_by_min_counts
from modeling.utils.file_utils import format_file_size

# Logger 설정
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """SVD 모델 설정"""
    n_factors: int = 50
    n_epochs: int = 20
    lr_all: float = 0.005
    reg_all: float = 0.02
    random_state: int = 42
    verbose: bool = True
    test_size: float = 0.2
    min_user_ratings: int = 30
    min_movie_ratings: int = 10
    rating_scale: Tuple[float, float] = (0.5, 5.0)
    
    # 데이터 통합 설정
    use_integrated_data: bool = False
    
    @classmethod
    def from_yaml(cls, yaml_path: Optional[str] = None) -> 'ModelConfig':
        """
        YAML 파일에서 설정을 로드하여 ModelConfig 객체 생성
        
        Args:
            yaml_path: YAML 파일 경로 (None이면 기본 경로 사용)
            
        Returns:
            ModelConfig 객체
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
        
        # svd 섹션 추출
        if 'svd' not in config_dict:
            raise ValueError("config.yaml 파일에 'svd' 섹션이 없습니다.")
        
        svd_config = config_dict['svd']
        
        # rating_scale이 리스트로 로드되므로 튜플로 변환
        if 'rating_scale' in svd_config:
            svd_config['rating_scale'] = tuple(svd_config['rating_scale'])
        
        # 데이터 통합 설정 추출 (svd 섹션에서 직접 읽기)
        use_integrated_data = svd_config.get('use_integrated_data', False)
        
        # 데이터 통합 설정을 svd_config에 추가
        svd_config.update({
            'use_integrated_data': use_integrated_data
        })
        
        logger.info("✅ 설정 로드 완료")
        return cls(**svd_config)


@dataclass
class EvaluationMetrics:
    """모델 평가 지표"""
    train_rmse: float
    test_rmse: float
    train_mae: float
    test_mae: float
    user_overlap: float
    item_overlap: float
    
    def __str__(self):
        return f"""
=== 평가 결과 요약 ===
Train RMSE: {self.train_rmse:.4f}
Test RMSE:  {self.test_rmse:.4f}
Train MAE:  {self.train_mae:.4f}
Test MAE:   {self.test_mae:.4f}

User Overlap: {self.user_overlap:.2f}%
Item Overlap: {self.item_overlap:.2f}%
"""


class SVDRecommenderPipeline:
    """
    SVD 기반 영화 추천 시스템의 전체 파이프라인
    
    주요 기능:
    - 데이터 로딩 및 전처리
    - Train/Test 분할
    - SVD 모델 학습 및 평가
    - 영화 추천
    - 모델 저장/로드
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """
        Args:
            config: 모델 설정 (None이면 기본값 사용)
        """
        self.config = config or ModelConfig()
        self.df_filtered = None
        self.df_firebase = None
        self.trained_user_ids = None
        self.svd_model = None        
        self.metrics: Optional[EvaluationMetrics] = None
        
    def predict(self, user_id:str, movie_id:str) -> float:
        """
        특정 사용자와 영화에 대한 평점 예측
        
        Args:
            user_id: 사용자 ID
            movie_id: 영화 ID
            
        Returns:
            예측된 평점 (float)
        """
        if self.svd_model is None:
            raise ValueError("모델을 먼저 학습해주세요. run_full_pipeline() 실행 필요")
        
        prediction = self.svd_model.predict(user_id, movie_id)
        return prediction.est

    def prepare_surprise_dataset(self, df: pd.DataFrame) -> Dataset:
        """
        Surprise 라이브러리용 데이터셋 준비
        
        Args:
            df: 사용할 데이터프레임 (None이면 self.df_filtered 사용)
            
        Returns:
            Surprise Dataset 객체
        """        
        logger.info("=== Surprise Dataset 준비 ===")
        
        # Reader 객체 생성 (평점 범위 지정)
        reader = Reader(rating_scale=self.config.rating_scale)
        
        # DataFrame을 Surprise Dataset으로 변환
        self.surprise_data = Dataset.load_from_df(
            df[['user_id', 'movie_id', 'rating']],
            reader
        )
        
        logger.info("✅ 데이터셋 생성 완료")
        logger.info(f"  - 총 평점 수: {len(df):,}")
        logger.info(f"  - 평점 범위: {self.config.rating_scale[0]} ~ {self.config.rating_scale[1]}")
        
        return self.surprise_data
                
    def split_train_test(self, data: Dataset, firebase_data: Dataset) -> Tuple[Dataset, Dataset]:
        """
        Train/Test 데이터 분할
        
        Returns:
            (trainset, testset) 튜플
        """
       
        logger.info(f"=== Train/Test Split (test_size={self.config.test_size}) ===")

        trainset, testset = train_test_split(
            data,
            test_size=self.config.test_size,
            random_state=self.config.random_state
        )

        def dataset_to_df(dataset: Dataset) -> pd.DataFrame:
            df = pd.DataFrame(dataset.raw_ratings, columns=["user_id", "movie_id", "rating", "timestamp"])
            return df.drop(columns=["timestamp"], errors="ignore")

        df_train = dataset_to_df(data)
        df_firebase = dataset_to_df(firebase_data)
        df_train_merged = pd.concat([df_train, df_firebase], ignore_index=True)
        train_dataset = self.prepare_surprise_dataset(df_train_merged)
        trainset = train_dataset.build_full_trainset()
        
        logger.info("✅ 데이터 분할 완료")
        logger.info(f"  - Train set size: {trainset.n_ratings:,}")
        logger.info(f"  - Test set size: {len(testset):,}")
        logger.info("Train set 통계:")
        logger.info(f"  - 사용자 수: {trainset.n_users:,}")
        logger.info(f"  - 영화 수: {trainset.n_items:,}")
        logger.info(f"  - 평점 수: {trainset.n_ratings:,}")
        logger.info(f"  - 전체 셀 수: {trainset.n_users * trainset.n_items:,}")
        sparsity = (1 - trainset.n_ratings / (trainset.n_users * trainset.n_items)) * 100
        logger.info(f"  - Train Sparsity: {sparsity:.2f}%")
        
        return trainset, testset
    
    def train(self, trainset: Dataset) -> SVD:
        """
        SVD 모델 학습
        
        Returns:
            학습된 SVD 모델
        """        
        logger.info("=== SVD 모델 학습 ===")
        
        # SVD 하이퍼파라미터 출력
        logger.info("SVD 파라미터:")
        logger.info(f"  - n_factors: {self.config.n_factors}")
        logger.info(f"  - n_epochs: {self.config.n_epochs}")
        logger.info(f"  - lr_all: {self.config.lr_all}")
        logger.info(f"  - reg_all: {self.config.reg_all}")
        logger.info(f"  - random_state: {self.config.random_state}")
        logger.info(f"  - verbose: {self.config.verbose}")
        
        logger.info("학습 시작...")
        
        # SVD 모델 생성 및 학습
        self.svd_model = SVD(
            n_factors=self.config.n_factors,
            n_epochs=self.config.n_epochs,
            lr_all=self.config.lr_all,
            reg_all=self.config.reg_all,
            random_state=self.config.random_state,
            verbose=self.config.verbose
        )
        
        self.svd_model.fit(trainset)
        
        logger.info("✅ 학습 완료!")
        
        return self.svd_model
    
    def evaluate(self, trainset: Dataset, testset: Dataset):
        """
        모델 평가 (Train/Test RMSE, MAE)
        
        Returns:
            평가 지표가 담긴 EvaluationMetrics 객체
        """
        if self.svd_model is None:
            raise ValueError("모델을 먼저 학습해주세요. train() 실행 필요")
        
        logger.info("=== 모델 평가 ===")
        
        # Test set 평가
        logger.info("Test set 평가:")
        test_predictions = self.svd_model.test(testset)
        test_rmse = accuracy.rmse(test_predictions, verbose=True)
        test_mae = accuracy.mae(test_predictions, verbose=True)
        
        # Train set 평가 (overfitting 확인용)
        logger.info("Train set 평가:")
        train_testset = trainset.build_testset()
        train_predictions = self.svd_model.test(train_testset)
        train_rmse = accuracy.rmse(train_predictions, verbose=True)
        train_mae = accuracy.mae(train_predictions, verbose=True)
        
        # User-Item Overlap 계산
        train_users = set(trainset._raw2inner_id_users.keys())
        train_items = set(trainset._raw2inner_id_items.keys())
        test_users = set([uid for (uid, _, _) in testset])
        test_items = set([iid for (_, iid, _) in testset])
        
        user_overlap = len(train_users & test_users) / len(test_users) * 100
        item_overlap = len(train_items & test_items) / len(test_items) * 100
        
        # 평가 지표 저장
        self.metrics = EvaluationMetrics(
            train_rmse=train_rmse,
            test_rmse=test_rmse,
            train_mae=train_mae,
            test_mae=test_mae,
            user_overlap=user_overlap,
            item_overlap=item_overlap
        )
        
        logger.info(str(self.metrics))
        
        # Overfitting 체크
        if test_rmse - train_rmse > 0.1:
            logger.warning("⚠️  경고: Test RMSE가 Train RMSE보다 유의미하게 높습니다. Overfitting 가능성이 있습니다.")
        elif test_rmse - train_rmse < 0.05:
            logger.info("✅ Train과 Test 성능이 비슷합니다. 적절한 일반화가 이루어졌습니다.")
        else:
            logger.info("✅ Train과 Test 성능 차이가 적절한 수준입니다.")
            
    def recommend_for_user(
        self,
        user_id: str,
        df_movies: pd.DataFrame,
        n: int = 10
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        특정 사용자에게 영화 추천
        
        Args:
            user_id: 추천받을 사용자 ID
            df_movies: 영화 정보 데이터프레임
            n: 추천할 영화 개수
            
        Returns:
            (top_watched, recommendations) 튜플
            - top_watched: 사용자가 높게 평가한 영화 Top N
            - recommendations: 추천 영화 Top N
        """
        if self.svd_model is None:
            raise ValueError("모델을 먼저 학습해주세요. train() 실행 필요")

        if user_id not in self.trained_user_ids:
            raise ValueError(f"사용자 ID '{user_id}'를 찾을 수 없습니다.")
        
        # 사용자가 본 영화
        user_ratings = self.df_filtered[self.df_filtered['user_id'] == user_id]
        watched_movie_ids = set(user_ratings['movie_id'])
        
        # 사용자가 보지 않은 영화에 대해 예측
        all_movie_ids = set(self.df_filtered['movie_id'].unique())
        unseen_movie_ids = all_movie_ids - watched_movie_ids
        
        predictions = []
        for movie_id in unseen_movie_ids:
            pred = self.svd_model.predict(user_id, movie_id)
            predictions.append({
                'movie_id': movie_id,
                'predicted_rating': pred.est
            })
        
        # 추천 목록 생성
        recommendations = pd.DataFrame(predictions)
        recommendations = pd.merge(recommendations, df_movies, on='movie_id', how='left')
        recommendations = recommendations.sort_values('predicted_rating', ascending=False).head(n)
        
        # 사용자가 높게 평가한 영화
        top_watched = user_ratings.sort_values('rating', ascending=False).head(n)
        top_watched = pd.merge(top_watched, df_movies, on='movie_id', how='left')
        
        return top_watched, recommendations
    
    def save_model(self, filepath: str):
        """
        학습된 모델을 파일로 저장
        
        Args:
            filepath: 저장할 파일 경로
        """
        if self.svd_model is None:
            raise ValueError("저장할 모델이 없습니다. train() 먼저 실행 필요")
        
        # 저장할 데이터 준비
        model_data = {
            'config': self.config,
            'svd_model': self.svd_model,
            'metrics': self.metrics,
            'df_filtered': self.df_filtered,
            'trained_user_ids': self.trained_user_ids
        }
        
        # 디렉토리 생성
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 모델 저장
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        # 파일 크기 출력
        file_size = format_file_size(filepath)
        logger.info(f"✅ 모델 저장 완료: {filepath}")
        logger.info(f"📦 파일 크기: {file_size}")
        
    @classmethod
    def load_model(cls, filepath: str) -> 'SVDRecommenderPipeline':
        """
        저장된 모델을 로드
        
        Args:
            filepath: 로드할 파일 경로
            
        Returns:
            로드된 SVDRecommenderPipeline 객체
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
        
        # 파이프라인 객체 생성
        pipeline = cls(config=model_data['config'])
        pipeline.svd_model = model_data['svd_model']
        pipeline.metrics = model_data.get('metrics', None)
        pipeline.df_filtered = model_data.get('df_filtered', None)
        pipeline.trained_user_ids = model_data.get('trained_user_ids', [])
        
        logger.info("✅ 모델 로드 완료")
        if pipeline.metrics:
            logger.info(f"  - Test RMSE: {pipeline.metrics.test_rmse:.4f}")
            logger.info(f"  - Test MAE: {pipeline.metrics.test_mae:.4f}")
        
        return pipeline
    
    def run_full_pipeline(self, filtered_data: pd.DataFrame, firebase_data: pd.DataFrame):
        """
        전체 파이프라인 실행 (데이터 로딩 -> 전처리 -> 학습 -> 평가)
        
        Args:
            data_path: 데이터 경로
            
        Returns:
            평가 지표
        """
        logger.info("🚀 SVD 추천 시스템 파이프라인 시작")
        logger.info("=" * 60)

        self.df_filtered = filtered_data
        self.df_firebase = firebase_data
        
        trained_user_ids = []
        trained_user_ids.extend(filtered_data['user_id'].values.tolist())
        trained_user_ids.extend(firebase_data['user_id'].values.tolist())

        self.trained_user_ids = trained_user_ids

        filtered_data, firebase_data = self.prepare_surprise_dataset(filtered_data), self.prepare_surprise_dataset(firebase_data)

        trainset, testset = self.split_train_test(data=filtered_data, firebase_data=firebase_data)
        
        # 5. 모델 학습
        self.train(trainset)
        
        # 6. 모델 평가
        self.evaluate(trainset, testset)
        
        logger.info("=" * 60)
        logger.info("✅ 파이프라인 완료!")

# 간단한 사용 예시
if __name__ == "__main__":
    # Logger 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 모델 설정
    config = ModelConfig(
        n_factors=50,
        n_epochs=20,
        lr_all=0.005,
        reg_all=0.02,
        test_size=0.2,
        min_user_ratings=30,
        min_movie_ratings=10,
        verbose=True
    )
    
    # 파이프라인 생성 및 실행
    pipeline = SVDRecommenderPipeline(config)
    metrics = pipeline.run_full_pipeline()
    
    # 모델 저장
    model_path = Path(__file__).parent / 'pkls' / 'svd_model.pkl'
    pipeline.save_model(str(model_path))
    
    # 영화 데이터 로드 및 추천
    df_movies = load_movie_data()
    
    # 특정 사용자에게 추천
    user_id = pipeline.df_filtered['user_id'].iloc[0]
    top_watched, recommendations = pipeline.recommend_for_user(user_id, df_movies, n=5)
    
    logger.info("🎬 자주 본 영화 (내가 직접 본 영화 중 평점 상위):")
    logger.info("\n" + top_watched[['movie_title', 'rating', 'title']].to_string(index=False))
    
    logger.info("✨ 추천 영화 (아직 안 본 영화 중 예상 평점이 높은 순):")
    logger.info("\n" + recommendations[['title', 'predicted_rating', 'genre', 'year']].to_string(index=False))
