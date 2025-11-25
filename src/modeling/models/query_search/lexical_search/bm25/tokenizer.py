"""
BM25 토크나이저 모듈

텍스트를 토큰으로 분리하는 기능을 제공합니다.
"""
import re
from typing import List


class BM25Tokenizer:
    """BM25용 토크나이저 (한글 및 영어 지원)"""
    
    def __init__(self, min_length: int = 1, max_length: int = 50, use_korean: bool = True):
        """
        토크나이저 초기화
        
        Args:
            min_length: 최소 토큰 길이
            max_length: 최대 토큰 길이
            use_korean: 한글 토크나이징 지원
        """
        self.min_length = min_length
        self.max_length = max_length
        self.use_korean = use_korean
    
    def tokenize(self, text: str) -> List[str]:
        """
        텍스트를 토큰으로 분리
        
        Args:
            text: 입력 텍스트
            
        Returns:
            토큰 리스트
        """
        if not text or not isinstance(text, str):
            return []
        
        # 소문자 변환
        text = text.lower()
        
        # 특수 문자 제거 (한글, 영문, 숫자, 공백만 유지)
        if self.use_korean:
            text = re.sub(r'[^가-힣a-z0-9\s]', ' ', text)
        else:
            text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # 공백으로 분리
        tokens = text.split()
        
        # 길이 필터링
        tokens = [
            token for token in tokens 
            if self.min_length <= len(token) <= self.max_length
        ]
        
        return tokens

