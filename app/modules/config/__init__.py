"""
설정 값 모음
Streamlit 버전은 app/legacy/streamlit/modules/config/에 있습니다.
"""
import yaml
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DataConfig:
    """데이터 로딩 및 필터링 관련 설정"""
    min_user_ratings: int = 10
    min_movie_ratings: int = 30
    
    @classmethod
    def from_yaml(cls, yaml_path: Path = None) -> 'DataConfig':
        """
        YAML 파일에서 데이터 설정을 로드하여 DataConfig 객체 생성
        
        Args:
            yaml_path: YAML 파일 경로 (None이면 기본 경로 사용)
            
        Returns:
            DataConfig 객체
        """
        # 기본 경로 설정
        if yaml_path is None:
            yaml_path = Path(__file__).parent.parent.parent.parent / 'modeling' / 'utils' / 'data_config.yaml'
        else:
            yaml_path = Path(yaml_path)
        
        # YAML 파일 읽기
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
            
            # data 섹션 추출
            if 'data' not in config_dict:
                raise ValueError("data_config.yaml 파일에 'data' 섹션이 없습니다.")
            
            data_config = config_dict['data']
            return cls(
                min_user_ratings=data_config.get('min_user_ratings', 10),
                min_movie_ratings=data_config.get('min_movie_ratings', 30)
            )
        except FileNotFoundError:
            # 파일이 없으면 기본값 사용
            return cls()


# 전역 설정 인스턴스 (YAML에서 로드)
data_config = DataConfig.from_yaml()
