"""영화 데이터프레임 공통 필터링 유틸리티."""

from typing import List, Optional

import pandas as pd


def apply_movie_filters(
    df: pd.DataFrame,
    *,
    genre: Optional[List[str]] = None,
    language: Optional[List[str]] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_rating: float = 0.0,
    min_vote_count: int = 0,
) -> pd.DataFrame:
    """영화 DataFrame에 공통 필터를 적용합니다.

    Args:
        df: 필터링할 영화 DataFrame
        genre: 포함할 장르 목록 (genres_tmdb 컬럼 기준)
        language: 포함할 언어 코드 목록
        min_year: 최소 개봉 연도 (포함)
        max_year: 최대 개봉 연도 (포함)
        min_rating: 최소 평균 평점 (0이면 미적용)
        min_vote_count: 최소 평점 개수 (0이면 미적용)

    Returns:
        필터가 적용된 DataFrame (원본 변경 없음)
    """
    result = df

    if genre:
        genre_list = [genre] if isinstance(genre, str) else genre
        genre_col = "genres_tmdb" if "genres_tmdb" in result.columns else "genres"
        if genre_col in result.columns:
            result = result[
                result[genre_col].apply(
                    lambda x: any(g in str(x) for g in genre_list) if pd.notna(x) else False
                )
            ]

    if language:
        lang_list = [language] if isinstance(language, str) else language
        if "language" in result.columns:
            result = result[
                result["language"].apply(
                    lambda x: any(lang in str(x) for lang in lang_list) if pd.notna(x) else False
                )
            ]

    if min_year is not None and "year" in result.columns:
        result = result[result["year"] >= min_year]

    if max_year is not None and "year" in result.columns:
        result = result[result["year"] <= max_year]

    if min_rating > 0 and "vote_average" in result.columns:
        result = result[result["vote_average"] >= min_rating]

    if min_vote_count > 0 and "vote_count" in result.columns:
        result = result[result["vote_count"] >= min_vote_count]

    return result
