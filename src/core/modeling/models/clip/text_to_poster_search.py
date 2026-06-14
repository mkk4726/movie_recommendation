"""
Text-to-Poster Search Pipeline

텍스트 쿼리로 영화 포스터를 검색하는 파이프라인.
CLIP 모델과 Qdrant 벡터 데이터베이스를 사용합니다.
한국어 쿼리는 자동으로 영어로 번역됩니다.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models.base import BaseClipEncoder

logger = logging.getLogger(__name__)


class TextToPosterSearchPipeline:
    """텍스트로 포스터를 검색하는 파이프라인 (한국어 자동 번역 지원)"""

    def __init__(
        self,
        model_key: str = "siglip-multilingual",
        vector_store_config_path: Optional[str] = None,
        enable_translation: bool = False,
    ):
        """
        Args:
            model_key: CLIP 모델 키 (siglip-multilingual, jina-clip, openai-b32 등)
            vector_store_config_path: Vector store 설정 파일 경로 (None이면 기본 경로)
            enable_translation: 한국어 자동 번역 활성화 여부
        """
        self.model_key = model_key
        self.encoder: Optional[BaseClipEncoder] = None
        self.qdrant_manager = None
        self.vector_store_config_path = vector_store_config_path
        self.enable_translation = enable_translation

        self.language_detector = None
        self.translator = None

        logger.info(f"TextToPosterSearchPipeline 초기화 (모델: {model_key}, 번역: {enable_translation})")

    def _load_encoder(self):
        """CLIP 인코더 로드 (지연 로딩)"""
        if self.encoder is None:
            logger.info(f"🔄 CLIP 인코더 로딩 중... (모델: {self.model_key})")
            self.encoder = BaseClipEncoder(model_key=self.model_key)
            logger.info(f"✅ CLIP 인코더 로드 완료 (디바이스: {self.encoder.device})")

    def _load_qdrant_manager(self):
        """Qdrant 매니저 로드 (지연 로딩)"""
        if self.qdrant_manager is not None:
            return

        logger.info("🔄 Qdrant 매니저 로딩 중...")

        from core.vector_store.qdrant_manager import QdrantManager
        from core.vector_store.utils.config import load_config

        config = None
        if self.vector_store_config_path:
            config_path = Path(self.vector_store_config_path)
            if config_path.exists():
                config = load_config(str(config_path))

        self.qdrant_manager = QdrantManager(config=config)
        self.qdrant_manager.load()

        logger.info(f"✅ Qdrant 매니저 로드 완료: {self.qdrant_manager.total_vectors:,}개 벡터")

    def _load_language_modules(self):
        """언어 감지 및 번역 모듈 로드 (지연 로딩)"""
        if not self.enable_translation:
            return

        if self.language_detector is None or self.translator is None:
            logger.info("🔄 언어 감지 및 번역 모듈 로딩 중...")

            try:
                from modeling.models.language import KoreanEnglishTranslator, LanguageDetector

                self.language_detector = LanguageDetector()
                self.translator = KoreanEnglishTranslator()

                logger.info("✅ 언어 감지 및 번역 모듈 로드 완료")
            except Exception as e:
                logger.warning(f"⚠️ 언어 모듈 로드 실패 (번역 비활성화): {e}")
                self.enable_translation = False

    def _translate_if_korean(self, query: str) -> tuple[str, bool]:
        """
        쿼리가 한국어인 경우 영어로 번역

        Returns:
            (처리된 쿼리, 번역 여부)
        """
        if not self.enable_translation:
            return query, False

        self._load_language_modules()

        if self.language_detector is None or self.translator is None:
            return query, False

        try:
            detected_lang = self.language_detector.detect_language(query)

            if detected_lang == "ko":
                logger.info(f"🌐 한국어 쿼리 감지: '{query}'")
                translated = self.translator.translate(query)
                logger.info(f"🌐 영어로 번역: '{translated}'")
                return translated, True

            return query, False

        except Exception as e:
            logger.warning(f"⚠️ 언어 감지/번역 실패 (원본 쿼리 사용): {e}")
            return query, False

    def _ensure_loaded(self):
        """필요한 리소스가 모두 로드되었는지 확인"""
        self._load_encoder()
        self._load_qdrant_manager()

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_movie_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        텍스트 쿼리로 포스터 검색 (한국어 자동 번역 지원)

        Args:
            query: 검색 텍스트 (한국어 또는 영어)
            top_k: 반환할 결과 수
            filter_movie_ids: 검색 대상 영화 ID 리스트 (None이면 전체 검색)

        Returns:
            [{"movie_id": str, "score": float}, ...]
        """
        self._ensure_loaded()

        logger.info(
            f"🔍 텍스트-포스터 검색: '{query}' "
            f"(top_k={top_k}, filter_ids={len(filter_movie_ids) if filter_movie_ids else 'None'})"
        )

        processed_query, was_translated = self._translate_if_korean(query)

        embedding = self.encoder.encode_text(processed_query)
        query_vector = embedding.cpu().numpy().flatten()

        results = self.qdrant_manager.search(query_vector, k=top_k, filter_movie_ids=filter_movie_ids)

        logger.info(f"✅ 검색 완료: {len(results)}개 결과 (번역: {was_translated})")
        return results

    def batch_search(
        self,
        queries: List[str],
        top_k: int = 10,
    ) -> List[List[Dict[str, Any]]]:
        """여러 쿼리 배치 검색"""
        return [self.search(q, top_k=top_k) for q in queries]

    def __repr__(self) -> str:
        loaded = "loaded" if self.encoder and self.qdrant_manager else "not loaded"
        return f"TextToPosterSearchPipeline(model={self.model_key}, status={loaded})"


def create_text_to_poster_pipeline(
    model_key: str = "siglip-multilingual",
    vector_store_config_path: Optional[str] = None,
    enable_translation: bool = False,
) -> TextToPosterSearchPipeline:
    """텍스트-포스터 검색 파이프라인 생성 헬퍼"""
    return TextToPosterSearchPipeline(
        model_key=model_key,
        vector_store_config_path=vector_store_config_path,
        enable_translation=enable_translation,
    )
