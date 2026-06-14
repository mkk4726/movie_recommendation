"""
Query generation prompt templates

Generates service-specific queries from user context
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .common import (
    JSON_FORMATTING_RULES,
    JSON_OUTPUT_GUIDELINE,
    SystemPrompt,
)


class QueryGenerationPrompt(BaseModel):
    """Query generation prompt for service-specific queries"""

    system_prompt: SystemPrompt = Field(
        default_factory=lambda: SystemPrompt(
            role="an expert query generator for movie recommendation systems",
            expertise=[
                "Understanding user preferences and intent",
                "Generating natural language search queries",
                "Creating effective search terms based on user context",
            ],
            guidelines=[
                "Generate queries that accurately reflect the user's preferences and intent",
                "Keep queries concise and focused",
                "Use natural language that users would actually type",
                "Consider genre preferences, mood, and other context",
                JSON_OUTPUT_GUIDELINE,
            ],
        ),
        description="System prompt",
    )

    service_type: Literal["natural_language_search", "poster_search", "other"] = Field(
        default="natural_language_search",
        description="Type of service to generate query for",
    )

    def get_system_prompt(self) -> str:
        """Return system prompt"""
        return self.system_prompt.to_string()

    def create_user_prompt(
        self,
        profile_text: str,
        service_type: Optional[str] = None,
    ) -> str:
        """
        Create user prompt for query generation

        Args:
            profile_text: User profile text
            service_type: Type of service (natural_language_search, poster_search, etc.)

        Returns:
            Generated full prompt
        """
        service = service_type or self.service_type

        # Few-shot examples for each service type
        few_shot_examples = {
            "natural_language_search": """Example 1:
User Profile:
I love action movies with strong female leads. Prefer sci-fi and thriller genres. Enjoy movies with intense fight scenes and compelling storylines.

Output:
{"query": "action movies strong female leads sci-fi", "reasoning": "Captures the user's preference for action, sci-fi genre, and strong female leads in a concise searchable format"}

Example 2:
User Profile:
Looking for romantic comedies from the 90s. Prefer light-hearted stories with good chemistry between leads.

Output:
{"query": "90s romantic comedies", "reasoning": "Focuses on the specific decade and genre preference in a natural search query format"}

Example 3:
User Profile:
Interested in psychological thrillers with plot twists. Prefer dark, atmospheric films that keep you guessing.

Output:
{"query": "psychological thriller plot twists", "reasoning": "Captures the genre and key feature (plot twists) that the user values"}""",
            "poster_search": """Example 1:
User Profile:
I love action movies with strong female leads. Prefer sci-fi and thriller genres. Enjoy movies with intense fight scenes and compelling storylines.

Output:
{"query": "futuristic sci-fi action poster neon colors", "reasoning": "Describes visual elements (futuristic, neon colors) that would appear in sci-fi action movie posters matching the user's preferences"}

Example 2:
User Profile:
Looking for romantic comedies from the 90s. Prefer light-hearted stories with good chemistry between leads.

Output:
{"query": "vintage 90s romantic poster warm colors", "reasoning": "Focuses on visual style elements (vintage, warm colors) that characterize 90s romantic comedy posters"}

Example 3:
User Profile:
Interested in psychological thrillers with plot twists. Prefer dark, atmospheric films that keep you guessing.

Output:
{"query": "dark moody thriller poster shadowy", "reasoning": "Describes the dark, atmospheric visual style typical of psychological thriller posters"}""",
            "other": """Example 1:
User Profile:
I love action movies with strong female leads. Prefer sci-fi and thriller genres. Enjoy movies with intense fight scenes and compelling storylines.

Output:
{"query": "action sci-fi female leads", "reasoning": "Generates a search query that captures the key preferences: action genre, sci-fi elements, and strong female leads"}

Example 2:
User Profile:
Looking for romantic comedies from the 90s. Prefer light-hearted stories with good chemistry between leads.

Output:
{"query": "romantic comedy 90s", "reasoning": "Creates a straightforward search query combining the genre and time period preferences"}""",
        }

        examples = few_shot_examples.get(service, few_shot_examples["other"])

        prompt = f"""You are generating a search query for a movie recommendation system.

Few-shot Examples:
{examples}

Now generate a query for the following user profile:

User Profile:
{profile_text}

Output Format:
Return a JSON object with exactly these fields:
{{
    "query": "the generated search query string",
    "reasoning": "brief explanation of why this query was generated"
}}

{JSON_FORMATTING_RULES}
- The query should be a single string, typically 1-10 words for natural language search.
- Follow the pattern shown in the examples above.
- Final answer format: {{"query": "your query here", "reasoning": "your reasoning"}}
"""

        return prompt

    @classmethod
    def create_default(cls) -> "QueryGenerationPrompt":
        """Create default query generation prompt"""
        return cls()

    @classmethod
    def create_for_service(
        cls,
        service_type: Literal["natural_language_search", "poster_search", "other"],
    ) -> "QueryGenerationPrompt":
        """
        Create query generation prompt for specific service type

        Args:
            service_type: Type of service

        Returns:
            Query generation prompt configured for the service
        """
        return cls(service_type=service_type)
