"""Scraper for movie comments from Watcha."""

import time
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page

from common.exceptions import DataParsingError
from .base_scraper import BaseScraper


class MovieCommentsScraper(BaseScraper):
    """Scraper for movie comments and ratings."""
    
    def scrape(self, movie_id: str) -> List[Dict[str, Any]]:
        """
        Scrape all comments for a movie.
        
        Args:
            movie_id: Watcha movie ID
        
        Returns:
            List of comment dictionaries
        
        Raises:
            DataParsingError: If scraping fails
        """
        self.logger.info(f"Scraping comments for movie ID: {movie_id}")
        
        url = self.config.get_comments_url(movie_id)
        comments = []
        
        try:
            with self.browser_manager.get_page() as page:
                page.goto(url)
                
                # Scroll to load all comments
                self._scroll_and_load(page)
                
                # Extract comments
                comments = self._extract_all_comments(page)
            
            self.logger.info(f"Successfully scraped {len(comments)} comments")
            return comments
            
        except Exception as e:
            self.logger.error(f"Failed to scrape comments for {movie_id}: {e}")
            raise DataParsingError(f"Failed to scrape comments for {movie_id}") from e
    
    def _scroll_and_load(self, page: Page) -> None:
        """Scroll page to load all comments."""
        self.logger.debug("Scrolling to load all comments")
        self.browser_manager._scroll_to_end(page)
    
    def _extract_all_comments(self, page: Page) -> List[Dict[str, Any]]:
        """Extract all comment data from page."""
        comments = []
        i = 1
        
        while True:
            try:
                comment_data = self._extract_single_comment(page, i)
                
                if not comment_data:
                    break
                
                comments.append(comment_data)
                i += 1
                
            except Exception as e:
                self.logger.debug(f"Finished extracting comments at index {i}: {e}")
                break
        
        return comments
    
    def _extract_single_comment(self, page: Page, index: int) -> Optional[Dict[str, Any]]:
        """
        Extract single comment data.
        
        Args:
            page: Playwright page instance
            index: Comment index (1-based)
        
        Returns:
            Comment data dictionary or None if not found
        """
        # Extract custom ID (user ID)
        custom_id_xpath = self.config.get_xpath('comment_custom_id_template', i=index)
        custom_id_locator = page.locator(custom_id_xpath)
        
        if custom_id_locator.count() == 0:
            return None
        
        href = custom_id_locator.get_attribute('href')
        custom_id = href.split('/')[-1] if href else None
        
        # Try to click spoiler "보기" button to reveal spoiler text
        spoiler_button_xpath = self.config.get_xpath('comment_spoiler_button_template', i=index)
        spoiler_button = page.locator(spoiler_button_xpath)
        
        if spoiler_button.count() > 0:
            try:
                spoiler_button.click()
                time.sleep(0.3)
            except Exception:
                pass  # Button might not be clickable
        
        # Extract comment text
        comment_xpath = self.config.get_xpath('comment_text_template', i=index)
        comment_locator = page.locator(comment_xpath)
        comment_text = None
        
        if comment_locator.count() > 0:
            raw_text = comment_locator.inner_text()
            comment_text = self.cleaner.sanitize_for_txt(raw_text)
        
        # Extract rating
        rating_xpath = self.config.get_xpath('comment_rating_template', i=index)
        rating_locator = page.locator(rating_xpath)
        rating = None
        
        if rating_locator.count() > 0:
            rating = self.cleaner.clean_text(rating_locator.inner_text())
        
        # Extract number of likes
        likes_xpath = self.config.get_xpath('comment_likes_template', i=index)
        likes_locator = page.locator(likes_xpath)
        n_likes = None
        
        if likes_locator.count() > 0:
            n_likes = self.cleaner.clean_text(likes_locator.inner_text())
        
        return {
            'custom_id': custom_id,
            'comment': comment_text,
            'rating': rating,
            'n_likes': n_likes,
        }

