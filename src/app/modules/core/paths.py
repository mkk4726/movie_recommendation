"""
경로 관리 모듈
프로젝트 전체의 sys.path 관리를 중앙화합니다.
"""

import sys
from pathlib import Path


def get_project_paths():
    """
    프로젝트 루트 및 app 디렉토리 경로 반환

    Returns:
        tuple: (project_root, app_dir)
    """
    # 현재 파일의 위치에서 프로젝트 루트 계산
    current_file = Path(__file__).resolve()
    # core/ -> modules/ -> app/ -> 프로젝트 루트
    project_root = current_file.parents[3]
    app_dir = project_root / "app"

    return project_root, app_dir


def add_project_paths():
    """
    프로젝트 루트 및 app 디렉토리를 sys.path에 추가

    이 함수는 한 번만 호출하면 됩니다. 여러 번 호출해도 안전합니다.

    Returns:
        tuple: (project_root, app_dir)
    """
    project_root, app_dir = get_project_paths()

    # sys.path에 추가 (중복 체크)
    for path in (project_root, app_dir):
        str_path = str(path)
        if str_path not in sys.path:
            sys.path.insert(0, str_path)

    return project_root, app_dir


# 모듈이 처음 import될 때 자동으로 경로 추가
PROJECT_ROOT, APP_DIR = add_project_paths()
