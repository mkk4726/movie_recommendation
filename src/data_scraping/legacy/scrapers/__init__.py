"""Scrapers for movie data."""

from .custom_rating_scraper import CustomRatingScraper
from .movie_comments_scraper import MovieCommentsScraper
from .movie_info_scraper import MovieInfoScraper

__all__ = [
    "MovieInfoScraper",
    "MovieCommentsScraper",
    "CustomRatingScraper",
]
