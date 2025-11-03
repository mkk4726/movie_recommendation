"""
추천 시스템 추상 기본 클래스
"""
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

from modeling.utils.file_utils import format_file_size

# joblib은 numpy 배열 직렬화에 최적화되어 있어 pickle보다 빠름
import joblib

logger = logging.getLogger(__name__)


class BaseRecommender(ABC):
    """
    추천 시스템의 추상 기본 클래스
    
    모든 추천 시스템이 공통으로 가져야 하는 기능을 정의합니다:
    - 모델 저장/로드
    - 설정 관리
    - 로깅
    """
    
    def __init__(self, config=None):
        """
        Args:
            config: 모델 설정 객체 (None이면 각 서브클래스의 기본 설정 사용)
        """
        self.config = config
    
    @abstractmethod
    def fit(self, *args, **kwargs):
        """
        모델 학습 (서브클래스에서 구현 필수)
        """
        pass
    
    @abstractmethod
    def predict(self, *args, **kwargs):
        """
        평점 또는 점수 예측 (서브클래스에서 구현 필수)
        """
        pass
    
    def _prepare_save_data(self) -> dict:
        """
        저장할 데이터 준비 (서브클래스에서 필요시 오버라이드)
        
        Returns:
            저장할 데이터를 담은 딕셔너리
        """
        return {
            'config': self.config,
        }
    
    def _load_saved_data(self, model_data: dict):
        """
        저장된 데이터 로드 (서브클래스에서 필요시 오버라이드)
        
        Args:
            model_data: 로드된 모델 데이터 딕셔너리
        """
        self.config = model_data.get('config', None)
    
    def save_model(self, filepath: str):
        """
        학습된 모델을 파일로 저장
        
        Args:
            filepath: 저장할 파일 경로
        """
        if not hasattr(self, 'config') or self.config is None:
            raise ValueError("저장할 모델이 없습니다. fit() 먼저 실행 필요")
        
        logger.info("💾 모델 저장 시작...")
        save_start_time = time.time()
        
        # 저장할 데이터 준비
        prep_start_time = time.time()
        model_data = self._prepare_save_data()
        prep_time = time.time() - prep_start_time
        logger.debug(f"  - 데이터 준비: {prep_time:.2f}초")
        
        # 디렉토리 생성
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 모델 저장 (joblib이 numpy 배열 직렬화에 더 효율적)
        serialize_start_time = time.time()
        logger.debug("  - joblib 사용 (numpy 배열 최적화)")
        joblib.dump(model_data, filepath, compress=3)  # compress=3은 속도/크기 균형
        serialize_time = time.time() - serialize_start_time
        logger.debug(f"  - joblib 직렬화: {serialize_time:.2f}초")
        
        # 파일 크기 출력
        file_size = format_file_size(filepath)
        total_time = time.time() - save_start_time
        logger.info(f"✅ 모델 저장 완료: {filepath}")
        logger.info(f"📦 파일 크기: {file_size}")
        logger.info(f"⏱️  저장 소요 시간: {total_time:.2f}초 (준비: {prep_time:.2f}초, 직렬화: {serialize_time:.2f}초)")
    
    @classmethod
    def load_model(cls, filepath: str):
        """
        저장된 모델을 로드
        
        Args:
            filepath: 로드할 파일 경로
            
        Returns:
            로드된 모델 객체
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {filepath}")
        
        # 파일 크기 출력
        file_size = format_file_size(filepath)
        logger.info(f"📂 모델 로드 중: {filepath}")
        logger.info(f"📦 파일 크기: {file_size}")
        logger.info(f"🔧 모델 클래스: {cls.__name__}")
        
        # pickle 파일의 모듈 경로 호환성을 위한 alias 추가
        logger.debug("🔗 모듈 경로 alias 설정 중...")
        import sys
        import modeling.models.svd as svd_module
        import modeling.models.item_based as item_based_module
        import modeling.models.base_recommender as base_recommender_module
        sys.modules['models.svd'] = svd_module
        sys.modules['models.item_based'] = item_based_module
        sys.modules['models.base_recommender'] = base_recommender_module
        sys.modules['models'] = sys.modules['modeling.models']
        logger.debug("✅ 모듈 경로 alias 설정 완료")
        
        logger.info("💾 모델 파일 읽는 중...")
        load_start_time = time.time()
        
        model_data = joblib.load(filepath)
        logger.debug("  - joblib으로 로드됨")
        
        load_time = time.time() - load_start_time
        logger.debug(f"  - 파일 로드: {load_time:.2f}초")
        logger.debug(f"📊 로드된 데이터 키: {list(model_data.keys())}")
        
        # 모델 객체 생성
        logger.info("🏗️ 모델 객체 생성 중...")
        config = model_data.get('config', None)
        if config:
            logger.debug(f"⚙️ 모델 설정 확인됨: {type(config).__name__}")
        model = cls(config=config)
        
        # 추가 데이터 로드 (서브클래스에서 필요시 오버라이드)
        logger.debug("📥 추가 모델 데이터 로드 중...")
        model._load_saved_data(model_data)
        
        logger.info("✅ 모델 로드 완료")
        
        return model
    
    def validate_model_loaded(self):
        """
        모델이 로드되었는지 검증 (서브클래스에서 필요시 사용)
        
        Raises:
            ValueError: 모델이 로드되지 않은 경우
        """
        # 기본 구현: config만 확인
        if not hasattr(self, 'config') or self.config is None:
            raise ValueError("모델을 먼저 학습하거나 로드해주세요.")
    
    def get_config(self):
        """
        현재 설정 반환
        
        Returns:
            설정 객체
        """
        return self.config
    
    def set_config(self, config):
        """
        설정 업데이트
        
        Args:
            config: 새로운 설정 객체
        """
        self.config = config
        logger.info("✅ 설정 업데이트 완료")

