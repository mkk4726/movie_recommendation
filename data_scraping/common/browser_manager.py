"""Browser management for Playwright-based scraping."""

import time
import os
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from bs4 import BeautifulSoup
from lxml import etree

from .config import Config
from .exceptions import BrowserError
from .logger import get_logger


class BrowserManager:
    """Manages Playwright browser instances and common operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize browser manager.
        
        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.logger = get_logger(__name__, level=self.config.LOG_LEVEL)
    
    @contextmanager
    def get_browser(self):
        """
        Context manager for browser instance.
        
        Yields:
            Browser instance
        """
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.config.BROWSER_HEADLESS)
            try:
                yield browser
            finally:
                browser.close()
    
    @contextmanager
    def get_page(self, browser: Optional[Browser] = None) -> Page:
        """
        Context manager for browser page with authentication.
        
        Args:
            browser: Optional browser instance (if None, creates new one)
        
        Yields:
            Page instance
        """
        if browser:
            context = self._create_context(browser)
            page = context.new_page()
            try:
                yield page
            finally:
                page.close()
                context.close()
        else:
            with self.get_browser() as browser:
                context = self._create_context(browser)
                page = context.new_page()
                try:
                    yield page
                finally:
                    page.close()
                    context.close()
    
    def _create_context(self, browser: Browser) -> BrowserContext:
        """
        Create browser context with authentication if available.
        
        Args:
            browser: Browser instance
        
        Returns:
            BrowserContext with or without stored authentication
        """
        auth_file = Path(self.config.AUTH_STATE_FILE)
        
        if auth_file.exists():
            self.logger.debug(f"Loading auth state from {auth_file}")
            context = browser.new_context(
                user_agent=self.config.USER_AGENT,
                storage_state=str(auth_file)
            )
        else:
            self.logger.debug("No auth state found, creating new context")
            context = browser.new_context(user_agent=self.config.USER_AGENT)
        
        return context
    
    def save_auth_state(self, context: BrowserContext) -> None:
        """
        Save authentication state for future use.
        
        Args:
            context: BrowserContext to save state from
        """
        auth_file = Path(self.config.AUTH_STATE_FILE)
        context.storage_state(path=str(auth_file))
        self.logger.info(f"Auth state saved to {auth_file}")
    
    def has_auth_state(self) -> bool:
        """
        Check if authentication state file exists.
        
        Returns:
            True if auth state exists, False otherwise
        """
        return Path(self.config.AUTH_STATE_FILE).exists()
    
    def fetch_page_content(self, url: str) -> str:
        """
        Fetch page content using Playwright.
        
        Args:
            url: URL to fetch
        
        Returns:
            Page HTML content
        
        Raises:
            BrowserError: If page fetch fails
        """
        try:
            with self.get_page() as page:
                self.logger.debug(f"Fetching URL: {url}")
                page.goto(url, timeout=self.config.BROWSER_TIMEOUT)
                content = page.content()
                return content
        except Exception as e:
            self.logger.error(f"Failed to fetch page {url}: {e}")
            raise BrowserError(f"Failed to fetch page: {e}") from e
    
    def fetch_with_scroll(self, url: str, page: Optional[Page] = None) -> str:
        """
        Fetch page content with infinite scroll.
        
        Args:
            url: URL to fetch
            page: Optional existing page instance
        
        Returns:
            Page HTML content after scrolling
        
        Raises:
            BrowserError: If page fetch fails
        """
        try:
            if page:
                page.goto(url)
                self._scroll_to_end(page)
                return page.content()
            else:
                with self.get_page() as page:
                    self.logger.debug(f"Fetching URL with scroll: {url}")
                    page.goto(url)
                    self._scroll_to_end(page)
                    return page.content()
        except Exception as e:
            self.logger.error(f"Failed to fetch page with scroll {url}: {e}")
            raise BrowserError(f"Failed to fetch page with scroll: {e}") from e
    
    def _scroll_to_end(self, page: Page) -> None:
        """
        Scroll page to the end to load all dynamic content.
        
        Args:
            page: Page instance to scroll
        """
        previous_height = 0
        attempts = 0
        scroll_count = 0
        
        while attempts < self.config.SCROLL_MAX_RETRIES:
            current_height = page.evaluate("document.body.scrollHeight")
            
            if current_height == previous_height:
                attempts += 1
            else:
                attempts = 0
            
            previous_height = current_height
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            scroll_count += 1
            
            self.logger.debug(f"Scroll #{scroll_count}, height: {current_height}")
            time.sleep(self.config.SCROLL_DELAY)
        
        self.logger.debug(f"Scrolling complete after {scroll_count} scrolls")
    
    def parse_html_to_tree(self, html_content: str) -> etree._Element:
        """
        Parse HTML content to lxml tree for XPath queries.
        
        Args:
            html_content: HTML string
        
        Returns:
            lxml ElementTree
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        tree = etree.HTML(str(soup))
        return tree
    
    def extract_xpath_text(
        self,
        tree: etree._Element,
        xpath: str,
        index: int = 0,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract text using XPath with error handling.
        
        Args:
            tree: lxml tree element
            xpath: XPath query string
            index: Index of element to extract (default 0)
            default: Default value if extraction fails
        
        Returns:
            Extracted text or default value
        """
        try:
            result = tree.xpath(xpath)
            if result and len(result) > index:
                return result[index]
            return default
        except Exception as e:
            self.logger.debug(f"XPath extraction failed for {xpath}: {e}")
            return default

