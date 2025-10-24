"""
파일 관련 유틸리티 함수들
"""
from pathlib import Path
from typing import Union


def format_file_size(file_path: Union[str, Path, int]) -> str:
    """
    파일 크기를 읽기 쉬운 형식으로 변환
    
    Args:
        file_path: 파일 경로(str/Path) 또는 파일 크기(int, bytes)
    
    Returns:
        포맷된 파일 크기 문자열 (예: "1.23 MB", "456.78 KB")
    
    Examples:
        >>> format_file_size(1024)
        '1.00 KB'
        >>> format_file_size(Path('model.pkl'))
        '15.34 MB'
        >>> format_file_size('data/model.pkl')
        '15.34 MB'
    """
    # 파일 경로가 주어진 경우 크기 계산
    if isinstance(file_path, (str, Path)):
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        file_size_bytes = file_path.stat().st_size
    else:
        file_size_bytes = file_path
    
    # 크기에 따라 적절한 단위로 변환
    if file_size_bytes < 1024:
        return f"{file_size_bytes} bytes"
    elif file_size_bytes < 1024**2:
        return f"{file_size_bytes / 1024:.2f} KB"
    elif file_size_bytes < 1024**3:
        return f"{file_size_bytes / (1024**2):.2f} MB"
    else:
        return f"{file_size_bytes / (1024**3):.2f} GB"

