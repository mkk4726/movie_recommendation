"""
설정 값 모음
Streamlit 버전은 app/legacy/streamlit/modules/config/에 있습니다.
"""
from dataclasses import dataclass


@dataclass
class DataConfig:
    """데이터 로딩 및 필터링 관련 설정"""
    # 최소 평점 개수 필터링 기준
    min_user_ratings: int = 30
    min_movie_ratings: int = 10


# 전역 설정 인스턴스
data_config = DataConfig()
