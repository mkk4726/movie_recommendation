"""
LLM 기반 추천 결과 평가기
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Optional

import yaml

from llm import Qwen, LLMConfig

from ..models import EvaluationResult, RecommendationList, UserContext
from .prompts import EvaluationPrompt

logger = logging.getLogger(__name__)


class LLMEvaluator:
    """LLM 기반 추천 평가기"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        llm: Optional[Qwen] = None,
        prompt_template: Optional[EvaluationPrompt] = None,
    ):
        """
        Args:
            config_path: 설정 파일 경로
            llm: 사용할 Qwen 인스턴스 (None이면 새로 생성)
            prompt_template: 프롬프트 템플릿 (None이면 기본값 사용)
        """
        # 설정 로드
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self.llm_config = config["llm"]
        self.eval_config = config["evaluation"]

        # 프롬프트 템플릿 초기화
        if prompt_template is None:
            self.prompt_template = EvaluationPrompt.create_default()
        else:
            self.prompt_template = prompt_template

        # LLM 초기화
        if llm is None:
            llm_cfg = LLMConfig(
                model_name=self.llm_config["model_name"],
                max_new_tokens=self.llm_config["max_new_tokens"],
                temperature=self.llm_config["temperature"],
                top_p=self.llm_config["top_p"],
                do_sample=self.llm_config["do_sample"],
            )
            self.llm = Qwen(config=llm_cfg)
        else:
            self.llm = llm

        logger.info("✅ LLM Evaluator 초기화 완료")

    def evaluate_lists(
        self,
        user_context: UserContext,
        list_a: RecommendationList,
        list_b: RecommendationList,
    ) -> EvaluationResult:
        """
        두 추천 리스트를 평가

        Args:
            user_context: 사용자 컨텍스트 (선호도 등)
            list_a: 추천 리스트 A
            list_b: 추천 리스트 B

        Returns:
            EvaluationResult 객체
        """
        # 프롬프트 생성
        include_descriptions = self.eval_config.get("include_movie_descriptions", True)

        user_prompt = self.prompt_template.create_user_prompt(
            profile_text=user_context.to_prompt_text(),
            list_a_text=list_a.to_display_text(include_descriptions=include_descriptions),
            list_b_text=list_b.to_display_text(include_descriptions=include_descriptions),
        )

        # LLM 호출
        try:
            system_prompt = self.prompt_template.get_system_prompt()

            response = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=self.llm_config["temperature"],
            )

            # 응답 파싱
            evaluation = self._parse_response(response)

            logger.info(
                "✅ 평가 완료: 선호=%s, liked_A=%d, liked_B=%d, clicked_ids_A=%d, clicked_ids_B=%d",
                evaluation.preferred_list,
                len(evaluation.liked_items_A),
                len(evaluation.liked_items_B),
                len(evaluation.clicked_item_ids_A),
                len(evaluation.clicked_item_ids_B),
            )

            return evaluation

        except Exception as e:
            logger.error(f"❌ 평가 중 오류 발생: {e}")
            return self._create_fallback_evaluation()

    def _parse_response(self, response: str) -> EvaluationResult:
        """LLM 응답을 파싱하여 EvaluationResult 생성"""
        try:
            # JSON 추출 시도
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
            else:
                data = json.loads(response)

            # 필수 필드 검증 및 기본값 설정
            preferred_list = data.get("preferred_list", "none")
            if preferred_list not in ["A", "B", "none"]:
                preferred_list = "none"

            reasoning = data.get("reasoning", "No reasoning provided")

            # EvaluationResult 생성
            evaluation = EvaluationResult(
                preferred_list=preferred_list,
                reasoning=reasoning,
                liked_items_A=self._normalize_str_list(data.get("liked_items_A")),
                liked_items_B=self._normalize_str_list(data.get("liked_items_B")),
                clicked_item_ids_A=self._normalize_str_list(data.get("clicked_item_ids_A")),
                clicked_item_ids_B=self._normalize_str_list(data.get("clicked_item_ids_B")),
            )

            return evaluation

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"⚠️  응답 파싱 실패: {e}. Fallback 사용.")
            logger.debug(f"원본 응답: {response[:200]}...")
            return self._create_fallback_evaluation()

    def _create_fallback_evaluation(self) -> EvaluationResult:
        """파싱 실패 시 기본 평가 생성"""
        return EvaluationResult(
            preferred_list="none",
            reasoning="Evaluation failed - using fallback neutral response",
            liked_items_A=[],
            liked_items_B=[],
            clicked_item_ids_A=[],
            clicked_item_ids_B=[],
        )

    @staticmethod
    def _normalize_str_list(value) -> List[str]:
        """입력 값을 문자열 리스트로 정규화"""
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(v) for v in value if v is not None]
        return [str(value)]
