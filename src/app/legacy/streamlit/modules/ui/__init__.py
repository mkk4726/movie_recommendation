"""
레거시 Streamlit UI 레이어 초기화
"""

from .components import display_footer, display_movie_card, inject_custom_css
from .movie_based import render_movie_based_recommendation
from .rating_management import render_rating_management
from .sidebar import render_app_sidebar
from .user_based import render_user_based_recommendation

__all__ = [
    "display_footer",
    "display_movie_card",
    "inject_custom_css",
    "render_movie_based_recommendation",
    "render_rating_management",
    "render_app_sidebar",
    "render_user_based_recommendation",
]
