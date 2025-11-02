"""Common utilities for movie data loading."""

from .data_loader import load_movie_data, load_ratings_data, get_ml32m_data_path
from .exceptions import ScrapingError, DataParsingError, BrowserError, DataNotFoundError
from .logger import get_logger

# Import legacy components for backward compatibility
# These are used by legacy scraping code
from legacy.config import Config
from legacy.browser_manager import BrowserManager
from legacy.data_cleaner import DataCleaner
from legacy.data_storage import DataStorage

__all__ = [
    # ML-32M data loader exports (primary exports)
    "load_movie_data",
    "load_ratings_data",
    "get_ml32m_data_path",
    # Common utilities
    "ScrapingError",
    "DataParsingError",
    "BrowserError",
    "DataNotFoundError",
    "get_logger",
    # Legacy exports (for backward compatibility)
    "Config",
    "DataStorage",
    "BrowserManager",
    "DataCleaner",
]
