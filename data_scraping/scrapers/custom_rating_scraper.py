"""Scraper for user's custom movie ratings from Watcha.

Note: XPath selectors updated on 2025-10-21 to match new Watcha page structure.
"""

from typing import List, Dict, Any, Optional

from common.exceptions import DataParsingError
from .base_scraper import BaseScraper


class CustomRatingScraper(BaseScraper):
    """Scraper for user's movie ratings."""
    
    def scrape(self, custom_id: str) -> List[Dict[str, Any]]:
        """
        Scrape all movie ratings for a user.
        
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
            # Fetch with scroll to load all ratings
            content = self.browser_manager.fetch_with_scroll(url)
            tree = self.browser_manager.parse_html_to_tree(content)
            
            # Extract all ratings
            ratings = self._extract_all_ratings(tree)
            
            self.logger.info(f"Successfully scraped {len(ratings)} ratings")
            return ratings
            
        except Exception as e:
            self.logger.error(f"Failed to scrape ratings for {custom_id}: {e}")
            raise DataParsingError(f"Failed to scrape ratings for {custom_id}") from e
    
    def _extract_all_ratings(self, tree) -> List[Dict[str, Any]]:
        """Extract all movie ratings from the page."""
        ratings = []
        i = 1
        
        while True:
            rating_data = self._extract_single_rating(tree, i)
            
            if not rating_data:
                break
            
            ratings.append(rating_data)
            i += 1
        
        return ratings
    
    def _extract_single_rating(self, tree, index: int) -> Optional[Dict[str, Any]]:
        """
        Extract single movie rating.
        
        Args:
            tree: lxml tree element
            index: Rating index (1-based)
        
        Returns:
            Rating data dictionary or None if not found
        """
        # Extract movie ID from href
        id_xpath = self.config.get_xpath('user_movie_id_template', i=index)
        movie_id_raw = self.browser_manager.extract_xpath_text(tree, id_xpath)
        
        if not movie_id_raw:
            return None
        
        movie_id = movie_id_raw.split('/')[-1]
        
        # Extract movie name
        name_xpath = self.config.get_xpath('user_movie_name_template', i=index)
        movie_name = self._extract_text_safe(tree, name_xpath)
        
        # Extract rating
        rating_xpath = self.config.get_xpath('user_movie_rating_template', i=index)
        rating_text = self._extract_text_safe(tree, rating_xpath)
        rating = self.cleaner.extract_number(rating_text) if rating_text else None
        
        return {
            'movie_id': movie_id,
            'movie_name': movie_name,
            'rating': str(rating) if rating else None,
        }

