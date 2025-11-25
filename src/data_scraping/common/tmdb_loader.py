"""
TMDB API 데이터 저장/로드 유틸리티
JSONL 형식으로 TMDB API 응답 데이터를 저장하고 관리합니다.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

# To-Do
# https://image.tmdb.org/t/p/{size}{poster_path}
# poster_url은 이렇게 매핑해서 사용하면 됨.
# IMDB url : https://www.imdb.com/title/{IMDB_id}/

# TMDB 장르 ID와 한글명 매핑 사전
TMDB_GENRES = {
    28: "액션",  # Action
    12: "모험",  # Adventure
    16: "애니메이션",  # Animation
    35: "코미디",  # Comedy
    80: "범죄",  # Crime
    99: "다큐멘터리",  # Documentary
    18: "드라마",  # Drama
    10751: "가족",  # Family
    14: "판타지",  # Fantasy
    36: "역사",  # History
    27: "공포",  # Horror
    10402: "음악",  # Music
    9648: "미스터리",  # Mystery
    10749: "로맨스",  # Romance
    878: "SF",  # Science Fiction
    10770: "TV 영화",  # TV Movie
    53: "스릴러",  # Thriller
    10752: "전쟁",  # War
    37: "서부",  # Western
}

TMDB_LANGUAGE = {
    "en": "영어",
    "ko": "한국어",
    "ja": "일본어",
    "zh": "중국어",
    "fr": "프랑스어",
    "de": "독일어",
    "es": "스페인어",
    "it": "이탈리아어",
    "ru": "러시아어",
    "pt": "포르투갈어",
    "hi": "힌디어 (인도)",
    "ar": "아랍어",
    "tr": "터키어",
    "th": "태국어",
    "vi": "베트남어",
    "id": "인도네시아어",
    "pl": "폴란드어",
    "nl": "네덜란드어",
    "sv": "스웨덴어",
    "da": "덴마크어",
    "no": "노르웨이어",
    "fi": "핀란드어",
    "he": "히브리어",
    "cs": "체코어",
    "el": "그리스어",
    "hu": "헝가리어",
    "fa": "페르시아어 (이란)",
    "ta": "타밀어",
    "te": "텔루구어",
    "ml": "말라얄람어",
    "bn": "벵골어 (방글라데시)",
    "uk": "우크라이나어",
    "ro": "루마니아어",
}


def get_tmdb_data_path() -> Path:
    """TMDB API 데이터 저장 디렉토리 경로를 반환"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    data_dir = project_root / "data_scraping" / "data" / "tmdb"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_tmdb_jsonl_file() -> Path:
    """TMDB 데이터 JSONL 파일 경로를 반환"""
    return get_tmdb_data_path() / "tmdb_data.jsonl"


def _extract_imdb_id(tmdb_dict: Dict[str, Any]) -> Optional[str]:
    """
    TMDB 결과에서 IMDb ID를 추출

    Args:
        tmdb_dict: TMDB API 응답 딕셔너리 (단일 영화/TV 객체)

    Returns:
        IMDb ID 문자열 (예: "tt26812510") 또는 None
    """
    imdb_id = tmdb_dict.get("imdb_id")
    if imdb_id:
        return imdb_id

    return None


def save_tmdb_data(tmdb_dict: Dict[str, Any], check_duplicate: bool = True) -> bool:
    """
    TMDB API 응답을 JSONL 형식으로 저장
    JSONL: 한 줄에 하나의 JSON 객체 (append 가능)

    .txt 파일보다 효율적인 이유:
    1. 구조화된 JSON 형식으로 파싱 쉬움
    2. append 모드로 대량 데이터 저장 가능
    3. imdb_id 기반으로 중복 체크 가능
    4. 나중에 DataFrame으로 변환 용이

    Args:
        tmdb_dict: TMDB API 응답 딕셔너리 (단일 영화/TV 객체)
        check_duplicate: 이미 저장된 데이터인지 체크 (기본값: True)

    Returns:
        저장 성공 여부
    """
    if not tmdb_dict:
        return False

    imdb_id = _extract_imdb_id(tmdb_dict)
    if not imdb_id:
        return False

    jsonl_file = get_tmdb_jsonl_file()

    # 중복 체크 (imdb_id 기준)
    if check_duplicate and jsonl_file.exists():
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        existing = json.loads(line)
                        existing_imdb_id = _extract_imdb_id(existing)
                        if existing_imdb_id == imdb_id:
                            return False  # 이미 존재함
                    except json.JSONDecodeError:
                        continue

    # JSONL 형식으로 저장 (한 줄에 하나의 JSON 객체)
    with open(jsonl_file, "a", encoding="utf-8") as f:
        json.dump(tmdb_dict, f, ensure_ascii=False)
        f.write("\n")

    return True


def load_tmdb_data(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    저장된 TMDB API 데이터를 DataFrame으로 로드

    Args:
        data_path: TMDB 데이터 디렉토리 경로 (None이면 자동 탐색)

    Returns:
        TMDB 메타데이터 DataFrame
    """
    if data_path is None:
        jsonl_file = get_tmdb_jsonl_file()
    else:
        jsonl_file = Path(data_path) / "tmdb_data.jsonl"

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

    # 중복 제거 (imdb_id 기준, 최신 것 유지)
    if "imdb_id" in df.columns:
        df = df.drop_duplicates(subset=["imdb_id"], keep="last").reset_index(drop=True)

    # 장르 ID를 한글명으로 매핑
    if "genre_ids" in df.columns:
        df["genres"] = df["genre_ids"].apply(
            lambda x: " ".join([TMDB_GENRES.get(gid, str(gid)) for gid in x]) if isinstance(x, list) else ""
        )

    # 언어 코드를 한글명으로 매핑
    if "original_language" in df.columns:
        df["language"] = df["original_language"].map(TMDB_LANGUAGE)

    return df


def get_stored_tmdb_imdb_ids(data_path: Optional[str] = None) -> set:
    """
    이미 저장된 TMDB 데이터의 IMDb ID 목록을 반환 (중복 체크용)

    Args:
        data_path: TMDB 데이터 디렉토리 경로 (None이면 자동 탐색)

    Returns:
        저장된 IMDb ID set (예: {"tt26812510", "tt0114709"})
    """
    if data_path is None:
        jsonl_file = get_tmdb_jsonl_file()
    else:
        jsonl_file = Path(data_path) / "tmdb_data.jsonl"

    if not jsonl_file.exists():
        return set()

    imdb_ids = set()
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    imdb_id = _extract_imdb_id(record)
                    if imdb_id:
                        imdb_ids.add(imdb_id)
                except json.JSONDecodeError:
                    continue

    return imdb_ids


def get_stored_tmdb_movie_ids(data_path: Optional[str] = None) -> set:
    """
    이미 저장된 TMDB 영화 ID 목록을 반환 (영화만 필터링)

    Args:
        data_path: TMDB 데이터 디렉토리 경로 (None이면 자동 탐색)

    Returns:
        저장된 TMDB 영화 ID set (숫자만)
    """
    df = load_tmdb_data(data_path)
    if df.empty:
        return set()

    # movie 결과만 필터링 (media_type이 'movie'인 것)
    if "media_type" in df.columns:
        movie_df = df[df["media_type"] == "movie"]
    else:
        # media_type 정보가 없으면 빈 set 반환
        return set()

    if "id" in movie_df.columns:
        return set(movie_df["id"].dropna().astype(int).astype(str))

    return set()
