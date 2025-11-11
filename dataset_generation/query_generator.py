"""
Query Generator 모듈
영화 메타데이터를 기반으로 검색 쿼리를 자동 생성합니다.
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from dataset_generation.llm import LLM

# Logger 설정
logger = logging.getLogger(__name__)


@dataclass
class QueryGeneratorConfig:
    """Query Generator 설정"""

    system_prompt: str
    user_prompt_template: str
    queries_per_movie: int = 7
    max_new_tokens: int = 256
    temperature: float = 0.5
    top_p: float = 0.85
    do_sample: bool = True

    @classmethod
    def from_yaml(cls, yaml_path: Optional[str] = None) -> "QueryGeneratorConfig":
        """
        YAML 파일에서 설정을 로드하여 QueryGeneratorConfig 객체 생성

        Args:
            yaml_path: YAML 파일 경로 (None이면 기본 경로 사용)

        Returns:
            QueryGeneratorConfig 객체
        """
        # 기본 경로 설정
        if yaml_path is None:
            yaml_path = Path(__file__).parent / "config.yaml"
        else:
            yaml_path = Path(yaml_path)

        # YAML 파일 읽기
        logger.info(f"📄 설정 파일 로드: {yaml_path}")
        with open(yaml_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        # query_generation 섹션 추출
        if "query_generation" not in config_dict:
            raise ValueError("config.yaml 파일에 'query_generation' 섹션이 없습니다.")

        qg_config = config_dict["query_generation"]

        # QueryGeneratorConfig에 필요한 필드만 추출
        config = {
            "system_prompt": qg_config.get("system_prompt", ""),
            "user_prompt_template": qg_config.get("user_prompt_template", ""),
            "queries_per_movie": qg_config.get("queries_per_movie", 7),
            "max_new_tokens": qg_config.get("max_new_tokens", 256),
            "temperature": qg_config.get("temperature", 0.5),
            "top_p": qg_config.get("top_p", 0.85),
            "do_sample": qg_config.get("do_sample", True),
        }

        logger.info("✅ Query Generator 설정 로드 완료")
        return cls(**config)


class QueryGenerator:
    """영화 메타데이터 기반 쿼리 생성 클래스"""

    def __init__(
        self,
        llm: LLM,
        config: Optional[QueryGeneratorConfig] = None,
        yaml_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
    ):
        """
        QueryGenerator 초기화

        Args:
            llm: 생성된 LLM 인스턴스 (외부에서 주입)
            config: QueryGeneratorConfig 객체 (None이면 YAML에서 로드)
            yaml_path: YAML 파일 경로 (config가 None일 때 사용)
            system_prompt: 시스템 프롬프트 (None이면 config에서 사용)
            user_prompt_template: 유저 프롬프트 템플릿 (None이면 config에서 사용)
        """
        self.llm = llm

        # 설정 로드
        if config is None:
            self.config = QueryGeneratorConfig.from_yaml(yaml_path)
        else:
            self.config = config

        # system_prompt와 user_prompt_template 오버라이드
        if system_prompt is not None:
            self.config.system_prompt = system_prompt
            logger.info("📝 System prompt가 제공되어 config 값을 오버라이드합니다.")

        if user_prompt_template is not None:
            self.config.user_prompt_template = user_prompt_template
            logger.info(
                "📝 User prompt template가 제공되어 config 값을 오버라이드합니다."
            )

        logger.info("✅ QueryGenerator 초기화 완료")

    def generate_queries(
        self,
        movie_data: Dict[str, Any],
        num_queries: Optional[int] = None,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        do_sample: Optional[bool] = None,
    ) -> List[Dict[str, str]]:
        """
        영화 메타데이터를 기반으로 검색 쿼리 생성

        Args:
            movie_data: 영화 메타데이터 딕셔너리
                - title: 영화 제목
                - original_title: 원제
                - genres: 장르
                - overview: 줄거리
                - director: 감독
                - actors: 배우
                - release_year: 개봉년도
            num_queries: 생성할 쿼리 수 (None이면 config 값 사용)
            max_new_tokens: 최대 생성 토큰 수
            temperature: 샘플링 온도
            top_p: Top-p 샘플링 값
            do_sample: 샘플링 사용 여부

        Returns:
            생성된 쿼리 리스트 [{"query": "...", "query_type": "...", "language": "ko"}, ...]
        """
        # 파라미터 설정
        num_queries = (
            num_queries if num_queries is not None else self.config.queries_per_movie
        )
        max_new_tokens = (
            max_new_tokens if max_new_tokens is not None else self.config.max_new_tokens
        )
        temperature = (
            temperature if temperature is not None else self.config.temperature
        )
        top_p = top_p if top_p is not None else self.config.top_p
        do_sample = do_sample if do_sample is not None else self.config.do_sample

        # User Prompt 생성
        user_prompt = self._create_user_prompt(movie_data, num_queries)

        logger.info(f"🎬 영화 '{movie_data.get('title', 'Unknown')}' 쿼리 생성 중...")
        logger.debug(f"User Prompt:\n{user_prompt}")

        # LLM으로 쿼리 생성
        response = self.llm.generate(
            prompt=user_prompt,
            system_prompt=self.config.system_prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
        )

        logger.debug(f"LLM Response:\n{response}")

        # JSON 파싱
        queries = self._parse_response(response)

        logger.info(f"✅ {len(queries)}개 쿼리 생성 완료")

        return queries

    def _create_user_prompt(self, movie_data: Dict[str, Any], num_queries: int) -> str:
        """
        영화 데이터를 기반으로 User Prompt 생성

        Args:
            movie_data: 영화 메타데이터
            num_queries: 생성할 쿼리 수

        Returns:
            포맷팅된 User Prompt
        """
        # 기본값 설정
        prompt_data = {
            "num_queries": num_queries,
            "title": movie_data.get("title", "Unknown"),
            "original_title": movie_data.get("original_title", "Unknown"),
            "genres": movie_data.get("genres", "Unknown"),
            "overview": movie_data.get("overview", "No overview available"),
            "director": movie_data.get("director", "Unknown"),
            "actors": movie_data.get("actors", "Unknown"),
            "release_year": movie_data.get("release_year", "Unknown"),
        }

        return self.config.user_prompt_template.format(**prompt_data)

    def _parse_response(self, response: str) -> List[Dict[str, str]]:
        """
        LLM 응답을 파싱하여 쿼리 리스트 추출

        Args:
            response: LLM 응답 텍스트

        Returns:
            파싱된 쿼리 리스트
        """
        # JSON 코드 블록 제거 (```json ... ``` 형태)
        response = response.strip()
        if response.startswith("```"):
            # 첫 번째 줄 제거
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            # 마지막 ``` 제거
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)

        # JSON 파싱 시도
        try:
            queries = json.loads(response)

            # 리스트인지 확인
            if not isinstance(queries, list):
                logger.warning(f"응답이 리스트가 아닙니다: {type(queries)}")
                return []

            # 각 쿼리가 필수 필드를 가지고 있는지 확인
            valid_queries = []
            for query in queries:
                if isinstance(query, dict) and "query" in query:
                    # 기본값 설정
                    if "query_type" not in query:
                        query["query_type"] = "unknown"
                    if "language" not in query:
                        query["language"] = "ko"
                    valid_queries.append(query)
                else:
                    logger.warning(f"잘못된 쿼리 형식: {query}")

            return valid_queries

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            logger.error(f"응답 내용:\n{response}")
            return []

    def generate_queries_batch(
        self, movies_data: List[Dict[str, Any]], **kwargs
    ) -> List[Dict[str, Any]]:
        """
        여러 영화에 대해 배치로 쿼리 생성

        Args:
            movies_data: 영화 메타데이터 리스트
            **kwargs: generate_queries에 전달할 추가 파라미터

        Returns:
            각 영화에 대한 결과 리스트
            [
                {
                    "movie": {...},
                    "queries": [...],
                    "success": True/False,
                    "error": "..." (실패 시)
                },
                ...
            ]
        """
        results = []

        for i, movie_data in enumerate(movies_data, 1):
            logger.info(f"📊 진행: {i}/{len(movies_data)}")

            try:
                queries = self.generate_queries(movie_data, **kwargs)
                results.append(
                    {"movie": movie_data, "queries": queries, "success": True}
                )
            except Exception as e:
                logger.error(
                    f"❌ 영화 '{movie_data.get('title', 'Unknown')}' 쿼리 생성 실패: {e}"
                )
                results.append(
                    {
                        "movie": movie_data,
                        "queries": [],
                        "success": False,
                        "error": str(e),
                    }
                )

        # 통계 출력
        success_count = sum(1 for r in results if r["success"])
        total_queries = sum(len(r["queries"]) for r in results)

        logger.info(f"\n{'='*60}")
        logger.info(f"📊 배치 생성 완료")
        logger.info(f"  - 성공: {success_count}/{len(movies_data)}")
        logger.info(f"  - 총 쿼리 수: {total_queries}")
        logger.info(f"{'='*60}\n")

        return results


# 사용 예시
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # LLM 초기화 (외부에서 생성)
    llm = LLM()

    # QueryGenerator 초기화 (LLM 인스턴스 주입)
    query_generator = QueryGenerator(llm=llm)

    # 테스트 영화 데이터
    movie_data = {
        "title": "기생충",
        "original_title": "Parasite",
        "genres": "드라마, 스릴러, 코미디",
        "overview": "전원 백수인 기택 가족이 부유한 박 사장 가족에게 취업하면서 벌어지는 이야기",
        "director": "봉준호",
        "actors": "송강호, 이선균, 조여정, 최우식, 박소담",
        "release_year": "2019",
    }

    # 쿼리 생성
    queries = query_generator.generate_queries(movie_data)

    # 결과 출력
    print("\n" + "=" * 60)
    print(f"🎬 영화: {movie_data['title']}")
    print("=" * 60)
    for i, query in enumerate(queries, 1):
        print(f"{i}. [{query['query_type']}] {query['query']}")
    print("=" * 60)
