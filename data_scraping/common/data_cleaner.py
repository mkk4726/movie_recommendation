"""Data cleaning utilities for scraped content."""

import re
from typing import Optional, List, Tuple


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
    
    @staticmethod
    def parse_cast_info(cast_text: str) -> List[Tuple[str, str]]:
        """
        Parse cast information from new format.
        
        Args:
            cast_text: Cast information in format "이름(역할); 이름(역할); ..."
        
        Returns:
            List of (name, role) tuples
        """
        if not cast_text:
            return []
        
        cast_list = []
        # Split by semicolon
        cast_items = cast_text.split(';')
        
        for item in cast_items:
            item = item.strip()
            if not item:
                continue
            
            # Extract name and role from "이름(역할)" format
            match = re.match(r'^([^(]+)\(([^)]+)\)$', item)
            if match:
                name = match.group(1).strip()
                role = match.group(2).strip()
                cast_list.append((name, role))
        
        return cast_list
    
    @staticmethod
    def parse_runtime_new(runtime_text: str) -> Optional[str]:
        """
        Parse runtime from new format (just numbers).
        
        Args:
            runtime_text: Runtime text (e.g., "105", "90")
        
        Returns:
            Runtime in minutes as string, or None if parsing fails
        """
        if not runtime_text:
            return None
        
        # Extract number
        runtime = DataCleaner.extract_number(runtime_text)
        if runtime:
            return str(int(runtime))
        
        return None
    
    @staticmethod
    def parse_rating_text(rating_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse rating text in format "평균 3.8(1,358명)".
        
        Args:
            rating_text: Rating text containing average and count
        
        Returns:
            Tuple of (avg_rating, rating_count) or (None, None) if parsing fails
        """
        if not rating_text:
            return None, None
        
        avg_rating = None
        rating_count = None
        
        try:
            # Extract average rating: "평균 3.8(1,358명)" -> "3.8"
            rating_match = re.search(r'평균\s+(\d+\.\d+)', rating_text)
            if rating_match:
                avg_rating = rating_match.group(1)
            
            # Extract rating count: "평균 3.8(1,358명)" -> "1358"
            count_match = re.search(r'\((\d+(?:,\d+)*)명\)', rating_text)
            if count_match:
                rating_count = count_match.group(1).replace(',', '')
        
        except Exception:
            pass
        
        return avg_rating, rating_count

