"""
LLM 기반 추천 결과 평가기
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

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
                f"✅ 평가 완료: "
                f"선호={evaluation.preferred_list}, "
                f"CTR_A={evaluation.click_probability_A:.3f}, "
                f"CTR_B={evaluation.click_probability_B:.3f}"
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

            # 확률 값 검증 (0~1 범위)
            click_prob_a = float(data.get("click_probability_A", 0.5))
            click_prob_a = max(0.0, min(1.0, click_prob_a))

            click_prob_b = float(data.get("click_probability_B", 0.5))
            click_prob_b = max(0.0, min(1.0, click_prob_b))

            # 관련성 점수 (0~10 범위)
            relevance_a = data.get("relevance_score_A")
            if relevance_a is not None:
                relevance_a = float(relevance_a)
                relevance_a = max(0.0, min(10.0, relevance_a))

            relevance_b = data.get("relevance_score_B")
            if relevance_b is not None:
                relevance_b = float(relevance_b)
                relevance_b = max(0.0, min(10.0, relevance_b))

            # EvaluationResult 생성
            evaluation = EvaluationResult(
                preferred_list=preferred_list,
                reasoning=reasoning,
                click_probability_A=click_prob_a,
                click_probability_B=click_prob_b,
                relevance_score_A=relevance_a,
                relevance_score_B=relevance_b,
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
            click_probability_A=0.5,
            click_probability_B=0.5,
            relevance_score_A=5.0,
            relevance_score_B=5.0,
        )
