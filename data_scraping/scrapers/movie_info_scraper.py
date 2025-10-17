"""Scraper for movie information from Watcha."""

from typing import Optional, Dict, Any, List, Tuple
from common.exceptions import DataParsingError
from .base_scraper import BaseScraper


class MovieInfoScraper(BaseScraper):
    """Scraper for movie basic information."""
    
    def scrape(self, movie_id: str) -> Dict[str, Any]:
        """
        Scrape movie information.
        
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
            # Fetch page content
            content = self.browser_manager.fetch_page_content(url)
            tree = self.browser_manager.parse_html_to_tree(content)
            
            # Extract basic info
            movie_data = {
                'movie_id': movie_id,
                'title': self._extract_title(tree),
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
            basic_info = self._extract_basic_info(tree)
            movie_data.update(basic_info)
            
            # Extract runtime and age rating
            additional_info = self._extract_additional_info(tree)
            movie_data.update(additional_info)
            
            # Extract cast and production info
            movie_data['cast_production'] = self._extract_cast_production(tree)
            
            # Extract synopsis
            movie_data['synopsis'] = self._extract_synopsis(tree)
            
            # Extract ratings
            rating_info = self._extract_rating_info(tree)
            movie_data.update(rating_info)
            
            # Extract comments count
            movie_data['n_comments'] = self._extract_comments_count(tree)
            
            self.logger.info(f"Successfully scraped movie: {movie_data.get('title')}")
            return movie_data
            
        except Exception as e:
            self.logger.error(f"Failed to scrape movie {movie_id}: {e}")
            raise DataParsingError(f"Failed to scrape movie {movie_id}") from e
    
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
                # Only runtime
                runtime_minutes = self.cleaner.time_to_minutes(items[0])
                result['runtime'] = str(runtime_minutes) if runtime_minutes else items[0]
            elif len(items) >= 2:
                # Runtime and age
                runtime_minutes = self.cleaner.time_to_minutes(items[0])
                result['runtime'] = str(runtime_minutes) if runtime_minutes else items[0]
                result['age'] = self.cleaner.extract_movie_age(items[1])
        
        return result
    
    def _extract_cast_production(self, tree) -> List[Tuple[str, str]]:
        """Extract cast and production crew information."""
        cast_list = []
        i = 1
        
        while True:
            name_xpath = self.config.get_xpath('cast_name_template', i=i)
            role_xpath = self.config.get_xpath('cast_role_template', i=i)
            
            name = self._extract_text_safe(tree, name_xpath)
            role = self._extract_text_safe(tree, role_xpath)
            
            if not name or not role:
                break
            
            cast_list.append((name, role))
            i += 1
        
        return cast_list
    
    def _extract_synopsis(self, tree) -> Optional[str]:
        """Extract movie synopsis."""
        xpath = self.config.get_xpath('movie_synopsis')
        synopsis = self._extract_text_safe(tree, xpath)
        return synopsis
    
    def _extract_rating_info(self, tree) -> Dict[str, Optional[str]]:
        """Extract average rating and number of ratings."""
        result = {'avg_rating': None, 'n_rating': None}
        
        # Average rating
        avg_xpath = self.config.get_xpath('movie_avg_rating')
        result['avg_rating'] = self._extract_text_safe(tree, avg_xpath)
        
        # Number of ratings (in 만명)
        n_xpath = self.config.get_xpath('movie_n_rating')
        n_rating_text = self._extract_text_safe(tree, n_xpath, index=1)
        if n_rating_text:
            n_rating = self.cleaner.extract_number(n_rating_text)
            result['n_rating'] = str(n_rating) if n_rating else None
        
        return result
    
    def _extract_comments_count(self, tree) -> Optional[str]:
        """Extract number of comments."""
        xpath = self.config.get_xpath('movie_n_comments')
        n_comments = self._extract_text_safe(tree, xpath)
        return n_comments

