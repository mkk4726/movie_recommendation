"""
OMDb API 데이터 저장/로드 유틸리티
JSONL 형식으로 OMDb API 응답 데이터를 저장하고 관리합니다.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


def get_omdb_data_path() -> Path:
    """OMDb API 데이터 저장 디렉토리 경로를 반환"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    data_dir = project_root / "data_scraping" / "data" / "omdb"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_omdb_jsonl_file() -> Path:
    """OMDb 데이터 JSONL 파일 경로를 반환"""
    return get_omdb_data_path() / "omdb_data.jsonl"


def save_omdb_data(omdb_dict: Dict[str, Any], check_duplicate: bool = True) -> bool:
    """
    OMDb API 응답을 JSONL 형식으로 저장
    JSONL: 한 줄에 하나의 JSON 객체 (append 가능)

    .txt 파일보다 효율적인 이유:
    1. 구조화된 JSON 형식으로 파싱 쉬움
    2. append 모드로 대량 데이터 저장 가능
    3. imdbID 기반 중복 체크 가능
    4. 나중에 DataFrame으로 변환 용이

    Args:
        omdb_dict: OMDb API 응답 딕셔너리
        check_duplicate: 이미 저장된 데이터인지 체크 (기본값: True)

    Returns:
        저장 성공 여부
    """
    if not omdb_dict or omdb_dict.get("Response") == "False":
        return False

    imdb_id = omdb_dict.get("imdbID", "")
    if not imdb_id:
        return False

    jsonl_file = get_omdb_jsonl_file()

    # 중복 체크
    if check_duplicate and jsonl_file.exists():
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    existing = json.loads(line.strip())
                    if existing.get("imdbID") == imdb_id:
                        return False  # 이미 존재함
                except json.JSONDecodeError:
                    continue

    # JSONL 형식으로 저장 (한 줄에 하나의 JSON 객체)
    with open(jsonl_file, "a", encoding="utf-8") as f:
        json.dump(omdb_dict, f, ensure_ascii=False)
        f.write("\n")

    return True


def load_omdb_data(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    저장된 OMDb API 데이터를 DataFrame으로 로드

    Args:
        data_path: OMDb 데이터 디렉토리 경로 (None이면 자동 탐색)

    Returns:
        OMDb 메타데이터 DataFrame
    """
    if data_path is None:
        jsonl_file = get_omdb_jsonl_file()
    else:
        jsonl_file = Path(data_path) / "omdb_data.jsonl"

    if not jsonl_file.exists():
        return pd.DataFrame()

    records = []
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    # Response가 False인 것은 제외
                    if record.get("Response") != "False":
                        records.append(record)
                except json.JSONDecodeError:
                    continue

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # 중복 제거 (imdbID 기준, 최신 것 유지)
    if "imdbID" in df.columns:
        df = df.drop_duplicates(subset=["imdbID"], keep="last").reset_index(drop=True)

    return df


def get_stored_imdb_ids(data_path: Optional[str] = None) -> set:
    """
    이미 저장된 IMDb ID 목록을 반환 (중복 체크용)

    Args:
        data_path: OMDb 데이터 디렉토리 경로 (None이면 자동 탐색)

    Returns:
        저장된 IMDb ID set
    """
    if data_path is None:
        jsonl_file = get_omdb_jsonl_file()
    else:
        jsonl_file = Path(data_path) / "omdb_data.jsonl"

    if not jsonl_file.exists():
        return set()

    imdb_ids = set()
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    imdb_id = record.get("imdbID")
                    if imdb_id:
                        imdb_ids.add(imdb_id)
                except json.JSONDecodeError:
                    continue

    return imdb_ids
