"""Scrapers for movie data."""

from .movie_info_scraper import MovieInfoScraper
from .movie_comments_scraper import MovieCommentsScraper
from .custom_rating_scraper import CustomRatingScraper

__all__ = [
    "MovieInfoScraper",
    "MovieCommentsScraper",
    "CustomRatingScraper",
]

