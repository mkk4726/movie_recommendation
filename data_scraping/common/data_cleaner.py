"""Data cleaning utilities for scraped content."""

import re
from typing import Optional


class DataCleaner:
    """Utility class for cleaning and processing scraped data."""
    
    @staticmethod
    def clean_text(text: str, remove_chars: Optional[str] = None) -> str:
        """
        Clean text by removing/replacing unwanted characters.
        
        Args:
            text: Text to clean
            remove_chars: Additional characters to remove
        
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Replace newlines, tabs, carriage returns with space
        text = text.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
        
        # Remove '/' character (used as delimiter)
        text = text.replace('/', ' ')
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove additional characters if specified
        if remove_chars:
            for char in remove_chars:
                text = text.replace(char, '')
        
        return text.strip()
    
    @staticmethod
    def sanitize_for_txt(text: str) -> str:
        """
        Sanitize text for TXT storage with '/' delimiter.
        
        Args:
            text: Text to sanitize
        
        Returns:
            TXT-safe text (with '/' removed)
        """
        if not text:
            return ""
        
        # Clean basic formatting (includes removing '/')
        text = DataCleaner.clean_text(text)
        
        return text
    
    @staticmethod
    def extract_number(text: str) -> Optional[float]:
        """
        Extract numeric value from text.
        
        Args:
            text: Text containing numbers
        
        Returns:
            Extracted number or None if not found
        """
        if not text:
            return None
        
        # Remove commas
        text = text.replace(',', '')
        
        # Extract number using regex
        match = re.search(r'(\d+\.\d+|\d+)', text)
        
        if match:
            return float(match.group(0))
        return None
    
    @staticmethod
    def time_to_minutes(time_str: str) -> Optional[int]:
        """
        Convert time string (e.g., '2시간 22분') to total minutes.
        
        Args:
            time_str: Time string in Korean format
        
        Returns:
            Total minutes or None if parsing fails
        """
        if not time_str:
            return None
        
        try:
            # Extract hours and minutes
            hours_match = re.search(r'(\d+)시간', time_str)
            minutes_match = re.search(r'(\d+)분', time_str)
            
            hours = int(hours_match.group(1)) if hours_match else 0
            minutes = int(minutes_match.group(1)) if minutes_match else 0
            
            return hours * 60 + minutes
        except (AttributeError, ValueError):
            return None
    
    @staticmethod
    def extract_movie_age(text: str) -> Optional[str]:
        """
        Extract and normalize age rating from text.
        
        Args:
            text: Age rating text
        
        Returns:
            Normalized age rating
        """
        if not text:
            return None
        
        text = text.strip()
        
        if text == '전체':
            return '12'
        elif text == '청불':
            return '19'
        else:
            # Extract number
            age = DataCleaner.extract_number(text)
            return str(int(age)) if age else None
    
    @staticmethod
    def remove_emojis(text: str) -> str:
        """
        Remove emojis from text.
        
        Args:
            text: Text containing emojis
        
        Returns:
            Text without emojis
        """
        if not text:
            return ""
        
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        
        return emoji_pattern.sub('', text)
    
    @staticmethod
    def parse_movie_info_line(line: str) -> list:
        """
        Parse movie info line separated by dots.
        
        Args:
            line: Info line with dot separators
        
        Returns:
            List of cleaned info items
        """
        if not line:
            return []
        
        items = line.split('·')
        return [item.strip() for item in items if item.strip()]

