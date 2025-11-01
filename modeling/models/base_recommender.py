"""
추천 시스템 추상 기본 클래스
"""
import pickle
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd

from modeling.utils.file_utils import format_file_size

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
        
        # 저장할 데이터 준비
        model_data = self._prepare_save_data()
        
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
        
        # pickle 파일의 모듈 경로 호환성을 위한 alias 추가
        import sys
        import modeling.models.svd as svd_module
        import modeling.models.item_based as item_based_module
        import modeling.models.base_recommender as base_recommender_module
        sys.modules['models.svd'] = svd_module
        sys.modules['models.item_based'] = item_based_module
        sys.modules['models.base_recommender'] = base_recommender_module
        sys.modules['models'] = sys.modules['modeling.models']
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        # 모델 객체 생성
        config = model_data.get('config', None)
        model = cls(config=config)
        
        # 추가 데이터 로드 (서브클래스에서 필요시 오버라이드)
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

