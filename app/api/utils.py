"""
Utility functions for API endpoints.
"""
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
from fastapi import Request

from user_system.firebase_config import get_firebase_manager


def get_current_user_from_cookies(request: Request) -> Optional[Dict[str, Any]]:
    """쿠키에서 현재 사용자 정보 가져오기"""
    try:
        from user_system.firebase_config import FIREBASE_AVAILABLE
        if not FIREBASE_AVAILABLE:
            return None
    except ImportError:
        return None
    
    try:
        auth_token = request.cookies.get("auth_token")
        user_uid = request.cookies.get("user_uid")
        
        if auth_token and user_uid and auth_token.startswith("demo_token_"):
            firebase_manager = get_firebase_manager()
            if not firebase_manager.initialized:
                return None
            
            db = firebase_manager.get_firestore()
            user_doc = db.collection("users").document(user_uid).get()
            
            if user_doc.exists:
                return user_doc.to_dict()
            else:
                # 기본 사용자 정보
                return {
                    "uid": user_uid,
                    "email": "user@example.com",
                    "display_name": "User"
                }
    except Exception:
        pass
    
    return None


def _safe_number(value) -> Optional[float]:
    """Convert numpy/NaN values to native floats."""
    if value is None:
        return None
    if isinstance(value, (float, int)):
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return None
        return float(value)
    if isinstance(value, (np.integer, np.floating)):
        if np.isnan(value):
            return None
        return float(value)
    return None


def _safe_year(value) -> Optional[int]:
    number = _safe_number(value)
    if number is None:
        return None
    return int(number)


def from_dataframe(
    df: pd.DataFrame,
    *,
    include_rating: bool = False,
    include_predicted: bool = False,
    include_similarity: bool = False,
) -> List[dict]:
    """Convert pandas DataFrame to list of dictionaries for API responses."""
    if df is None or df.empty:
        return []

    records = []
    for row in df.to_dict(orient="records"):
        title = row.get("title") or row.get("movie_title")
        record = {
            "movie_id": str(row.get("movie_id", "")),
            "title": title,
            "genre": row.get("genre"),
            "year": _safe_year(row.get("year")),
        }
        if include_rating:
            record["rating"] = _safe_number(row.get("rating"))
        if include_predicted:
            record["predicted_rating"] = _safe_number(row.get("predicted_rating"))
        if include_similarity:
            record["similarity"] = _safe_number(row.get("similarity"))
        records.append(record)
    return records

