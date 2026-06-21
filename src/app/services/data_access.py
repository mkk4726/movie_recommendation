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
