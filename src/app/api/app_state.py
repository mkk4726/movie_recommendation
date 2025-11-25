"""
애플리케이션 상태 관리 모듈
로딩 상태를 전역으로 관리합니다.
"""

import threading
from typing import Optional

# 로딩 상태 관리
_loading_state = {
    "is_loading": True,
    "loading_message": "애플리케이션 초기화 중...",
    "progress": {
        "model": False,
        "data": False,
        "search": False,
        "poster_search": False,
    },
}
_lock = threading.Lock()


def set_loading(is_loading: bool, message: Optional[str] = None):
    """
    로딩 상태를 설정합니다.

    Args:
        is_loading: 로딩 중 여부
        message: 로딩 메시지 (선택사항)
    """
    with _lock:
        _loading_state["is_loading"] = is_loading
        if message:
            _loading_state["loading_message"] = message


def set_progress(step: str, completed: bool):
    """
    특정 단계의 진행 상태를 설정합니다.

    Args:
        step: 단계 이름 ('model', 'data')
        completed: 완료 여부
    """
    with _lock:
        if step in _loading_state["progress"]:
            _loading_state["progress"][step] = completed


def get_loading_state() -> dict:
    """
    현재 로딩 상태를 반환합니다.

    Returns:
        로딩 상태 딕셔너리
    """
    with _lock:
        return _loading_state.copy()


def is_loading() -> bool:
    """
    현재 로딩 중인지 확인합니다.

    Returns:
        로딩 중이면 True
    """
    with _lock:
        return _loading_state["is_loading"]
