"""Custom exceptions for the movie scraper."""


class ScrapingError(Exception):
    """Base exception for scraping errors."""
    pass


class DataParsingError(ScrapingError):
    """Exception raised when data parsing fails."""
    pass


class BrowserError(ScrapingError):
    """Exception raised when browser operations fail."""
    pass


class DataNotFoundError(ScrapingError):
    """Exception raised when expected data is not found."""
    pass

