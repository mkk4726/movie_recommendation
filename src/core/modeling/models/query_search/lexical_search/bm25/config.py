"""
BM25 설정 모듈

BM25 알고리즘 및 검색 관련 설정을 관리합니다.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class BM25Config:
    """BM25 검색 설정"""

    k1: float = 1.5  # 용어 빈도 포화 파라미터 (1.2~2.0 권장)
    b: float = 0.75  # 문서 길이 정규화 파라미터 (0~1)
    epsilon: float = 0.25  # IDF 하한값 (음수 IDF 방지)

    # 검색 설정
    top_k: int = 20  # 반환할 상위 결과 개수
    min_score: float = 0.0  # 최소 스코어 임계값

    # 토크나이저 설정
    use_korean: bool = True  # 한글 토크나이징 지원
    min_token_length: int = 1  # 최소 토큰 길이
    max_token_length: int = 50  # 최대 토큰 길이

    # 필드 가중치 (영화 검색에 최적화)
    field_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "title": 3.0,  # 제목에 가장 높은 가중치
            "genres": 2.0,  # 장르에 중간 가중치
            "tags": 1.0,  # 태그에 기본 가중치
            "overview": 1.5,  # 줄거리/개요에 중간 가중치
        }
    )

    # 캐시 설정
    cache_dir: Optional[str] = None  # 색인 캐시 디렉토리
    use_cache: bool = True  # 캐시 사용 여부

    @classmethod
    def from_yaml(cls, yaml_path: Optional[str] = None) -> "BM25Config":
        """
        YAML 파일에서 설정을 로드하여 BM25Config 객체 생성

        Args:
            yaml_path: YAML 파일 경로 (None이면 기본 경로 사용)

        Returns:
            BM25Config 객체
        """
        # 기본 경로 설정
        if yaml_path is None:
            yaml_path = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "config" / "modeling.yaml"
        else:
            yaml_path = Path(yaml_path)

        # YAML 파일 읽기
        logger.info(f"📄 설정 파일 로드: {yaml_path}")
        with open(yaml_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        # bm25 섹션 추출 (없으면 기본값 사용)
        if "bm25" in config_dict:
            bm25_config = config_dict["bm25"]
            logger.info("✅ BM25 설정 로드 완료")
            return cls(**bm25_config)
        else:
            logger.warning("⚠️ config.yaml에 'bm25' 섹션이 없습니다. 기본값을 사용합니다.")
            return cls()
