"""
Data models for recommendation evaluation
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MovieRecommendation(BaseModel):
    """Movie recommendation item"""

    movie_id: str = Field(..., description="Movie ID")
    title: str = Field(..., description="Movie title")
    year: Optional[int] = Field(default=None, description="Release year")
    genres: Optional[List[str]] = Field(default=None, description="Genres")
    description: Optional[str] = Field(default=None, description="Movie description")
    score: Optional[float] = Field(default=None, description="Recommendation score")
    rank: Optional[int] = Field(default=None, description="Recommendation rank")

    def to_display_text(self, include_description: bool = True) -> str:
        """Create display text"""
        text = f"{self.title} [id={self.movie_id}]"

        if self.year:
            text += f" ({self.year})"

        if self.genres:
            text += f" - Genres: {', '.join(self.genres)}"

        if include_description and self.description:
            desc = self.description[:200] + "..." if len(self.description) > 200 else self.description
            text += f"\n  {desc}"

        return text


class RecommendationList(BaseModel):
    """Recommendation list"""

    list_id: str = Field(..., description="List ID (A or B)")
    system_name: str = Field(..., description="Recommendation system name")
    recommendations: List[MovieRecommendation] = Field(..., description="Recommended movies")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    def to_display_text(self, include_descriptions: bool = True) -> str:
        """Create display text"""
        text = f"List {self.list_id} ({self.system_name}):\n"

        for i, rec in enumerate(self.recommendations, 1):
            text += f"{i}. {rec.to_display_text(include_descriptions)}\n"

        return text


class EvaluationResult(BaseModel):
    """LLM evaluation result"""

    preferred_list: Literal["A", "B", "none"] = Field(..., description="Preferred list")
    reasoning: str = Field(..., description="Reason for preference")
    liked_items_A: List[str] = Field(default_factory=list, description="Liked movie titles from List A")
    liked_items_B: List[str] = Field(default_factory=list, description="Liked movie titles from List B")
    clicked_item_ids_A: List[str] = Field(default_factory=list, description="Selected movie IDs from List A")
    clicked_item_ids_B: List[str] = Field(default_factory=list, description="Selected movie IDs from List B")
    timestamp: datetime = Field(default_factory=datetime.now, description="Evaluation timestamp")


class UserContext(BaseModel):
    """User context (information to consider during evaluation)"""

    user_description: str = Field(..., description="User description (preferred genres, moods, etc.)")
    additional_context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")

    def to_prompt_text(self) -> str:
        """Create text for prompt"""
        text = f"User: {self.user_description}"
        if self.additional_context:
            text += f"\nAdditional Context: {self.additional_context}"
        return text
