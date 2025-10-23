"""Scraper for movie information from Watcha."""

from typing import Optional, Dict, Any, List, Tuple
from common.exceptions import DataParsingError
from .base_scraper import BaseScraper


class MovieInfoScraper(BaseScraper):
    """Scraper for movie basic information."""
    
    def scrape(self, movie_id: str) -> Dict[str, Any]:
        """
        Scrape movie information using Playwright.
        
        Args:
            movie_id: Watcha movie ID
        
        Returns:
            Dictionary containing movie information
        
        Raises:
            DataParsingError: If critical data extraction fails
        """
        self.logger.info(f"Scraping movie info for ID: {movie_id}")
        
        url = self.config.get_movie_url(movie_id)
        
        try:
            # Use Playwright to extract all data
            with self.browser_manager.get_page() as page:
                page.goto(url, timeout=self.config.BROWSER_TIMEOUT)
                
                # Extract basic info
                movie_data = {
                    'movie_id': movie_id,
                    'title': self._extract_with_playwright(page, 'movie_title'),
                    'year': None,
                    'genre': None,
                    'country': None,
                    'runtime': None,
                    'age': None,
                    'cast_production': [],
                    'synopsis': None,
                    'avg_rating': None,
                    'n_rating': None,
                    'n_comments': None,
                }
                
                # Extract year, genre, country
                basic_info_text = self._extract_with_playwright(page, 'movie_basic_info')
                if basic_info_text:
                    items = self.cleaner.parse_movie_info_line(basic_info_text)
                    if len(items) >= 3:
                        movie_data['year'] = items[0]
                        movie_data['genre'] = items[1]
                        movie_data['country'] = items[2]
                
                # Extract runtime and age rating
                additional_info_text = self._extract_with_playwright(page, 'movie_additional_info')
                if additional_info_text:
                    items = self.cleaner.parse_movie_info_line(additional_info_text)
                    if len(items) >= 1:
                        # Keep original format "1시간 35분" without converting to minutes
                        movie_data['runtime'] = items[0]
                    if len(items) >= 2:
                        movie_data['age'] = items[1]  # Keep original format (전체, 12, 15, 19, 청불)
                
                # Extract cast and production info
                movie_data['cast_production'] = self._extract_cast_with_playwright(page)
                
                # Extract synopsis (find longest p element like in debug)
                synopsis = None
                try:
                    # Try XPath first
                    synopsis = self._extract_with_playwright(page, 'movie_synopsis')
                    
                    # If not found, try finding longest p element
                    if not synopsis:
                        long_text_elements = page.locator('p')
                        count = long_text_elements.count()
                        longest_text = ''
                        for i in range(min(count, 10)):  # Check first 10 p elements
                            try:
                                text = long_text_elements.nth(i).inner_text()
                                if len(text) > len(longest_text) and len(text) > 10:
                                    longest_text = text
                            except Exception:
                                pass
                        synopsis = longest_text if longest_text else None
                except Exception as e:
                    self.logger.warning(f"Could not extract synopsis: {e}")
                
                movie_data['synopsis'] = synopsis
                
                # Extract ratings
                rating_text = None
                try:
                    rating_elements = page.locator('text=/평균/')
                    if rating_elements.count() > 0:
                        rating_text = rating_elements.first.inner_text()
                        avg_rating, rating_count = self.cleaner.parse_rating_text(rating_text)
                        movie_data['avg_rating'] = avg_rating
                        movie_data['n_rating'] = rating_count
                except Exception as e:
                    self.logger.warning(f"Could not extract rating: {e}")
                
                # Extract comments count
                movie_data['n_comments'] = self._extract_with_playwright(page, 'movie_n_comments')
            
            self.logger.info(f"Successfully scraped movie: {movie_data.get('title')}")
            return movie_data
            
        except Exception as e:
            self.logger.error(f"Failed to scrape movie {movie_id}: {e}")
            raise DataParsingError(f"Failed to scrape movie {movie_id}") from e
    
    def _extract_with_playwright(self, page, xpath_key: str) -> Optional[str]:
        """
        Extract text using Playwright.
        
        Args:
            page: Playwright Page object
            xpath_key: Key to get XPath from config
        
        Returns:
            Extracted text or None
        """
        try:
            xpath = self.config.get_xpath(xpath_key)
            element = page.locator(f'xpath={xpath}')
            if element.count() > 0:
                text = element.first.inner_text()
                return text
        except Exception as e:
            self.logger.debug(f"Could not extract {xpath_key}: {e}")
        return None
    
    def _extract_cast_with_playwright(self, page) -> List[Tuple[str, str]]:
        """Extract cast and production crew information using Playwright."""
        cast_list = []
        i = 1
        
        while True:
            name_xpath = self.config.get_xpath('cast_name_template', i=i)
            role_xpath = self.config.get_xpath('cast_role_template', i=i)
            
            try:
                name_elem = page.locator(f'xpath={name_xpath}')
                role_elem = page.locator(f'xpath={role_xpath}')
                
                if name_elem.count() > 0 and role_elem.count() > 0:
                    name = name_elem.first.inner_text()
                    role = role_elem.first.inner_text()
                    cast_list.append((name, role))
                    i += 1
                else:
                    break
            except Exception:
                break
        
        return cast_list
    
    def _extract_title(self, tree) -> Optional[str]:
        """Extract movie title."""
        xpath = self.config.get_xpath('movie_title')
        title = self._extract_text_safe(tree, xpath)
        return title
    
    def _extract_basic_info(self, tree) -> Dict[str, Optional[str]]:
        """Extract year, genre, and country."""
        xpath = self.config.get_xpath('movie_basic_info')
        info_text = self._extract_text_safe(tree, xpath)
        
        result = {'year': None, 'genre': None, 'country': None}
        
        if info_text:
            items = self.cleaner.parse_movie_info_line(info_text)
            if len(items) >= 3:
                result['year'] = items[0]
                result['genre'] = items[1]
                result['country'] = items[2]
        
        return result
    
    def _extract_additional_info(self, tree) -> Dict[str, Optional[str]]:
        """Extract runtime and age rating."""
        xpath = self.config.get_xpath('movie_additional_info')
        info_text = self._extract_text_safe(tree, xpath)
        
        result = {'runtime': None, 'age': None}
        
        if info_text:
            items = self.cleaner.parse_movie_info_line(info_text)
            if len(items) == 1:
                # Only runtime - try both old and new formats
                runtime_minutes = self.cleaner.time_to_minutes(items[0])
                if runtime_minutes:
                    result['runtime'] = str(runtime_minutes)
                else:
                    # Try new format (just numbers)
                    result['runtime'] = self.cleaner.parse_runtime_new(items[0])
            elif len(items) >= 2:
                # Runtime and age - try both old and new formats
                runtime_minutes = self.cleaner.time_to_minutes(items[0])
                if runtime_minutes:
                    result['runtime'] = str(runtime_minutes)
                else:
                    # Try new format (just numbers)
                    result['runtime'] = self.cleaner.parse_runtime_new(items[0])
                result['age'] = self.cleaner.extract_movie_age(items[1])
        
        return result
    
    def _extract_cast_production(self, tree) -> List[Tuple[str, str]]:
        """Extract cast and production crew information."""
        cast_list = []
        i = 1
        
        # Try individual extraction first (old method)
        while True:
            name_xpath = self.config.get_xpath('cast_name_template', i=i)
            role_xpath = self.config.get_xpath('cast_role_template', i=i)
            
            name = self._extract_text_safe(tree, name_xpath)
            role = self._extract_text_safe(tree, role_xpath)
            
            if not name or not role:
                break
            
            cast_list.append((name, role))
            i += 1
        
        # If no cast found with individual extraction, try bulk extraction
        if not cast_list:
            # Try to find cast information in a different format
            # This might be in a different section or format
            cast_list = self._extract_cast_bulk(tree)
        
        return cast_list
    
    def _extract_cast_bulk(self, tree) -> List[Tuple[str, str]]:
        """Extract cast information from bulk text format."""
        # This method would need to be implemented based on the actual HTML structure
        # For now, return empty list
        return []
    
    def _extract_synopsis(self, tree) -> Optional[str]:
        """Extract movie synopsis."""
        xpath = self.config.get_xpath('movie_synopsis')
        synopsis = self._extract_text_safe(tree, xpath)
        return synopsis
    
    def _extract_rating_info(self, tree, rating_text: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Extract average rating and number of ratings.
        
        Args:
            tree: lxml tree element
            rating_text: Optional pre-extracted rating text from Playwright
        """
        result = {'avg_rating': None, 'n_rating': None}
        
        # If rating_text is provided (from Playwright), use it
        if rating_text and '평균' in rating_text:
            # Parse "평균 3.8(1,358명)" format
            avg_rating, rating_count = self.cleaner.parse_rating_text(rating_text)
            result['avg_rating'] = avg_rating
            result['n_rating'] = rating_count
            return result
        
        # Fallback: try extracting from tree (old method)
        rating_xpath = self.config.get_xpath('movie_avg_rating')
        extracted_text = self._extract_text_safe(tree, rating_xpath)
        
        if extracted_text and '평균' in extracted_text:
            avg_rating, rating_count = self.cleaner.parse_rating_text(extracted_text)
            result['avg_rating'] = avg_rating
            result['n_rating'] = rating_count
        else:
            result['avg_rating'] = extracted_text
            
            # Try to extract rating count separately
            n_xpath = self.config.get_xpath('movie_n_rating')
            n_rating_text = self._extract_text_safe(tree, n_xpath, index=1)
            if n_rating_text:
                n_rating = self.cleaner.extract_number(n_rating_text)
                result['n_rating'] = str(int(n_rating)) if n_rating else None
        
        return result
    
    def _extract_comments_count(self, tree) -> Optional[str]:
        """Extract number of comments."""
        xpath = self.config.get_xpath('movie_n_comments')
        n_comments = self._extract_text_safe(tree, xpath)
        return n_comments

