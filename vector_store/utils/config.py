"""
Vector Store Configuration Loader

YAML 파일에서 설정을 로드하는 유틸리티 함수
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    YAML 설정 파일 로드

    Args:
        config_path: 설정 파일 경로. None이면 기본 경로 사용

    Returns:
        설정 딕셔너리
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def get_index_path(config: Dict[str, Any] = None) -> Path:
    """인덱스 파일 경로 반환"""
    if config is None:
        config = load_config()

    base_dir = Path(config["index"]["base_dir"])

    # 상대 경로인 경우 프로젝트 루트 기준으로 절대 경로 생성
    if not base_dir.is_absolute():
        # vector_store/utils/config.py 기준으로 프로젝트 루트는 2단계 위
        project_root = Path(__file__).resolve().parent.parent.parent
        base_dir = project_root / base_dir

    index_file = config["index"]["index_file"]
    return base_dir / index_file


def get_embeddings_path(config: Dict[str, Any] = None) -> Path:
    """임베딩 파일 경로 반환"""
    if config is None:
        config = load_config()

    base_dir = Path(config["index"]["base_dir"])

    # 상대 경로인 경우 프로젝트 루트 기준으로 절대 경로 생성
    if not base_dir.is_absolute():
        # vector_store/utils/config.py 기준으로 프로젝트 루트는 2단계 위
        project_root = Path(__file__).resolve().parent.parent.parent
        base_dir = project_root / base_dir

    embeddings_file = config["index"]["embeddings_file"]
    return base_dir / embeddings_file
