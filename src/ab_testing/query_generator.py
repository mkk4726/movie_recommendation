"""
LLM 기반 쿼리 생성기

UserContext를 입력받아서 서비스별로 쿼리를 생성합니다.
"""

import json
import logging
import re
from pathlib import Path
from typing import Literal, Optional

import yaml

from llm import Qwen, LLMConfig

from .models import UserContext
from .prompts import QueryGenerationPrompt

logger = logging.getLogger(__name__)


class QueryResult:
    """쿼리 생성 결과"""

    def __init__(self, query: str, reasoning: str):
        self.query = query
        self.reasoning = reasoning

    def __repr__(self) -> str:
        return f"QueryResult(query='{self.query}', reasoning='{self.reasoning}')"


class QueryGenerator:
    """LLM 기반 쿼리 생성기"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        llm: Optional[Qwen] = None,
        prompt_template: Optional[QueryGenerationPrompt] = None,
    ):
        """
        Args:
            config_path: 설정 파일 경로
            llm: 사용할 Qwen 인스턴스 (None이면 새로 생성)
            prompt_template: 프롬프트 템플릿 (None이면 기본값 사용)
        """
        # 설정 로드
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self.llm_config = config["llm"]

        # 프롬프트 템플릿 초기화
        if prompt_template is None:
            self.prompt_template = QueryGenerationPrompt.create_default()
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

        logger.info("✅ Query Generator 초기화 완료")

    def generate_query(
        self,
        user_context: UserContext,
        service_type: Literal[
            "natural_language_search", "poster_search", "other"
        ] = "natural_language_search",
    ) -> QueryResult:
        """
        사용자 컨텍스트를 기반으로 서비스별 쿼리 생성

        Args:
            user_context: 사용자 컨텍스트 (선호도 등)
            service_type: 서비스 타입 (natural_language_search, poster_search, other)

        Returns:
            QueryResult 객체 (query, reasoning)
        """
        # 프롬프트 생성
        user_prompt = self.prompt_template.create_user_prompt(
            profile_text=user_context.to_prompt_text(),
            service_type=service_type,
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
            result = self._parse_response(response)

            logger.info(
                "✅ 쿼리 생성 완료: service=%s, query='%s'",
                service_type,
                result.query,
            )

            return result

        except Exception as e:
            logger.error(f"❌ 쿼리 생성 중 오류 발생: {e}")
            return self._create_fallback_query()

    def _parse_response(self, response: str) -> QueryResult:
        """LLM 응답을 파싱하여 QueryResult 생성"""
        try:
            # JSON 추출 시도
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
            else:
                data = json.loads(response)

            # 필수 필드 검증 및 기본값 설정
            query = data.get("query", "")
            if not query or not isinstance(query, str):
                query = ""

            reasoning = data.get("reasoning", "No reasoning provided")
            if not isinstance(reasoning, str):
                reasoning = str(reasoning) if reasoning else "No reasoning provided"

            return QueryResult(query=query, reasoning=reasoning)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"⚠️  응답 파싱 실패: {e}. Fallback 사용.")
            logger.debug(f"원본 응답: {response[:200]}...")
            return self._create_fallback_query()

    def _create_fallback_query(self) -> QueryResult:
        """파싱 실패 시 기본 쿼리 생성"""
        return QueryResult(
            query="",
            reasoning="Query generation failed - using fallback empty query",
        )


if __name__ == "__main__":
    """
    QueryGenerator 사용 예시
    """
    import logging

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 사용자 컨텍스트 생성
    user_context = UserContext(
        user_description=(
            "A sci-fi enthusiast who loves mind-bending plots, "
            "visual effects, and thought-provoking narratives. Age 25-35."
        )
    )

    # QueryGenerator 초기화
    print("=" * 60)
    print("🚀 QueryGenerator 사용 예시")
    print("=" * 60)

    generator = QueryGenerator()

    # Natural language search 쿼리 생성
    print("\n📝 Natural Language Search 쿼리 생성:")
    result = generator.generate_query(
        user_context=user_context,
        service_type="natural_language_search",
    )
    print(f"  Query: {result.query}")
    print(f"  Reasoning: {result.reasoning}")

    # Poster search 쿼리 생성
    print("\n🎨 Poster Search 쿼리 생성:")
    result = generator.generate_query(
        user_context=user_context,
        service_type="poster_search",
    )
    print(f"  Query: {result.query}")
    print(f"  Reasoning: {result.reasoning}")

    # 다른 사용자 컨텍스트 예시
    print("\n" + "=" * 60)
    print("다른 사용자 컨텍스트 예시:")
    print("=" * 60)

    thriller_context = UserContext(
        user_description=(
            "Loves thriller and dark-themed movies, enjoys intense suspense "
            "and mysterious atmospheres. Prefers movies with twists and "
            "psychological depth. Age 28-40."
        )
    )

    result = generator.generate_query(
        user_context=thriller_context,
        service_type="natural_language_search",
    )
    print(f"  Query: {result.query}")
    print(f"  Reasoning: {result.reasoning}")

    print("\n✅ 예시 실행 완료!")
