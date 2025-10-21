"""Data storage utilities for TXT-based persistence with '/' delimiter."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from .config import Config
from .logger import get_logger


class DataStorage:
    """Handles reading and writing data to TXT files with '/' delimiter."""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize data storage.
        
        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.logger = get_logger(__name__, level=self.config.LOG_LEVEL)
        
        # Ensure data directory exists
        Path(self.config.DATA_DIR).mkdir(parents=True, exist_ok=True)
    
    def get_movie_info_path(self) -> str:
        """Get full path to movie info file."""
        return os.path.join(self.config.DATA_DIR, self.config.MOVIE_INFO_FILE)
    
    def get_movie_comments_path(self) -> str:
        """Get full path to movie comments file."""
        return os.path.join(self.config.DATA_DIR, self.config.MOVIE_COMMENTS_FILE)
    
    def get_custom_rating_path(self) -> str:
        """Get full path to custom rating file."""
        return os.path.join(self.config.DATA_DIR, self.config.CUSTOM_RATING_FILE)
    
    def save_movie_info(self, movie_data: Dict[str, Any]) -> None:
        """
        Save movie info to TXT file.
        
        Args:
            movie_data: Movie information dictionary
        """
        file_path = self.get_movie_info_path()
        
        # Convert cast_production list to string (semicolon separated)
        cast_str = '; '.join([f"{name}({role})" for name, role in movie_data.get('cast_production', [])])
        
        # Prepare data in order
        data_list = [
            str(movie_data.get('movie_id', '')),
            str(movie_data.get('title', '')),
            str(movie_data.get('year', '')),
            str(movie_data.get('genre', '')),
            str(movie_data.get('country', '')),
            str(movie_data.get('runtime', '')),
            str(movie_data.get('age', '')),
            cast_str,
            str(movie_data.get('synopsis', '')),
            str(movie_data.get('avg_rating', '')),
            str(movie_data.get('n_rating', '')),
            str(movie_data.get('n_comments', '')),
        ]
        
        self._append_to_txt(file_path, data_list)
        self.logger.debug(f"Saved movie info: {movie_data.get('movie_id')}")
    
    def save_movie_comment(self, movie_id: str, comment_data: Dict[str, Any]) -> None:
        """
        Save movie comment to TXT file.
        
        Args:
            movie_id: Movie ID
            comment_data: Comment information dictionary
        """
        file_path = self.get_movie_comments_path()
        
        data_list = [
            str(movie_id),
            str(comment_data.get('custom_id', '')),
            str(comment_data.get('comment', '')),
            str(comment_data.get('rating', '')),
            str(comment_data.get('n_likes', '')),
        ]
        
        self._append_to_txt(file_path, data_list)
    
    def save_movie_comments_batch(self, movie_id: str, comments: List[Dict[str, Any]]) -> None:
        """
        Save multiple comments at once (batch operation for better performance).
        
        Args:
            movie_id: Movie ID
            comments: List of comment information dictionaries
        """
        if not comments:
            return
        
        file_path = self.get_movie_comments_path()
        
        lines = []
        for comment_data in comments:
            data_list = [
                str(movie_id),
                str(comment_data.get('custom_id', '')),
                str(comment_data.get('comment', '')),
                str(comment_data.get('rating', '')),
                str(comment_data.get('n_likes', '')),
            ]
            lines.append(self.config.DATA_SEPARATOR.join(data_list))
        
        # Single file operation for all comments
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        
        self.logger.debug(f"Batch saved {len(comments)} comments for movie {movie_id}")
    
    def save_custom_rating(self, custom_id: str, rating_data: Dict[str, Any]) -> None:
        """
        Save custom rating to TXT file.
        
        Args:
            custom_id: User ID
            rating_data: Rating information dictionary
        """
        file_path = self.get_custom_rating_path()
        
        data_list = [
            str(custom_id),
            str(rating_data.get('movie_id', '')),
            str(rating_data.get('movie_name', '')),
            str(rating_data.get('rating', '')),
        ]
        
        self._append_to_txt(file_path, data_list)
    
    def _append_to_txt(self, file_path: str, data: List[str]) -> None:
        """
        Append data row to TXT file with '/' delimiter.
        
        Args:
            file_path: Path to TXT file
            data: List of values to write
        """
        line = self.config.DATA_SEPARATOR.join(data) + "\n"
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def _read_txt(self, file_path: str) -> List[List[str]]:
        """
        Read TXT file and parse rows.
        
        Args:
            file_path: Path to TXT file
        
        Returns:
            List of rows (each row is a list of values)
        """
        rows = []
        
        if not os.path.exists(file_path):
            return rows
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    rows.append(line.strip().split(self.config.DATA_SEPARATOR))
        
        return rows
    
    def load_movie_info(self) -> pd.DataFrame:
        """
        Load movie info from TXT file.
        
        Returns:
            DataFrame with movie information
        """
        file_path = self.get_movie_info_path()
        
        if not os.path.exists(file_path):
            self.logger.warning(f"Movie info file not found: {file_path}")
            return pd.DataFrame()
        
        rows = self._read_txt(file_path)
        
        columns = [
            'MovieID', 'Title', 'Year', 'Genre', 'Country', 'Runtime', 
            'Age', 'Cast_Production', 'Synopsis', 'Avg_Rating', 'N_Rating', 'N_Comments'
        ]
        
        return pd.DataFrame(rows, columns=columns)
    
    def load_movie_comments(self) -> pd.DataFrame:
        """
        Load movie comments from TXT file.
        
        Returns:
            DataFrame with movie comments
        """
        file_path = self.get_movie_comments_path()
        
        if not os.path.exists(file_path):
            self.logger.warning(f"Movie comments file not found: {file_path}")
            return pd.DataFrame()
        
        rows = self._read_txt(file_path)
        
        columns = ['MovieID', 'CustomID', 'Comment', 'Rating', 'N_Likes']
        
        return pd.DataFrame(rows, columns=columns)
    
    def load_custom_rating(self) -> pd.DataFrame:
        """
        Load custom ratings from TXT file.
        
        Returns:
            DataFrame with custom ratings
        """
        file_path = self.get_custom_rating_path()
        
        if not os.path.exists(file_path):
            self.logger.warning(f"Custom rating file not found: {file_path}")
            return pd.DataFrame()
        
        rows = self._read_txt(file_path)
        
        columns = ['CustomID', 'MovieID', 'MovieName', 'Rating']
        
        return pd.DataFrame(rows, columns=columns)
    
    def get_missing_movie_ids(self) -> List[str]:
        """
        Get movie IDs that need info scraping.
        
        Returns:
            List of movie IDs
        """
        try:
            custom_ratings = self.load_custom_rating()
            movie_info = self.load_movie_info()
            
            if custom_ratings.empty:
                return []
            
            # Filter out movies that already have valid info
            if not movie_info.empty and 'Title' in movie_info.columns:
                valid_movie_ids = set(movie_info[movie_info['Title'].notna()]['MovieID'])
            else:
                valid_movie_ids = set()
            
            all_movie_ids = set(custom_ratings['MovieID'])
            missing_ids = list(all_movie_ids - valid_movie_ids)
            
            self.logger.info(f"Found {len(missing_ids)} movies needing info scraping")
            return missing_ids
            
        except Exception as e:
            self.logger.error(f"Error getting missing movie IDs: {e}")
            return []
    
    def get_missing_comment_movie_ids(self) -> List[str]:
        """
        Get movie IDs that need comment scraping.
        Uses optimized set-based approach for better performance.
        
        Returns:
            List of movie IDs
        """
        try:
            custom_ratings = self.load_custom_rating()
            
            if custom_ratings.empty:
                return []
            
            all_movie_ids = set(custom_ratings['MovieID'])
            
            # Optimized: Only read MovieID column from comments file
            comments_file = self.get_movie_comments_path()
            scraped_movie_ids = set()
            
            if os.path.exists(comments_file):
                with open(comments_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            # First column is MovieID
                            movie_id = line.split(self.config.DATA_SEPARATOR)[0]
                            scraped_movie_ids.add(movie_id)
            
            missing_ids = list(all_movie_ids - scraped_movie_ids)
            
            self.logger.info(f"Found {len(missing_ids)} movies needing comment scraping")
            return missing_ids
            
        except Exception as e:
            self.logger.error(f"Error getting missing comment movie IDs: {e}")
            return []
    
    def get_missing_custom_ids(self) -> List[str]:
        """
        Get custom IDs (users) that need rating scraping.
        
        Returns:
            List of custom IDs
        """
        try:
            comments = self.load_movie_comments()
            custom_ratings = self.load_custom_rating()
            
            if comments.empty:
                return []
            
            all_custom_ids = set(comments['CustomID'])
            
            if not custom_ratings.empty and 'CustomID' in custom_ratings.columns:
                scraped_custom_ids = set(custom_ratings['CustomID'])
            else:
                scraped_custom_ids = set()
            
            missing_ids = list(all_custom_ids - scraped_custom_ids)
            
            self.logger.info(f"Found {len(missing_ids)} users needing rating scraping")
            return missing_ids
            
        except Exception as e:
            self.logger.error(f"Error getting missing custom IDs: {e}")
            return []
