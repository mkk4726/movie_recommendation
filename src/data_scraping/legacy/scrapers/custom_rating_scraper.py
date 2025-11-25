"""Scraper for user's custom movie ratings from Watcha.

Note: XPath selectors updated on 2025-10-23 to match new Watcha page structure.
Updated to use Playwright for consistency with other scrapers.
"""

from typing import List, Dict, Any, Optional
from playwright.sync_api import Page  # type: ignore

from common.exceptions import DataParsingError
from .base_scraper import BaseScraper


class CustomRatingScraper(BaseScraper):
    """Scraper for user's movie ratings."""
    
    def scrape(self, custom_id: str) -> List[Dict[str, Any]]:
        """
        Scrape all movie ratings for a user using Playwright.
        
        Args:
            custom_id: Watcha user ID
        
        Returns:
            List of rating dictionaries
        
        Raises:
            DataParsingError: If scraping fails
        """
        self.logger.info(f"Scraping ratings for user ID: {custom_id}")
        
        url = self.config.get_user_ratings_url(custom_id)
        
        try:
            with self.browser_manager.get_page() as page:
                page.goto(url, timeout=self.config.BROWSER_TIMEOUT)
                
                # Scroll to load all ratings
                self._scroll_and_load(page)
                
                # Extract all ratings
                ratings = self._extract_all_ratings(page)
            
            self.logger.info(f"Successfully scraped {len(ratings)} ratings")
            return ratings
            
        except Exception as e:
            self.logger.error(f"Failed to scrape ratings for {custom_id}: {e}")
            raise DataParsingError(f"Failed to scrape ratings for {custom_id}") from e
    
    def _scroll_and_load(self, page: Page) -> None:
        """
        Scroll page to load all ratings.
        
        Args:
            page: Playwright page instance
        """
        self.logger.debug("Scrolling to load all ratings")
        
        # Scroll to end to load all dynamic content
        self.browser_manager._scroll_to_end(page)
    
    def _extract_all_ratings(self, page: Page) -> List[Dict[str, Any]]:
        """
        Extract all movie ratings from the page using Playwright.
        
        Args:
            page: Playwright page instance
        
        Returns:
            List of rating dictionaries
        """
        ratings = []
        i = 1
        
        while True:
            rating_data = self._extract_single_rating(page, i)
            
            if not rating_data:
                break
            
            ratings.append(rating_data)
            i += 1
        
        return ratings
    
    def _extract_single_rating(self, page: Page, index: int) -> Optional[Dict[str, Any]]:
        """
        Extract single movie rating using Playwright.
        
        Args:
            page: Playwright page instance
            index: Rating index (1-based)
        
        Returns:
            Rating data dictionary or None if not found
        """
        # Extract movie ID from href
        id_xpath = self.config.get_xpath('user_movie_id_template', i=index)
        movie_id_raw = None
        try:
            movie_id_elem = page.locator(f'xpath={id_xpath}')
            if movie_id_elem.count() > 0:
                href = movie_id_elem.get_attribute('href')
                movie_id_raw = href
        except Exception:
            pass
        
        if not movie_id_raw:
            return None
        
        movie_id = movie_id_raw.split('/')[-1]
        
        # Extract movie name
        name_xpath = self.config.get_xpath('user_movie_name_template', i=index)
        movie_name = None
        try:
            name_elem = page.locator(f'xpath={name_xpath}')
            if name_elem.count() > 0:
                movie_name = name_elem.inner_text()
        except Exception:
            pass
        
        # Extract rating
        rating_xpath = self.config.get_xpath('user_movie_rating_template', i=index)
        rating_text = None
        try:
            rating_elem = page.locator(f'xpath={rating_xpath}')
            if rating_elem.count() > 0:
                rating_text = rating_elem.inner_text()
        except Exception:
            pass
        
        rating = self.cleaner.extract_number(rating_text) if rating_text else None
        
        return {
            'movie_id': movie_id,
            'movie_name': movie_name,
            'rating': str(rating) if rating else None,
        }
