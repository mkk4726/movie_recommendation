"""
YAML 설정 파일 로더
"""
import streamlit as st
from pathlib import Path
import yaml


def _load_config_file():
    """
    config.yaml 파일을 직접 로드합니다 (캐싱 없음).
    내부 구현용 함수입니다.
    """
    config_path = Path(__file__).parent / "config.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


@st.cache_data
def load_config():
    """
    config.yaml 파일을 로드합니다.
    
    Returns:
        dict: 설정값 딕셔너리
    """
    return _load_config_file()


def get_config():
    """
    캐시된 설정을 반환합니다.
    Streamlit 컨텍스트 밖에서는 파일을 직접 로드합니다.
    """
    try:
        # Streamlit 컨텍스트 내에서 캐시 사용 시도
        return load_config()
    except (AttributeError, AssertionError):
        # Streamlit 컨텍스트 밖에서는 직접 로드
        return _load_config_file()


# 하위 호환성을 위한 상수들 (지연 로딩)
def _init_constants():
    """상수를 초기화합니다."""
    global GENRE_OPTIONS, COUNTRY_OPTIONS, MIN_YEAR, MAX_YEAR
    _config_data = get_config()
    GENRE_OPTIONS = _config_data["genre_options"]
    COUNTRY_OPTIONS = _config_data["country_options"]
    year_filter = _config_data["year_filter"]
    MIN_YEAR = year_filter["min_year"]
    MAX_YEAR = year_filter["max_year"]


# 모듈이 처음 import될 때 상수 초기화
_init_constants()
