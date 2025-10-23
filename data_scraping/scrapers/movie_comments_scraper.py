"""Scraper for movie comments from Watcha."""

import time
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page  # type: ignore

from common.exceptions import DataParsingError
from .base_scraper import BaseScraper


class MovieCommentsScraper(BaseScraper):
    """Scraper for movie comments and ratings."""
    
    def scrape(self, movie_id: str, max_comments: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scrape all comments for a movie.
        
        Args:
            movie_id: Watcha movie ID
            max_comments: Maximum number of comments to scrape (None for all)
        
        Returns:
            List of comment dictionaries
        
        Raises:
            DataParsingError: If scraping fails
        """
        self.logger.info(f"Scraping comments for movie ID: {movie_id}")
        if max_comments:
            self.logger.info(f"Max comments limit: {max_comments}")
        
        url = self.config.get_comments_url(movie_id)
        comments = []
        
        try:
            with self.browser_manager.get_page() as page:
                page.goto(url)
                
                # Scroll to load all comments (or up to max_comments)
                self._scroll_and_load(page, max_comments)
                
                # Extract comments
                comments = self._extract_all_comments(page, max_comments)
            
            self.logger.info(f"Successfully scraped {len(comments)} comments")
            return comments
            
        except Exception as e:
            self.logger.error(f"Failed to scrape comments for {movie_id}: {e}")
            raise DataParsingError(f"Failed to scrape comments for {movie_id}") from e
    
    def _scroll_and_load(self, page: Page, max_comments: Optional[int] = None) -> None:
        """
        Scroll page to load comments.
        
        Args:
            page: Playwright page instance
            max_comments: Maximum number of comments to load (None for all)
        """
        if max_comments:
            self.logger.debug(f"Scrolling to load up to {max_comments} comments")
        else:
            self.logger.debug("Scrolling to load all comments")
        
        # If no limit, scroll to end
        if not max_comments:
            self.browser_manager._scroll_to_end(page)
        else:
            # Scroll until we have enough comments or reach the end
            comment_list_xpath = '/html/body/main/div[1]/section/div[2]/ul/li'
            previous_count = 0
            no_change_count = 0
            max_no_change = 3  # Stop after 3 consecutive scrolls with no new comments
            
            # Allow more scrolls - calculate based on max_comments (roughly 10-20 comments per scroll)
            max_scrolls = max(50, (max_comments // 10) + 10)
            
            for scroll_num in range(max_scrolls):
                comment_elements = page.locator(f'xpath={comment_list_xpath}')
                count = comment_elements.count()
                
                self.logger.debug(f"Scroll {scroll_num + 1}: Found {count} comments (target: {max_comments})")
                
                # Check if we have enough comments
                if count >= max_comments:
                    self.logger.debug(f"Reached target of {max_comments} comments")
                    break
                
                # Check if no new comments loaded
                if count == previous_count:
                    no_change_count += 1
                    if no_change_count >= max_no_change:
                        self.logger.debug(f"No new comments after {max_no_change} scrolls, stopping")
                        break
                else:
                    no_change_count = 0
                
                previous_count = count
                
                # Scroll down
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(self.config.SCROLL_DELAY)
    
    def _extract_all_comments(self, page: Page, max_comments: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Extract comment data from page with optimized DOM queries.
        
        Args:
            page: Playwright page instance
            max_comments: Maximum number of comments to extract (None for all)
        
        Returns:
            List of comment dictionaries
        """
        comments = []
        
        # Get all comment elements at once (more efficient than querying one by one)
        comment_list_xpath = '/html/body/main/div[1]/section/div[2]/ul/li'
        comment_elements = page.locator(f'xpath={comment_list_xpath}')
        
        count = comment_elements.count()
        
        # Limit count if max_comments is specified
        if max_comments:
            count = min(count, max_comments)
        
        self.logger.debug(f"Found {comment_elements.count()} comment elements, extracting {count}")
        
        for i in range(count):
            try:
                comment_data = self._extract_single_comment_optimized(page, i + 1)
                
                if comment_data:
                    comments.append(comment_data)
                    
            except Exception as e:
                self.logger.debug(f"Failed to extract comment at index {i + 1}: {e}")
                continue
        
        return comments
    
    def _extract_single_comment(self, page: Page, index: int) -> Optional[Dict[str, Any]]:
        """
        Extract single comment data (legacy method, kept for compatibility).
        
        Args:
            page: Playwright page instance
            index: Comment index (1-based)
        
        Returns:
            Comment data dictionary or None if not found
        """
        return self._extract_single_comment_optimized(page, index)
    
    def _extract_single_comment_optimized(self, page: Page, index: int) -> Optional[Dict[str, Any]]:
        """
        Extract single comment data with optimized locator queries.
        
        Args:
            page: Playwright page instance
            index: Comment index (1-based)
        
        Returns:
            Comment data dictionary or None if not found
        """
        # Extract custom ID (user ID)
        custom_id_xpath = self.config.get_xpath('comment_custom_id_template', i=index)
        custom_id_locator = page.locator(custom_id_xpath)
        
        # Check existence first (single count() call per comment)
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
        
        # Extract comment text - use first() to avoid extra count() call
        comment_xpath = self.config.get_xpath('comment_text_template', i=index)
        comment_text = None
        try:
            raw_text = page.locator(comment_xpath).first.inner_text(timeout=1000)
            comment_text = self.cleaner.sanitize_for_txt(raw_text)
        except Exception:
            pass
        
        # Extract rating - use first() to avoid extra count() call
        rating_xpath = self.config.get_xpath('comment_rating_template', i=index)
        rating = None
        try:
            rating_text = page.locator(rating_xpath).first.inner_text(timeout=1000)
            rating = self.cleaner.clean_text(rating_text)
        except Exception:
            pass
        
        # Extract number of likes - use first() to avoid extra count() call
        likes_xpath = self.config.get_xpath('comment_likes_template', i=index)
        n_likes = None
        try:
            likes_text = page.locator(likes_xpath).first.inner_text(timeout=1000)
            n_likes = self.cleaner.clean_text(likes_text)
        except Exception:
            pass
        
        return {
            'custom_id': custom_id,
            'comment': comment_text,
            'rating': rating,
            'n_likes': n_likes,
        }

