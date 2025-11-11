"""
NER (Named Entity Recognition) Module

영화 추천 쿼리에서 엔티티(배우, 장르, 감독 등)를 추출합니다.
"""

from .qwen_based import QwenBasedNER, NERConfig, NERResult
from .gliner_based import GLiNERPersonExtractor, PersonExtractionResult

__all__ = [
    # Qwen-based NER (전체 엔티티 추출)
    'QwenBasedNER',
    'NERConfig',
    'NERResult',
    
    # GLiNER-based Person Extractor (사람 이름만 추출)
    'GLiNERPersonExtractor',
    'PersonExtractionResult',
]

