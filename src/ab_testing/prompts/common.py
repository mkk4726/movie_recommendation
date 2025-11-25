"""
Common prompt components shared across different prompt types
"""

from typing import List

from pydantic import BaseModel, Field


class SystemPrompt(BaseModel):
    """System prompt"""

    role: str = Field(..., description="Role of the LLM")
    expertise: List[str] = Field(default_factory=list, description="Areas of expertise")
    guidelines: List[str] = Field(
        default_factory=list, description="Guidelines to follow"
    )

    def to_string(self) -> str:
        """Convert system prompt to string"""
        prompt = f"You are {self.role}."

        if self.expertise:
            prompt += "\n\nYour expertise includes:"
            for exp in self.expertise:
                prompt += f"\n- {exp}"

        if self.guidelines:
            prompt += "\n\nGuidelines:"
            for guideline in self.guidelines:
                prompt += f"\n- {guideline}"

        return prompt


class UserProfilePrompt(BaseModel):
    """User profile prompt component"""

    template: str = Field(
        default="User Profile:\n{profile_text}",
        description="Profile template",
    )

    def format(self, profile_text: str) -> str:
        """Format profile text"""
        return self.template.format(profile_text=profile_text)


# Common JSON formatting rules
JSON_FORMATTING_RULES = (
    "Formatting rules:\n"
    "- Respond as ONE LINE. The first character must be '{' and the last "
    "must be '}'.\n"
    "- Do NOT include any text before or after the JSON (no explanations, "
    "apologies, or code fences).\n"
    "- Use double quotes for all keys and string values; no trailing commas."
)

JSON_OUTPUT_GUIDELINE = (
    "Output strictly as JSON: single line, first character '{', "
    "last character '}', no code fences or extra text"
)
