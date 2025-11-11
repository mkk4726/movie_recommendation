"""
BM25 핵심 알고리즘 모듈

BM25 (Best Matching 25) 검색 알고리즘의 핵심 구현
"""
import math
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Any
from collections import Counter

from .config import BM25Config
from .tokenizer import BM25Tokenizer
from .models import BM25SearchResult

logger = logging.getLogger(__name__)


class BM25:
    """
    BM25 (Best Matching 25) 검색 알고리즘
    
    BM25는 정보 검색에서 가장 널리 사용되는 랭킹 함수 중 하나입니다.
    TF-IDF의 확률론적 개선 버전으로, 문서의 길이와 용어 빈도를 고려합니다.
    
    주요 특징:
    - 용어 빈도 포화: 같은 단어가 여러 번 나와도 스코어가 무한정 증가하지 않음
    - 문서 길이 정규화: 긴 문서가 유리하지 않도록 조정
    - IDF (Inverse Document Frequency): 희귀한 단어에 더 높은 가중치
    """
    
    def __init__(self, config: Optional[BM25Config] = None, yaml_path: Optional[str] = None):
        """
        BM25 초기화
        
        Args:
            config: BM25Config 객체 (None이면 YAML에서 로드)
            yaml_path: YAML 파일 경로 (config가 None일 때 사용)
        """
        # 설정 로드
        if config is None:
            self.config = BM25Config.from_yaml(yaml_path)
        else:
            self.config = config
        
        # 토크나이저 초기화
        self.tokenizer = BM25Tokenizer(
            min_length=self.config.min_token_length,
            max_length=self.config.max_token_length,
            use_korean=self.config.use_korean
        )
        
        # 색인 데이터 초기화
        self.corpus_size = 0  # 전체 문서 수
        self.avgdl = 0.0  # 평균 문서 길이
        self.doc_freqs = []  # 각 문서의 용어 빈도
        self.idf = {}  # IDF 값
        self.doc_len = []  # 각 문서의 길이
        self.doc_ids = []  # 문서 ID 리스트
        self.doc_metadata = []  # 문서 메타데이터 (제목, 장르 등)
        
        logger.info("✅ BM25 초기화 완료")
    
    def _calc_idf(self, nd: Dict[str, int]) -> Dict[str, float]:
        """
        IDF (Inverse Document Frequency) 계산
        
        IDF = log((N - n(qi) + 0.5) / (n(qi) + 0.5) + 1)
        여기서 N은 전체 문서 수, n(qi)는 용어 qi를 포함하는 문서 수
        
        Args:
            nd: 각 용어가 등장하는 문서 수 딕셔너리
            
        Returns:
            용어별 IDF 값 딕셔너리
        """
        idf_sum = 0.0
        idf = {}
        
        for word, freq in nd.items():
            # BM25 IDF 공식
            idf_score = math.log(
                (self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0
            )
            # epsilon보다 작으면 epsilon으로 설정 (음수 방지)
            idf[word] = max(self.config.epsilon, idf_score)
            idf_sum += idf[word]
        
        # 평균 IDF 계산 (로깅용)
        avg_idf = idf_sum / len(idf) if idf else 0.0
        logger.info(f"📊 IDF 계산 완료: {len(idf)}개 용어, 평균 IDF: {avg_idf:.4f}")
        
        return idf
    
    def fit(self, corpus: List[str], doc_ids: List[Any], metadata: Optional[List[Dict]] = None):
        """
        문서 집합에 대해 BM25 색인 생성
        
        Args:
            corpus: 문서 텍스트 리스트
            doc_ids: 문서 ID 리스트
            metadata: 문서 메타데이터 리스트 (제목, 장르 등)
        """
        logger.info(f"🔄 BM25 색인 생성 중... ({len(corpus)}개 문서)")
        
        self.corpus_size = len(corpus)
        self.doc_ids = doc_ids
        self.doc_metadata = metadata if metadata else [{} for _ in range(len(corpus))]
        
        # 각 문서를 토크나이징하고 용어 빈도 계산
        nd = {}  # 각 용어가 등장하는 문서 수
        self.doc_freqs = []
        self.doc_len = []
        
        for doc in corpus:
            tokens = self.tokenizer.tokenize(doc)
            self.doc_len.append(len(tokens))
            
            # 용어 빈도 계산
            frequencies = Counter(tokens)
            self.doc_freqs.append(frequencies)
            
            # 문서 빈도 업데이트
            for word in frequencies.keys():
                nd[word] = nd.get(word, 0) + 1
        
        # 평균 문서 길이 계산
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0.0
        
        # IDF 계산
        self.idf = self._calc_idf(nd)
        
        logger.info(f"✅ BM25 색인 생성 완료: {self.corpus_size}개 문서, 평균 길이: {self.avgdl:.2f}")
    
    def _score_document(self, query_tokens: List[str], doc_idx: int) -> float:
        """
        단일 문서에 대한 BM25 스코어 계산
        
        BM25 공식:
        score(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1 + 1)) / (f(qi,D) + k1 * (1 - b + b * |D| / avgdl))
        
        Args:
            query_tokens: 쿼리 토큰 리스트
            doc_idx: 문서 인덱스
            
        Returns:
            BM25 스코어
        """
        score = 0.0
        doc_freqs = self.doc_freqs[doc_idx]
        doc_len = self.doc_len[doc_idx]
        
        for token in query_tokens:
            if token not in doc_freqs:
                continue
            
            # 용어 빈도
            freq = doc_freqs[token]
            
            # IDF 값
            idf = self.idf.get(token, 0.0)
            
            # BM25 스코어 계산
            numerator = idf * freq * (self.config.k1 + 1)
            denominator = freq + self.config.k1 * (
                1 - self.config.b + self.config.b * doc_len / self.avgdl
            )
            
            score += numerator / denominator
        
        return score
    
    def search(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        min_score: Optional[float] = None
    ) -> List[BM25SearchResult]:
        """
        쿼리에 대한 BM25 검색 수행
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 개수 (None이면 config 값 사용)
            min_score: 최소 스코어 임계값 (None이면 config 값 사용)
            
        Returns:
            BM25SearchResult 리스트 (스코어 내림차순 정렬)
        """
        if self.corpus_size == 0:
            logger.warning("⚠️ 색인이 비어있습니다. fit()을 먼저 호출하세요.")
            return []
        
        # 파라미터 기본값 설정
        top_k = top_k if top_k is not None else self.config.top_k
        min_score = min_score if min_score is not None else self.config.min_score
        
        # 쿼리 토크나이징
        query_tokens = self.tokenizer.tokenize(query)
        
        if not query_tokens:
            logger.warning(f"⚠️ 쿼리 토큰이 비어있습니다: '{query}'")
            return []
        
        logger.info(f"🔍 검색 중: '{query}' -> 토큰: {query_tokens}")
        
        # 각 문서에 대해 스코어 계산
        scores = []
        for idx in range(self.corpus_size):
            score = self._score_document(query_tokens, idx)
            
            if score >= min_score:
                scores.append((idx, score))
        
        # 스코어 내림차순 정렬
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 K개 결과 반환
        results = []
        for idx, score in scores[:top_k]:
            metadata = self.doc_metadata[idx]
            result = BM25SearchResult(
                movie_id=self.doc_ids[idx],
                score=score,
                title=metadata.get('title', 'Unknown'),
                genres=metadata.get('genres', 'Unknown'),
                matched_fields={'combined': score},
                overview=metadata.get('overview', '')
            )
            results.append(result)
        
        logger.info(f"✅ 검색 완료: {len(results)}개 결과 반환")
        return results
    
    def save(self, filepath: str):
        """
        BM25 색인을 파일로 저장
        
        Args:
            filepath: 저장할 파일 경로
        """
        data = {
            'config': self.config,
            'corpus_size': self.corpus_size,
            'avgdl': self.avgdl,
            'doc_freqs': self.doc_freqs,
            'idf': self.idf,
            'doc_len': self.doc_len,
            'doc_ids': self.doc_ids,
            'doc_metadata': self.doc_metadata
        }
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"💾 BM25 색인 저장 완료: {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'BM25':
        """
        파일에서 BM25 색인 로드
        
        Args:
            filepath: 로드할 파일 경로
            
        Returns:
            BM25 객체
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        # BM25 객체 생성
        bm25 = cls(config=data['config'])
        
        # 색인 데이터 복원
        bm25.corpus_size = data['corpus_size']
        bm25.avgdl = data['avgdl']
        bm25.doc_freqs = data['doc_freqs']
        bm25.idf = data['idf']
        bm25.doc_len = data['doc_len']
        bm25.doc_ids = data['doc_ids']
        bm25.doc_metadata = data['doc_metadata']
        
        logger.info(f"📂 BM25 색인 로드 완료: {filepath} ({bm25.corpus_size}개 문서)")
        return bm25

