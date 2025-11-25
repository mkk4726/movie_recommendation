"""
LLM 평가 프롬프트 템플릿 (Pydantic 기반)

Ragas 프레임워크와 유사한 구조화된 프롬프트 시스템
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """기본 프롬프트 템플릿"""

    instruction: str = Field(..., description="프롬프트 지시사항")
    input_keys: List[str] = Field(default_factory=list, description="필요한 입력 키들")
    output_format: Optional[str] = Field(None, description="출력 형식 설명")

    def format(self, **kwargs) -> str:
        """프롬프트를 포맷팅"""
        missing_keys = [key for key in self.input_keys if key not in kwargs]
        if missing_keys:
            raise ValueError(f"Missing required keys: {missing_keys}")

        return self.instruction.format(**kwargs)


class SystemPrompt(BaseModel):
    """시스템 프롬프트"""

    role: str = Field(..., description="LLM의 역할")
    expertise: List[str] = Field(default_factory=list, description="전문 분야")
    guidelines: List[str] = Field(default_factory=list, description="따라야 할 가이드라인")

    def to_string(self) -> str:
        """시스템 프롬프트를 문자열로 변환"""
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
    """사용자 프로필 프롬프트 컴포넌트"""

    template: str = Field(
        default="You are evaluating movie recommendations for a user with the following profile:\n\n{profile_text}",
        description="프로필 템플릿",
    )

    def format(self, profile_text: str) -> str:
        """프로필 텍스트 포맷팅"""
        return self.template.format(profile_text=profile_text)


class RecommendationListPrompt(BaseModel):
    """추천 리스트 프롬프트 컴포넌트"""

    template: str = Field(
        default="Below are two recommendation lists from different systems:\n\n{list_a_text}\n\n{list_b_text}",
        description="리스트 템플릿",
    )

    def format(self, list_a_text: str, list_b_text: str) -> str:
        """추천 리스트 텍스트 포맷팅"""
        return self.template.format(list_a_text=list_a_text, list_b_text=list_b_text)


class TaskInstructionPrompt(BaseModel):
    """작업 지시 프롬프트 컴포넌트"""

    task_description: str = Field(
        default="**Task**: Evaluate these two lists from the perspective of the user profile.",
        description="작업 설명",
    )
    considerations: List[str] = Field(
        default_factory=lambda: [
            "How well each list matches the user's genre preferences",
            "How well each list matches the user's mood preferences",
            "The diversity and quality of recommendations",
            "The overall appeal of the movies",
        ],
        description="고려사항",
    )

    def to_string(self) -> str:
        """작업 지시를 문자열로 변환"""
        prompt = self.task_description

        if self.considerations:
            prompt += "\n\nBe realistic and consider:"
            for i, consideration in enumerate(self.considerations, 1):
                prompt += f"\n{i}. {consideration}"

        return prompt


class OutputFormatPrompt(BaseModel):
    """출력 형식 프롬프트 컴포넌트"""

    format_type: str = Field(default="json", description="출력 형식 타입")
    schema: Dict[str, str] = Field(
        default_factory=lambda: {
            "preferred_list": '"A" or "B" or "none"',
            "reasoning": '"Detailed explanation of why you prefer this list or why they are similar"',
            "click_probability_A": "0.0 to 1.0 (how likely you would click on any movie in List A)",
            "click_probability_B": "0.0 to 1.0 (how likely you would click on any movie in List B)",
            "relevance_score_A": "0 to 10 (how relevant is List A to the user profile)",
            "relevance_score_B": "0 to 10 (how relevant is List B to the user profile)",
        },
        description="출력 스키마",
    )
    strict_mode: bool = Field(default=True, description="엄격 모드 (JSON만 출력)")

    def to_string(self) -> str:
        """출력 형식을 문자열로 변환"""
        prompt = f"Please respond in the following {self.format_type.upper()} format:\n{{"

        for key, description in self.schema.items():
            prompt += f'\n    "{key}": {description},'

        prompt = prompt.rstrip(",") + "\n}"

        if self.strict_mode:
            prompt += f"\n\nRespond with ONLY the {self.format_type.upper()} object, no additional text."

        return prompt


class EvaluationPrompt(BaseModel):
    """영화 추천 평가 프롬프트 (전체 구성)"""

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
            ],
        ),
        description="시스템 프롬프트",
    )

    user_profile: UserProfilePrompt = Field(
        default_factory=UserProfilePrompt, description="사용자 프로필 컴포넌트"
    )

    recommendation_list: RecommendationListPrompt = Field(
        default_factory=RecommendationListPrompt, description="추천 리스트 컴포넌트"
    )

    task_instruction: TaskInstructionPrompt = Field(
        default_factory=TaskInstructionPrompt, description="작업 지시 컴포넌트"
    )

    output_format: OutputFormatPrompt = Field(
        default_factory=OutputFormatPrompt, description="출력 형식 컴포넌트"
    )

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return self.system_prompt.to_string()

    def create_user_prompt(
        self,
        profile_text: str,
        list_a_text: str,
        list_b_text: str,
    ) -> str:
        """
        사용자 프롬프트 생성

        Args:
            profile_text: 사용자 프로필 텍스트
            list_a_text: 리스트 A 텍스트
            list_b_text: 리스트 B 텍스트

        Returns:
            생성된 전체 프롬프트
        """
        sections = [
            self.user_profile.format(profile_text=profile_text),
            self.recommendation_list.format(list_a_text=list_a_text, list_b_text=list_b_text),
            self.task_instruction.to_string(),
            self.output_format.to_string(),
        ]

        return "\n\n".join(sections)

    @classmethod
    def create_default(cls) -> "EvaluationPrompt":
        """기본 평가 프롬프트 생성"""
        return cls()

    @classmethod
    def create_custom(
        cls,
        role: Optional[str] = None,
        considerations: Optional[List[str]] = None,
        output_schema: Optional[Dict[str, str]] = None,
    ) -> "EvaluationPrompt":
        """
        커스텀 평가 프롬프트 생성

        Args:
            role: LLM의 역할
            considerations: 고려사항 리스트
            output_schema: 출력 스키마

        Returns:
            커스텀 평가 프롬프트
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
            kwargs["task_instruction"] = TaskInstructionPrompt(considerations=considerations)

        if output_schema:
            kwargs["output_format"] = OutputFormatPrompt(schema=output_schema)

        return cls(**kwargs)


# 하위 호환성을 위한 정적 메서드
def create_evaluation_prompt(
    profile_text: str,
    list_a_text: str,
    list_b_text: str,
    include_descriptions: bool = True,
) -> str:
    """
    평가 프롬프트 생성 (하위 호환성)

    Args:
        profile_text: 사용자 프로필 텍스트
        list_a_text: 리스트 A 텍스트
        list_b_text: 리스트 B 텍스트
        include_descriptions: 영화 설명 포함 여부 (현재 미사용)

    Returns:
        생성된 프롬프트
    """
    prompt = EvaluationPrompt.create_default()
    return prompt.create_user_prompt(profile_text, list_a_text, list_b_text)
