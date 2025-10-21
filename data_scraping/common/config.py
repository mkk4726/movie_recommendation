"""Configuration settings for the movie scraper."""

from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration class for scraping settings."""
    
    # Base URLs
    WATCHA_BASE_URL: str = "https://pedia.watcha.com/ko-KR"
    
    # Browser settings
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 60000
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
    
    # Authentication settings
    AUTH_STATE_FILE: str = "./auth_state.json"
    
    # Scroll settings
    SCROLL_DELAY: int = 2
    SCROLL_MAX_RETRIES: int = 5
    
    # Data settings
    DATA_DIR: str = "./data"
    DATA_SEPARATOR: str = "/"  # Using '/' as delimiter (data is cleaned to remove '/')
    
    # File names
    MOVIE_INFO_FILE: str = "movie_info_watcha.txt"
    MOVIE_COMMENTS_FILE: str = "movie_comments.txt"
    CUSTOM_RATING_FILE: str = "custom_movie_rating.txt"
    
    # XPath configurations
    XPATHS: Dict[str, str] = field(default_factory=lambda: {
        # Movie info page
        "movie_title": '//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[1]/div[2]/div/h1/text()',
        "movie_basic_info": '//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[1]/div[2]/div/div[2]/text()',
        "movie_additional_info": '//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[1]/div[2]/div/div[3]/text()',
        "movie_synopsis": '//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[3]/p/text()',
        "movie_avg_rating": '//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[2]/div/div[1]/text()',
        "movie_n_rating": '//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[2]/div/div[2]/text()',
        "movie_n_comments": '/html/body/div[1]/div[1]/section/div/div[2]/section/section[2]/header/span/text()',
        
        # Cast and crew (dynamic index)
        "cast_name_template": '//*[@id="content_credits"]/section/div[1]/ul/li[{i}]/a/div[2]/div[1]/div[1]/text()',
        "cast_role_template": '//*[@id="content_credits"]/section/div[1]/ul/li[{i}]/a/div[2]/div[1]/div[2]/text()',
        
        # Comments page (dynamic index) - Updated 2025-10-21 for new page structure
        "comment_custom_id_template": '//*[@id="root"]/div[1]/section/div[2]/ul/li[{i}]/article/a[1]',
        "comment_text_template": '//*[@id="root"]/div[1]/section/div[2]/ul/li[{i}]/article/a[2]/p',
        "comment_rating_template": '//*[@id="root"]/div[1]/section/div[2]/ul/li[{i}]/article/a[1]/header/div[2]/p',
        "comment_likes_template": '//*[@id="root"]/div[1]/section/div[2]/ul/li[{i}]/article/ul/li[1]/button/span',
        "comment_spoiler_button_template": '//*[@id="root"]/div[1]/section/div[2]/ul/li[{i}]/article/a[2]/p/button',
        
        # User ratings page (dynamic index)
        "user_movie_id_template": '//*[@id="root"]/div[1]/section/section/div[1]/section/div[1]/div/ul/li[{i}]/a/@href',
        "user_movie_name_template": '//*[@id="root"]/div[1]/section/section/div[1]/section/div[1]/div/ul/li[{i}]/a/div[2]/div[1]/text()',
        "user_movie_rating_template": '//*[@id="root"]/div[1]/section/section/div[1]/section/div[1]/div/ul/li[{i}]/a/div[2]/div[2]/text()',
    })
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "scraper.log"
    
    def get_movie_url(self, movie_id: str) -> str:
        """Generate movie info URL."""
        return f"{self.WATCHA_BASE_URL}/contents/{movie_id}"
    
    def get_comments_url(self, movie_id: str) -> str:
        """Generate movie comments URL."""
        return f"{self.WATCHA_BASE_URL}/contents/{movie_id}/comments"
    
    def get_user_ratings_url(self, custom_id: str) -> str:
        """Generate user ratings URL."""
        return f"{self.WATCHA_BASE_URL}/users/{custom_id}/contents/movies/ratings"
    
    def get_xpath(self, key: str, **kwargs: Any) -> str:
        """Get XPath with optional template formatting."""
        xpath = self.XPATHS.get(key)
        if xpath and kwargs:
            return xpath.format(**kwargs)
        return xpath

