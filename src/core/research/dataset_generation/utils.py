import json
import os
from typing import Dict, List, Union

import pandas as pd


def parse_row_to_dict(cast_data: pd.DataFrame, row: pd.Series) -> dict:
    """영화 데이터 행을 딕셔너리로 변환"""
    tmdb_id = row["tmdb_id"]

    title = row["total_title"]
    original_title = row["original_title"]
    genres = row.get("genres_tmdb", "Unknown")
    overview = row.get("overview", "No overview available")
    release_year = str(row.get("release_date", "Unknown"))[:4] if row.get("release_date") else "Unknown"

    cast = cast_data[cast_data["tmdb_id"] == float(tmdb_id)]
    actor_data = cast[cast["known_for_department"] == "Acting"]["name"]
    actor = ", ".join(actor_data.head(10))
    director_data = cast[cast["known_for_department"] == "Director"]["name"]
    director = ", ".join(director_data)

    return {
        "title": title if title else "Unknown",
        "original_title": original_title if original_title else "Unknown",
        "genres": genres if genres else "Unknown",
        "overview": overview if overview else "No overview available",
        "director": director if director else "Unknown",
        "actors": actor if actor else "Unknown",
        "release_year": release_year if release_year else "Unknown",
    }


def save_queries_to_jsonl(queries: List[Dict], file_path: Union[str, None] = None, mode: str = "w") -> None:
    """
    쿼리 리스트를 JSONL 형식으로 저장

    Args:
        queries: 저장할 쿼리 딕셔너리 리스트
        file_path: 저장할 파일 경로 (None이면 기본 경로 사용)
        mode: 파일 쓰기 모드 ('w': 덮어쓰기, 'a': 추가)
    """
    # 경로가 제공되지 않으면 기본 경로 사용
    if file_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        file_path = get_queries_file_path(project_root)
        print(f"Using default path: {file_path}")

    # 디렉토리가 없으면 생성
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, mode, encoding="utf-8") as f:
        for query in queries:
            f.write(json.dumps(query, ensure_ascii=False) + "\n")

    print(f"Saved {len(queries)} queries to: {file_path}")


def append_query_to_jsonl(query: Dict, file_path: Union[str, None] = None) -> None:
    """
    단일 쿼리를 JSONL 파일에 추가 (실시간 저장용)

    Args:
        query: 저장할 쿼리 딕셔너리
        file_path: 저장할 파일 경로 (None이면 기본 경로 사용)
    """
    # 경로가 제공되지 않으면 기본 경로 사용
    if file_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        file_path = get_queries_file_path(project_root)

    # 디렉토리가 없으면 생성
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(query, ensure_ascii=False) + "\n")


def load_queries_from_jsonl(file_path: Union[str, None] = None) -> pd.DataFrame:
    """
    JSONL 파일을 읽어서 DataFrame으로 변환

    Args:
        file_path: 읽을 JSONL 파일 경로 (None이면 기본 경로 사용)

    Returns:
        쿼리 데이터가 담긴 DataFrame
    """
    # 경로가 제공되지 않으면 기본 경로 사용
    if file_path is None:
        # 현재 파일의 위치를 기준으로 프로젝트 루트를 찾음
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        file_path = get_queries_file_path(project_root)
        print(f"Using default path: {file_path}")

    queries = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:  # 빈 줄 무시
                queries.append(json.loads(line))

    df = pd.DataFrame(queries)
    print(f"Loaded {len(df)} queries from: {file_path}")
    return df


def get_queries_file_path(project_root: str, filename: str = "generated_queries.jsonl") -> str:
    """
    쿼리 파일 경로 생성

    Args:
        project_root: 프로젝트 루트 디렉토리
        filename: 파일명 (기본값: generated_queries.jsonl)

    Returns:
        전체 파일 경로
    """
    return os.path.join(project_root, "dataset_generation", "data", filename)
