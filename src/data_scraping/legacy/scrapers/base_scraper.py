"""Base scraper class with common functionality."""

import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path to import from legacy
legacy_dir = Path(__file__).parent.parent
if legacy_dir not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from browser_manager import BrowserManager
from config import Config
from data_cleaner import DataCleaner
from logger import get_logger


class BaseScraper(ABC):
    """Base class for all scrapers."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize base scraper.

        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.browser_manager = BrowserManager(self.config)
        self.cleaner = DataCleaner()
        self.logger = get_logger(self.__class__.__name__, level=self.config.LOG_LEVEL, log_file=self.config.LOG_FILE)

    @abstractmethod
    def scrape(self, *args, **kwargs) -> Any:
        """
        Main scraping method to be implemented by subclasses.

        Returns:
            Scraped data
        """
        pass

    def _extract_text_safe(self, tree, xpath: str, index: int = 0, clean: bool = True) -> Optional[str]:
        """
        Safely extract text from XPath with cleaning.

        Args:
            tree: lxml tree element
            xpath: XPath query
            index: Index to extract
            clean: Whether to clean the text

        Returns:
            Extracted and optionally cleaned text
        """
        text = self.browser_manager.extract_xpath_text(tree, xpath, index)

        if text and clean:
            text = self.cleaner.clean_text(text)

        return text
