"""
LLM evaluation prompt templates (Pydantic based)

Structured prompt system similar to the Ragas framework
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """Base prompt template"""

    instruction: str = Field(..., description="Prompt instructions")
    input_keys: List[str] = Field(
        default_factory=list, description="Required input keys"
    )
    output_format: Optional[str] = Field(None, description="Output format description")

    def format(self, **kwargs) -> str:
        """Format the prompt"""
        missing_keys = [key for key in self.input_keys if key not in kwargs]
        if missing_keys:
            raise ValueError(f"Missing required keys: {missing_keys}")

        return self.instruction.format(**kwargs)


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
        default="You are evaluating movie recommendations for a user with the following profile:\n\n{profile_text}",
        description="Profile template",
    )

    def format(self, profile_text: str) -> str:
        """Format profile text"""
        return self.template.format(profile_text=profile_text)


class RecommendationListPrompt(BaseModel):
    """Recommendation list prompt component"""

    template: str = Field(
        default=(
            "Below are two recommendation lists from different systems. "
            "Each movie line includes its ID in the form '[id=<movie_id>]':\n\n{list_a_text}\n\n{list_b_text}"
        ),
        description="List template",
    )

    def format(self, list_a_text: str, list_b_text: str) -> str:
        """Format recommendation list text"""
        return self.template.format(list_a_text=list_a_text, list_b_text=list_b_text)


class TaskInstructionPrompt(BaseModel):
    """Task instruction prompt component"""

    task_description: str = Field(
        default=(
            "**Task**: Evaluate these two lists from the perspective of the user profile. "
            "State which list you prefer and why. For each list, pick the movies you would actually want to watch and provide their IDs exactly as shown."
        ),
        description="Task description",
    )
    considerations: List[str] = Field(
        default_factory=lambda: [
            "How well each list matches the user's genre preferences",
            "How well each list matches the user's mood preferences",
            "The diversity and quality of recommendations",
            "The overall appeal of the movies",
            "Select movies only from the provided lists; avoid inventing titles",
            "Select movie IDs only from the provided lists; do not invent IDs",
            "If no movies are appealing in a list, return an empty selection (and empty IDs) for that list",
        ],
        description="Considerations",
    )

    def to_string(self) -> str:
        """Convert task instructions to string"""
        prompt = self.task_description

        if self.considerations:
            prompt += "\n\nBe realistic and consider:"
            for i, consideration in enumerate(self.considerations, 1):
                prompt += f"\n{i}. {consideration}"

        return prompt


class OutputFormatPrompt(BaseModel):
    """Output format prompt component"""

    format_type: str = Field(default="json", description="Output format type")
    schema: Dict[str, str] = Field(
        default_factory=lambda: {
            "preferred_list": '"A" or "B" or "none"',
            "reasoning": '"Detailed explanation of why you prefer this list or why they are similar"',
            "liked_items_A": '["Exact movie title from List A", ...] (empty list if none)',
            "liked_items_B": '["Exact movie title from List B", ...] (empty list if none)',
            "clicked_item_ids_A": '["movie_id_from_List_A", ...] (exact IDs from the list, empty if none)',
            "clicked_item_ids_B": '["movie_id_from_List_B", ...] (exact IDs from the list, empty if none)',
        },
        description="Output schema",
    )
    strict_mode: bool = Field(
        default=True, description="Strict mode (JSON output only)"
    )

    def to_string(self) -> str:
        """Convert output format to string"""
        prompt = "Return one single-line JSON object with exactly these fields (no newlines inside the JSON):\n{"

        for key, description in self.schema.items():
            prompt += f'\n    "{key}": {description},'

        prompt = prompt.rstrip(",") + "\n}"

        prompt += (
            "\n\nUse exact movie titles from each list for liked_items_A and liked_items_B. "
            "For clicked_item_ids_A and clicked_item_ids_B, copy the movie IDs exactly as shown in the list lines (the value inside [id=<...>]). "
            "If no movies are appealing in a list, return empty arrays for that list."
        )

        prompt += (
            "\n\nFormatting rules:"
            "\n- Respond as ONE LINE. The first character must be '{' and the last must be '}'."
            "\n- Do NOT include any text before or after the JSON (no explanations, apologies, or code fences)."
            "\n- Use double quotes for all keys and string values; no trailing commas."
            '\n- If unsure about a field, choose the safest valid value (e.g., preferred_list="none", liked_items=[], clicked_item_ids=[]).'
            "\n- Final answer (replace with your values, keep it one line): "
            '{"preferred_list": "A|B|none", "reasoning": "text", "liked_items_A": [], "liked_items_B": [], "clicked_item_ids_A": [], "clicked_item_ids_B": []}'
        )

        if self.strict_mode:
            prompt += f"\n\nRespond with ONLY the {self.format_type.upper()} object, no additional text."

        return prompt


class EvaluationPrompt(BaseModel):
    """Movie recommendation evaluation prompt (full structure)"""

    system_prompt: SystemPrompt = Field(
        default_factory=lambda: SystemPrompt(
            role="an expert movie recommendation evaluator",
            expertise=[
                "Understanding user preferences and behavior",
                "Evaluating recommendation quality",
                "Simulating realistic user responses",
            ],
            guidelines=[
                "Be realistic and consider factors like relevance, diversity, and appeal",
                "Think from the user's perspective",
                "Provide honest and objective evaluations",
                "Only select movies that appear in the provided lists; do not invent titles",
                "Only use movie IDs that appear in the provided lists; do not invent IDs",
                "Movie IDs are shown in the list lines as [id=<movie_id>]—copy them exactly",
                "If a list has no appealing movies, explicitly return an empty selection (and empty IDs) for that list",
                "Output strictly as JSON: single line, first character '{', last character '}', no code fences or extra text",
            ],
        ),
        description="System prompt",
    )

    user_profile: UserProfilePrompt = Field(
        default_factory=UserProfilePrompt, description="User profile component"
    )

    recommendation_list: RecommendationListPrompt = Field(
        default_factory=RecommendationListPrompt,
        description="Recommendation list component",
    )

    task_instruction: TaskInstructionPrompt = Field(
        default_factory=TaskInstructionPrompt, description="Task instruction component"
    )

    output_format: OutputFormatPrompt = Field(
        default_factory=OutputFormatPrompt, description="Output format component"
    )

    def get_system_prompt(self) -> str:
        """Return system prompt"""
        return self.system_prompt.to_string()

    def create_user_prompt(
        self,
        profile_text: str,
        list_a_text: str,
        list_b_text: str,
    ) -> str:
        """
        Create user prompt

        Args:
            profile_text: User profile text
            list_a_text: List A text
            list_b_text: List B text

        Returns:
            Generated full prompt
        """
        sections = [
            self.user_profile.format(profile_text=profile_text),
            self.recommendation_list.format(
                list_a_text=list_a_text, list_b_text=list_b_text
            ),
            self.task_instruction.to_string(),
            self.output_format.to_string(),
        ]

        return "\n\n".join(sections)

    @classmethod
    def create_default(cls) -> "EvaluationPrompt":
        """Create default evaluation prompt"""
        return cls()

    @classmethod
    def create_custom(
        cls,
        role: Optional[str] = None,
        considerations: Optional[List[str]] = None,
        output_schema: Optional[Dict[str, str]] = None,
    ) -> "EvaluationPrompt":
        """
        Create custom evaluation prompt

        Args:
            role: Role of the LLM
            considerations: List of considerations
            output_schema: Output schema

        Returns:
            Custom evaluation prompt
        """
        kwargs = {}

        if role:
            kwargs["system_prompt"] = SystemPrompt(
                role=role,
                expertise=[
                    "Understanding user preferences",
                    "Evaluating recommendations",
                ],
                guidelines=["Be realistic", "Provide honest evaluations"],
            )

        if considerations:
            kwargs["task_instruction"] = TaskInstructionPrompt(
                considerations=considerations
            )

        if output_schema:
            kwargs["output_format"] = OutputFormatPrompt(schema=output_schema)

        return cls(**kwargs)


# Static helper for backward compatibility
def create_evaluation_prompt(
    profile_text: str,
    list_a_text: str,
    list_b_text: str,
    include_descriptions: bool = True,
) -> str:
    """
    Create evaluation prompt (backward compatibility)

    Args:
        profile_text: User profile text
        list_a_text: List A text
        list_b_text: List B text
        include_descriptions: Whether to include movie descriptions (currently unused)

    Returns:
        Generated prompt
    """
    prompt = EvaluationPrompt.create_default()
    return prompt.create_user_prompt(profile_text, list_a_text, list_b_text)
