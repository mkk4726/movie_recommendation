"""
Re-exports from core.db.data_access for backward compatibility.
Data access logic lives in core so pipelines can use it directly.
"""

from core.db.data_access import (  # noqa: F401
    load_movie_data,
    load_cast_data,
    user_exists,
    get_popular_movie_ids,
    get_sample_user_ids,
    search_movies_cached,
    get_data_stats,
    invalidate_data_cache,
)


def load_all_data(min_user_ratings=None, min_movie_ratings=None):
    """영화 데이터를 반환합니다. ratings는 더 이상 메모리에 올리지 않습니다."""
    return load_movie_data(), None, None
