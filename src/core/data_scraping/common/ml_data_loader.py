"""
ML-32M 데이터셋을 사용
"""

from pathlib import Path

import pandas as pd


def get_ml32m_data_path() -> Path:
    """ML-32M 데이터 디렉토리 경로를 반환"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    ml32m_dir = project_root / "data_scraping" / "data" / "ml-32m"
    return ml32m_dir


def load_movie_data_ml(data_path: str = None) -> pd.DataFrame:
    """
    ML-32M 영화 정보 데이터 로딩
    movies.csv 파일을 읽어서 기존 형식과 호환되는 형태로 변환

    Args:
        data_path: ML-32M 디렉토리 경로 (None이면 자동 탐색)

    Returns:
        영화 정보 DataFrame
    """
    if data_path is None:
        ml32m_dir = get_ml32m_data_path()
    else:
        ml32m_dir = Path(data_path)

    movies_file = ml32m_dir / "movies.csv"

    if not movies_file.exists():
        raise FileNotFoundError(f"ML-32M movies.csv 파일을 찾을 수 없습니다: {movies_file}")

    # CSV 읽기
    df_movies = pd.read_csv(movies_file)

    if df_movies.empty:
        return df_movies

    # 컬럼명을 소문자로 변환하고 기존 형식에 맞게 매핑
    column_mapping = {"movieId": "movie_id"}
    df_movies = df_movies.rename(columns=column_mapping)

    # movie_id를 문자열로 변환
    df_movies["movie_id"] = df_movies["movie_id"].astype(str)

    # 장르를 공백으로 구분된 문자열로 변환 (예: "Action|Adventure" -> "Action Adventure")
    df_movies["genres"] = df_movies["genres"].str.replace("|", " ", regex=False)
    df_movies["genres"] = df_movies["genres"].str.replace("(no genres listed)", "", regex=False)
    df_movies["genres"] = df_movies["genres"].str.strip()

    # 중복 제거 및 재정렬
    df_movies = df_movies.drop_duplicates(subset=["movie_id"], keep="first").reset_index(drop=True)

    return df_movies.reset_index(drop=True, inplace=False)


def load_ratings_data_ml(data_path: str = None) -> pd.DataFrame:
    """
    ML-32M 사용자 평점 데이터 로딩
    ratings.csv 파일을 읽어서 기존 형식과 호환되는 형태로 변환

    Args:
        data_path: ML-32M 디렉토리 경로 (None이면 자동 탐색)

    Returns:
        평점 정보 DataFrame
    """
    if data_path is None:
        ml32m_dir = get_ml32m_data_path()
    else:
        ml32m_dir = Path(data_path)

    ratings_file = ml32m_dir / "ratings.csv"

    if not ratings_file.exists():
        raise FileNotFoundError(f"ML-32M ratings.csv 파일을 찾을 수 없습니다: {ratings_file}")

    # CSV 읽기
    df_ratings = pd.read_csv(ratings_file)

    if df_ratings.empty:
        return df_ratings

    # 컬럼명을 소문자로 변환하고 기존 형식에 맞게 매핑
    column_mapping = {"userId": "user_id", "movieId": "movie_id", "rating": "rating"}
    df_ratings = df_ratings.rename(columns=column_mapping)

    # user_id와 movie_id를 문자열로 변환
    df_ratings["user_id"] = df_ratings["user_id"].astype(str)
    df_ratings["movie_id"] = df_ratings["movie_id"].astype(str)

    # ML-32M 평점은 0.5~5.0 범위이므로 0~5 범위로 유지
    # (기존 코드에서 이미 0~5 범위로 필터링하므로 그대로 사용 가능)

    # 필터링: 유효한 평점만 유지
    df_ratings = df_ratings[(df_ratings["rating"] >= 0) & (df_ratings["rating"] <= 5)]
    df_ratings = df_ratings.dropna(subset=["rating"])

    return df_ratings.reset_index(drop=True, inplace=False)


def load_links_data_ml(data_path: str = None) -> pd.DataFrame:
    """
    ML-32M 영화 링크 데이터 로딩
    links.csv 파일을 읽어서 기존 형식과 호환되는 형태로 변환

    Args:
        data_path: ML-32M 디렉토리 경로 (None이면 자동 탐색)

    Returns:
        링크 정보 DataFrame (movieId, imdbId, tmdbId)
    """
    if data_path is None:
        ml32m_dir = get_ml32m_data_path()
    else:
        ml32m_dir = Path(data_path)

    links_file = ml32m_dir / "links.csv"

    if not links_file.exists():
        raise FileNotFoundError(f"ML-32M links.csv 파일을 찾을 수 없습니다: {links_file}")

    # CSV 읽기
    df_links = pd.read_csv(links_file)

    if df_links.empty:
        return df_links

    # 컬럼명을 소문자로 변환하고 기존 형식에 맞게 매핑
    column_mapping = {"movieId": "movie_id", "imdbId": "imdb_id", "tmdbId": "tmdb_id"}
    df_links = df_links.rename(columns=column_mapping)

    # movie_id를 문자열로 변환
    df_links["movie_id"] = df_links["movie_id"].astype(str)

    # imdb_id를 'tt' 접두사 + 7자리 숫자 형식으로 변환 (예: 114709 -> tt0114709)
    if "imdb_id" in df_links.columns:

        def format_imdb_id(imdb_id):
            if pd.isna(imdb_id) or imdb_id == "":
                return ""
            try:
                return f"tt{int(float(imdb_id)):07d}"
            except (ValueError, TypeError):
                # 이미 'tt' 형식이거나 변환 불가능한 경우 그대로 반환
                return str(imdb_id)

        df_links["imdb_id"] = df_links["imdb_id"].apply(format_imdb_id)
    if "tmdb_id" in df_links.columns:
        df_links["tmdb_id"] = df_links["tmdb_id"].fillna("").astype(str).replace("nan", "")

    return df_links.reset_index(drop=True, inplace=False)
