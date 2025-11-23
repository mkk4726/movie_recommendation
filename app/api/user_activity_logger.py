"""
User Activity Logger Module

Logs user activities to local JSONL files for analytics and CTR prediction model training.
Uses IP addresses to identify users and tracks search, click, rating, and view events.
"""
import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from fastapi import Request

logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
ACTIVITY_LOGS_DIR = PROJECT_ROOT / "app" / "activity_logs"


class ActivityType(Enum):
    """Types of user activities to log"""
    SEARCH = "search"  # Natural language search
    POSTER_SEARCH = "poster_search"  # Poster-based search
    SEARCH_RESULT_CLICK = "search_result_click"  # Click on search result (for CTR)
    MOVIE_VIEW = "movie_view"  # Movie detail view
    RATING_ADD = "rating_add"  # Rating added
    RATING_UPDATE = "rating_update"  # Rating updated
    RATING_DELETE = "rating_delete"  # Rating deleted
    RECOMMENDATION_VIEW = "recommendation_view"  # Recommendation result view
    RECOMMENDATION_CLICK = "recommendation_click"  # Click on recommendation


class UserActivityLogger:
    """
    Logger for user activities using JSONL files.
    
    Each activity type is stored in a separate JSONL file for efficient querying.
    Users are identified by IP address.
    """
    
    def __init__(self, logs_dir: Path = ACTIVITY_LOGS_DIR):
        """
        Initialize the activity logger.
        
        Args:
            logs_dir: Directory to store log files
        """
        self.logs_dir = logs_dir
        # Ensure directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Define log file paths
        self.log_files = {
            ActivityType.SEARCH: self.logs_dir / "searches.jsonl",
            ActivityType.POSTER_SEARCH: self.logs_dir / "searches.jsonl",  # Same file
            ActivityType.SEARCH_RESULT_CLICK: self.logs_dir / "clicks.jsonl",
            ActivityType.RATING_ADD: self.logs_dir / "ratings.jsonl",
            ActivityType.RATING_UPDATE: self.logs_dir / "ratings.jsonl",  # Same file
            ActivityType.RATING_DELETE: self.logs_dir / "ratings.jsonl",  # Same file
            ActivityType.MOVIE_VIEW: self.logs_dir / "views.jsonl",
            ActivityType.RECOMMENDATION_VIEW: self.logs_dir / "recommendations.jsonl",
            ActivityType.RECOMMENDATION_CLICK: self.logs_dir / "recommendations.jsonl",  # Same file
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from FastAPI request.
        
        Handles proxy headers (X-Forwarded-For, X-Real-IP) for accurate IP detection.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Client IP address as string
        """
        # Check for proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client host
        return request.client.host if request.client else "unknown"
    
    def _append_log(self, activity_type: ActivityType, log_data: Dict[str, Any]) -> None:
        """
        Append a log entry to the appropriate JSONL file.
        
        Args:
            activity_type: Type of activity
            log_data: Log data dictionary
        """
        log_file = self.log_files[activity_type]
        
        try:
            # Add timestamp if not present
            if "timestamp" not in log_data:
                log_data["timestamp"] = datetime.now().isoformat()
            
            # Add activity type
            log_data["activity_type"] = activity_type.value
            
            # Append to file (create if doesn't exist)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
            
            logger.debug(f"Logged {activity_type.value}: {log_data.get('ip', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to log activity {activity_type.value}: {e}", exc_info=True)
    
    def log_search(
        self,
        request: Request,
        query: str,
        result_count: int,
        result_movie_ids: List[str],
        search_type: str = "natural_language"
    ) -> str:
        """
        Log a search event and return a session ID for click tracking.
        
        Args:
            request: FastAPI Request object
            query: Search query string
            result_count: Number of results returned
            result_movie_ids: List of movie IDs in the results
            search_type: Type of search ("natural_language" or "poster")
            
        Returns:
            Session ID for linking clicks to this search
        """
        session_id = str(uuid.uuid4())
        ip = self._get_client_ip(request)
        
        activity_type = (
            ActivityType.POSTER_SEARCH if search_type == "poster"
            else ActivityType.SEARCH
        )
        
        log_data = {
            "ip": ip,
            "session_id": session_id,
            "query": query,
            "search_type": search_type,
            "result_count": result_count,
            "result_movie_ids": result_movie_ids,
        }
        
        self._append_log(activity_type, log_data)
        return session_id
    
    def log_click(
        self,
        request: Request,
        session_id: str,
        movie_id: str,
        position: int,
        search_query: Optional[str] = None
    ) -> None:
        """
        Log a click event on a search result.
        
        Args:
            request: FastAPI Request object
            session_id: Search session ID
            movie_id: ID of clicked movie
            position: Position in search results (0-indexed)
            search_query: Original search query (optional, for convenience)
        """
        ip = self._get_client_ip(request)
        
        log_data = {
            "ip": ip,
            "session_id": session_id,
            "movie_id": movie_id,
            "position": position,
        }
        
        if search_query:
            log_data["search_query"] = search_query
        
        self._append_log(ActivityType.SEARCH_RESULT_CLICK, log_data)
    
    def log_rating(
        self,
        request: Request,
        movie_id: str,
        rating: float,
        action: str = "add"
    ) -> None:
        """
        Log a rating event.
        
        Args:
            request: FastAPI Request object
            movie_id: Movie ID
            rating: Rating value (0.5 - 5.0)
            action: Action type ("add", "update", or "delete")
        """
        ip = self._get_client_ip(request)
        
        activity_type_map = {
            "add": ActivityType.RATING_ADD,
            "update": ActivityType.RATING_UPDATE,
            "delete": ActivityType.RATING_DELETE,
        }
        
        activity_type = activity_type_map.get(action, ActivityType.RATING_ADD)
        
        log_data = {
            "ip": ip,
            "movie_id": movie_id,
            "rating": rating,
            "action": action,
        }
        
        self._append_log(activity_type, log_data)
    
    def log_view(
        self,
        request: Request,
        movie_id: str,
        view_context: Optional[str] = None
    ) -> None:
        """
        Log a movie view event.
        
        Args:
            request: FastAPI Request object
            movie_id: Movie ID
            view_context: Context of view (e.g., "search", "recommendation", "similar")
        """
        ip = self._get_client_ip(request)
        
        log_data = {
            "ip": ip,
            "movie_id": movie_id,
        }
        
        if view_context:
            log_data["view_context"] = view_context
        
        self._append_log(ActivityType.MOVIE_VIEW, log_data)
    
    def log_recommendation(
        self,
        request: Request,
        recommendation_type: str,
        result_movie_ids: List[str],
        user_id: Optional[str] = None
    ) -> None:
        """
        Log a recommendation view event.
        
        Args:
            request: FastAPI Request object
            recommendation_type: Type of recommendation (e.g., "user_based", "item_based")
            result_movie_ids: List of recommended movie IDs
            user_id: User ID if applicable
        """
        ip = self._get_client_ip(request)
        
        log_data = {
            "ip": ip,
            "recommendation_type": recommendation_type,
            "result_movie_ids": result_movie_ids,
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        self._append_log(ActivityType.RECOMMENDATION_VIEW, log_data)
    
    def get_ctr_data(
        self,
        ip_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get CTR data by joining search and click logs.
        
        Args:
            ip_filter: Filter by specific IP address (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
            
        Returns:
            List of CTR data points with search and click information
        """
        ctr_data = []
        
        try:
            # Load searches
            searches = {}
            search_file = self.log_files[ActivityType.SEARCH]
            
            if search_file.exists():
                with open(search_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            log = json.loads(line.strip())
                            
                            # Apply filters
                            if ip_filter and log.get("ip") != ip_filter:
                                continue
                            
                            log_time = datetime.fromisoformat(log["timestamp"])
                            if start_date and log_time < start_date:
                                continue
                            if end_date and log_time > end_date:
                                continue
                            
                            session_id = log.get("session_id")
                            if session_id:
                                searches[session_id] = log
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Invalid search log line: {e}")
                            continue
            
            # Load clicks and join with searches
            click_file = self.log_files[ActivityType.SEARCH_RESULT_CLICK]
            
            if click_file.exists():
                with open(click_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            click_log = json.loads(line.strip())
                            
                            # Apply filters
                            if ip_filter and click_log.get("ip") != ip_filter:
                                continue
                            
                            click_time = datetime.fromisoformat(click_log["timestamp"])
                            if start_date and click_time < start_date:
                                continue
                            if end_date and click_time > end_date:
                                continue
                            
                            session_id = click_log.get("session_id")
                            if session_id and session_id in searches:
                                search_log = searches[session_id]
                                
                                ctr_data.append({
                                    "session_id": session_id,
                                    "ip": click_log["ip"],
                                    "search_query": search_log.get("query"),
                                    "search_type": search_log.get("search_type"),
                                    "search_timestamp": search_log["timestamp"],
                                    "search_results": search_log.get("result_movie_ids", []),
                                    "clicked_movie_id": click_log.get("movie_id"),
                                    "click_position": click_log.get("position"),
                                    "click_timestamp": click_log["timestamp"],
                                })
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Invalid click log line: {e}")
                            continue
        
        except Exception as e:
            logger.error(f"Failed to get CTR data: {e}", exc_info=True)
        
        return ctr_data
    
    def get_stats(self, ip: Optional[str] = None) -> Dict[str, Any]:
        """
        Get activity statistics.
        
        Args:
            ip: Filter by specific IP address (optional)
            
        Returns:
            Dictionary with activity statistics
        """
        stats = {
            "total_searches": 0,
            "total_clicks": 0,
            "total_ratings": 0,
            "total_views": 0,
            "ctr": 0.0,
        }
        
        try:
            # Count searches
            search_file = self.log_files[ActivityType.SEARCH]
            if search_file.exists():
                with open(search_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            log = json.loads(line.strip())
                            if ip is None or log.get("ip") == ip:
                                stats["total_searches"] += 1
                        except json.JSONDecodeError:
                            continue
            
            # Count clicks
            click_file = self.log_files[ActivityType.SEARCH_RESULT_CLICK]
            if click_file.exists():
                with open(click_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            log = json.loads(line.strip())
                            if ip is None or log.get("ip") == ip:
                                stats["total_clicks"] += 1
                        except json.JSONDecodeError:
                            continue
            
            # Calculate CTR
            if stats["total_searches"] > 0:
                stats["ctr"] = stats["total_clicks"] / stats["total_searches"]
            
            # Count ratings
            rating_file = self.log_files[ActivityType.RATING_ADD]
            if rating_file.exists():
                with open(rating_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            log = json.loads(line.strip())
                            if ip is None or log.get("ip") == ip:
                                stats["total_ratings"] += 1
                        except json.JSONDecodeError:
                            continue
            
            # Count views
            view_file = self.log_files[ActivityType.MOVIE_VIEW]
            if view_file.exists():
                with open(view_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            log = json.loads(line.strip())
                            if ip is None or log.get("ip") == ip:
                                stats["total_views"] += 1
                        except json.JSONDecodeError:
                            continue
        
        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
        
        return stats


# Global logger instance
_activity_logger: Optional[UserActivityLogger] = None


def get_activity_logger() -> UserActivityLogger:
    """Get or create the global activity logger instance."""
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = UserActivityLogger()
    return _activity_logger
