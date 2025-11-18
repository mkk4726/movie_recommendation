"""
Text-to-Poster Search Pipeline

텍스트 쿼리로 영화 포스터를 검색하는 파이프라인
CLIP 모델과 FAISS 벡터 인덱스를 사용합니다.
한국어 쿼리는 자동으로 영어로 번역됩니다.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

import numpy as np

from .models.base import BaseClipEncoder

logger = logging.getLogger(__name__)


class TextToPosterSearchPipeline:
    """텍스트로 포스터를 검색하는 파이프라인 (한국어 자동 번역 지원)"""
    
    def __init__(
        self,
        model_key: str = "jina-clip",
        vector_store_config_path: Optional[str] = None,
        enable_translation: bool = True,
    ):
        """
        Args:
            model_key: CLIP 모델 키 (jina-clip, openai-b32 등)
            vector_store_config_path: Vector store 설정 파일 경로 (None이면 기본 경로)
            enable_translation: 한국어 자동 번역 활성화 여부
        """
        self.model_key = model_key
        self.encoder = None
        self.faiss_manager = None
        self.movie_ids = None
        self.vector_store_config_path = vector_store_config_path
        self.enable_translation = enable_translation
        
        # 언어 감지 및 번역 모듈 (지연 로딩)
        self.language_detector = None
        self.translator = None
        
        logger.info(f"TextToPosterSearchPipeline 초기화 (모델: {model_key}, 번역: {enable_translation})")
    
    def _load_encoder(self):
        """CLIP 인코더 로드 (지연 로딩)"""
        if self.encoder is None:
            logger.info(f"🔄 CLIP 인코더 로딩 중... (모델: {self.model_key})")
            self.encoder = BaseClipEncoder(model_key=self.model_key)
            logger.info(f"✅ CLIP 인코더 로드 완료 (디바이스: {self.encoder.device})")
    
    def _load_faiss_manager(self):
        """FAISS 매니저 로드 (지연 로딩)"""
        if self.faiss_manager is None:
            logger.info("🔄 FAISS 매니저 로딩 중...")
            
            # vector_store 모듈 import
            import sys
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            vector_store_path = project_root / "vector_store"
            
            if str(vector_store_path) not in sys.path:
                sys.path.insert(0, str(vector_store_path))
            
            from vector_store import FAISSManager, load_config
            
            # 설정 로드
            if self.vector_store_config_path:
                config_path = Path(self.vector_store_config_path)
            else:
                config_path = vector_store_path / "config.yaml"
            
            if not config_path.exists():
                raise FileNotFoundError(f"Vector store 설정 파일을 찾을 수 없습니다: {config_path}")
            
            config = load_config(str(config_path))
            
            # FAISS 매니저 생성 및 인덱스 로드
            self.faiss_manager = FAISSManager(config=config)
            self.faiss_manager.load()
            
            logger.info(f"✅ FAISS 매니저 로드 완료: {self.faiss_manager.total_vectors:,}개 벡터")
    
    def _load_movie_ids(self):
        """movie_ids 매핑 로드 (지연 로딩)"""
        if self.movie_ids is None:
            logger.info("🔄 movie_ids 매핑 로딩 중...")
            
            # movie_ids.json 경로
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            movie_ids_path = project_root / "vector_store" / "indices" / "movie_ids.json"
            
            if not movie_ids_path.exists():
                raise FileNotFoundError(f"movie_ids.json 파일을 찾을 수 없습니다: {movie_ids_path}")
            
            with open(movie_ids_path, "r") as f:
                self.movie_ids = json.load(f)
            
            logger.info(f"✅ movie_ids 매핑 로드 완료: {len(self.movie_ids):,}개")
    
    def _load_language_modules(self):
        """언어 감지 및 번역 모듈 로드 (지연 로딩)"""
        if not self.enable_translation:
            return
        
        if self.language_detector is None or self.translator is None:
            logger.info("🔄 언어 감지 및 번역 모듈 로딩 중...")
            
            try:
                # language 모듈 import
                import sys
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                modeling_path = project_root / "modeling"
                
                if str(modeling_path) not in sys.path:
                    sys.path.insert(0, str(modeling_path))
                
                from models.language import LanguageDetector, KoreanEnglishTranslator
                
                self.language_detector = LanguageDetector()
                self.translator = KoreanEnglishTranslator()
                
                logger.info("✅ 언어 감지 및 번역 모듈 로드 완료")
            except Exception as e:
                logger.warning(f"⚠️ 언어 모듈 로드 실패 (번역 비활성화): {e}")
                self.enable_translation = False
    
    def _translate_if_korean(self, query: str) -> tuple[str, bool]:
        """
        쿼리가 한국어인 경우 영어로 번역
        
        Args:
            query: 입력 쿼리
        
        Returns:
            (처리된 쿼리, 번역 여부)
        """
        if not self.enable_translation:
            return query, False
        
        # 언어 모듈 로드
        self._load_language_modules()
        
        if self.language_detector is None or self.translator is None:
            return query, False
        
        try:
            # 언어 감지
            detected_lang = self.language_detector.detect_language(query)
            
            if detected_lang == "ko":
                logger.info(f"🌐 한국어 쿼리 감지: '{query}'")
                translated_query = self.translator.translate(query)
                logger.info(f"🌐 영어로 번역: '{translated_query}'")
                return translated_query, True
            else:
                logger.debug(f"언어 감지: {detected_lang} (번역 불필요)")
                return query, False
                
        except Exception as e:
            logger.warning(f"⚠️ 언어 감지/번역 실패 (원본 쿼리 사용): {e}")
            return query, False
    
    def _ensure_loaded(self):
        """필요한 리소스가 모두 로드되었는지 확인"""
        self._load_encoder()
        self._load_faiss_manager()
        self._load_movie_ids()
    
    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        텍스트 쿼리로 포스터 검색 (한국어 자동 번역 지원)
        
        Args:
            query: 검색 텍스트 쿼리 (한국어 또는 영어)
            top_k: 반환할 결과 수
        
        Returns:
            검색 결과 리스트 [{"movie_id": str, "score": float, "index": int}, ...]
        """
        # 리소스 로드 확인
        self._ensure_loaded()
        
        logger.info(f"🔍 텍스트-포스터 검색: '{query}' (top_k={top_k})")
        
        # 1. 한국어 쿼리 번역 (필요시)
        processed_query, was_translated = self._translate_if_korean(query)
        
        # 2. 텍스트 인코딩
        embedding = self.encoder.encode_text(processed_query)
        query_vector = embedding.cpu().numpy().flatten()
        
        # 3. FAISS 검색
        results = self.faiss_manager.search(query_vector, k=top_k)
        
        # 4. FAISS 인덱스 -> movie_id 변환
        enriched_results = []
        for result in results:
            faiss_idx = result["index"]
            if faiss_idx < len(self.movie_ids):
                movie_id = self.movie_ids[faiss_idx]
                enriched_result = {
                    "movie_id": str(movie_id),
                    "score": float(result["score"]),
                    "index": int(faiss_idx),
                }
                enriched_results.append(enriched_result)
            else:
                logger.warning(f"FAISS 인덱스 {faiss_idx}가 movie_ids 범위를 벗어났습니다.")
        
        logger.info(f"✅ 텍스트-포스터 검색 완료: {len(enriched_results)}개 결과 (번역: {was_translated})")
        return enriched_results
    
    def batch_search(
        self,
        queries: List[str],
        top_k: int = 10,
    ) -> List[List[Dict[str, Any]]]:
        """
        여러 텍스트 쿼리로 배치 검색
        
        Args:
            queries: 검색 텍스트 쿼리 리스트
            top_k: 각 쿼리당 반환할 결과 수
        
        Returns:
            각 쿼리의 검색 결과 리스트
        """
        results = []
        for query in queries:
            query_results = self.search(query, top_k=top_k)
            results.append(query_results)
        return results
    
    def __repr__(self) -> str:
        loaded_status = "loaded" if self.encoder and self.faiss_manager else "not loaded"
        return f"TextToPosterSearchPipeline(model={self.model_key}, status={loaded_status})"


def create_text_to_poster_pipeline(
    model_key: str = "jina-clip",
    vector_store_config_path: Optional[str] = None,
    enable_translation: bool = True,
) -> TextToPosterSearchPipeline:
    """
    텍스트-포스터 검색 파이프라인 생성 헬퍼 함수
    
    Args:
        model_key: CLIP 모델 키
        vector_store_config_path: Vector store 설정 파일 경로
        enable_translation: 한국어 자동 번역 활성화 여부
    
    Returns:
        TextToPosterSearchPipeline 인스턴스
    """
    return TextToPosterSearchPipeline(
        model_key=model_key,
        vector_store_config_path=vector_store_config_path,
        enable_translation=enable_translation,
    )

