"""Cast 정보 처리 유틸리티."""

import pandas as pd


def build_cast_info(movie_cast: pd.DataFrame):
    """배우/감독/작가 행을 MovieCastInfo Pydantic 객체로 변환합니다.

    Args:
        movie_cast: 단일 영화의 cast 행들 (imdb_id 기준으로 미리 필터링된 DataFrame)

    Returns:
        MovieCastInfo 객체 (행이 없으면 빈 목록을 가진 객체 반환)
    """
    from app.api.schemas import CastMember, MovieCastInfo

    if movie_cast.empty:
        return MovieCastInfo()

    actors_data = (
        movie_cast[movie_cast["known_for_department"] == "Acting"].sort_values("cast_id").head(5)
    )
    actors = [
        CastMember(
            name=row["name"],
            original_name=row["original_name"],
            character=row["character"] if pd.notna(row["character"]) else None,
            profile_path=row["profile_path"] if pd.notna(row["profile_path"]) else None,
        )
        for _, row in actors_data.iterrows()
    ]

    directors_data = movie_cast[movie_cast["known_for_department"] == "Directing"].sort_values("cast_id")
    directors = [
        CastMember(
            name=row["name"],
            original_name=row["original_name"],
            character=None,
            profile_path=row["profile_path"] if pd.notna(row["profile_path"]) else None,
        )
        for _, row in directors_data.iterrows()
    ]

    writers_data = movie_cast[movie_cast["known_for_department"] == "Writing"].sort_values("cast_id")
    writers = [
        CastMember(
            name=row["name"],
            original_name=row["original_name"],
            character=None,
            profile_path=row["profile_path"] if pd.notna(row["profile_path"]) else None,
        )
        for _, row in writers_data.iterrows()
    ]

    return MovieCastInfo(actors=actors, directors=directors, writers=writers)
