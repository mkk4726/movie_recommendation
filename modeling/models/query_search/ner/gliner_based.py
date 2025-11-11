"""
GLiNER 기반 Named Entity Recognition (NER) - 사람 이름 추출
영화 추천 쿼리에서 배우, 감독 등 사람 이름을 추출합니다.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# Hugging Face 진행 표시줄 비활성화
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

try:
    from gliner import GLiNER
    GLINER_AVAILABLE = True
except ImportError:
    GLINER_AVAILABLE = False
    GLiNER = None

# Logger 설정
logger = logging.getLogger(__name__)


@dataclass
class PersonExtractionResult:
    """사람 이름 추출 결과"""
    persons: List[str] = field(default_factory=list)
    raw_entities: List[Dict[str, Any]] = field(default_factory=list)
    
    def __str__(self) -> str:
        """사람이 읽기 쉬운 형식으로 출력"""
        if self.persons:
            return f"추출된 인물: {', '.join(self.persons)}"
        return "추출된 인물 없음"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "persons": self.persons,
            "count": len(self.persons)
        }


class GLiNERPersonExtractor:
    """GLiNER 기반 사람 이름 추출기"""
    
    def __init__(self, model_name: str = "taeminlee/gliner_ko"):
        """
        GLiNERPersonExtractor 초기화
        
        Args:
            model_name: 사용할 GLiNER 모델 이름 (기본: taeminlee/gliner_ko)
        
        Raises:
            ImportError: gliner 패키지가 설치되지 않은 경우
        """
        if not GLINER_AVAILABLE:
            raise ImportError(
                "gliner 패키지가 설치되지 않았습니다. "
                "다음 명령으로 설치하세요: pip install gliner"
            )
        
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self):
        """GLiNER 모델 로드"""
        logger.info(f"🔄 GLiNER 모델 로드 중: {self.model_name}")
        
        try:
            self.model = GLiNER.from_pretrained(self.model_name)
            logger.info("✅ GLiNER 모델 로드 완료")
        except Exception as e:
            logger.error(f"❌ GLiNER 모델 로드 실패: {e}")
            raise
    
    def extract_persons(
        self, 
        text: str, 
        threshold: float = 0.3,
        verbose: bool = False
    ) -> PersonExtractionResult:
        """
        텍스트에서 사람 이름 추출
        
        Args:
            text: 사용자 쿼리 텍스트
            threshold: 신뢰도 임계값 (0.0 ~ 1.0)
            verbose: 상세 출력 여부
            
        Returns:
            PersonExtractionResult 객체 (추출된 사람 이름)
        """
        if verbose:
            logger.info(f"🔍 쿼리 분석 중: '{text}'")
        
        # PERSON 레이블로 엔티티 추출
        labels = ["PERSON"]
        
        try:
            entities = self.model.predict_entities(
                text, 
                labels,
                threshold=threshold
            )
            
            if verbose:
                print(f"\n🎯 추출된 엔티티 ({len(entities)}개):")
                for entity in entities:
                    score = entity.get('score', 0.0)
                    print(f"  - {entity['text']} (신뢰도: {score:.3f})")
            
            # 사람 이름만 추출 (중복 제거)
            persons = []
            seen = set()
            
            for entity in entities:
                if entity.get('label') == 'PERSON':
                    text_clean = entity['text'].strip()
                    if text_clean and text_clean not in seen:
                        persons.append(text_clean)
                        seen.add(text_clean)
            
            result = PersonExtractionResult(
                persons=persons,
                raw_entities=entities
            )
            
            if verbose:
                print(f"\n📋 결과: {result}")
                print("✅ 완료!")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 엔티티 추출 실패: {e}", exc_info=True)
            if verbose:
                print(f"\n❌ 엔티티 추출 실패: {e}")
            return PersonExtractionResult()
    
    def __call__(self, text: str, threshold: float = 0.3, verbose: bool = False) -> List[str]:
        """
        편의 메서드: 텍스트에서 사람 이름만 리스트로 반환
        
        Args:
            text: 사용자 쿼리 텍스트
            threshold: 신뢰도 임계값
            verbose: 상세 출력 여부
            
        Returns:
            추출된 사람 이름 리스트
        """
        result = self.extract_persons(text, threshold, verbose)
        return result.persons


# 사용 예시
if __name__ == "__main__":
    # GLiNER가 설치되어 있는지 확인
    if not GLINER_AVAILABLE:
        print("❌ gliner 패키지가 설치되지 않았습니다.")
        print("설치 명령: pip install gliner")
        exit(1)
    
    print("=" * 60)
    print("GLiNER 기반 사람 이름 추출기 테스트")
    print("=" * 60)
    
    try:
        # 추출기 초기화
        extractor = GLiNERPersonExtractor()
        
        # 테스트 쿼리들
        test_queries = [
            "이병헌이 출연한 영화 추천해줘",
            "김민규가 나오는 진지한 분위기의 로맨스 영화 추천해줘",
            "크리스토퍼 놀란 감독의 액션 영화",
            "박찬욱 감독과 송강호가 출연한 영화",
            "일본 애니메이션 영화 추천해줘"  # 사람 이름 없음
        ]
        
        for query in test_queries:
            print(f"\n{'=' * 60}")
            print(f"쿼리: {query}")
            print('=' * 60)
            
            # 방법 1: extract_persons 메서드 사용
            result = extractor.extract_persons(query, threshold=0.3, verbose=True)
            
            # 방법 2: __call__ 메서드 사용 (간단)
            # persons = extractor(query, threshold=0.3, verbose=True)
            # print(f"추출된 인물: {persons}")
        
        print(f"\n{'=' * 60}")
        print("테스트 완료!")
        print('=' * 60)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
