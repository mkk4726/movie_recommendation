# ADR 004: 검색 시스템 - BM25 + NER

## 상태
📝 Draft

## 날짜
[작성 날짜]

## 컨텍스트
사용자가 자연어로 영화를 검색할 수 있는 시스템이 필요했다. 단순 키워드 매칭을 넘어서 의미 있는 검색 결과를 제공하고 싶었다.

### 고려한 옵션

1. **단순 키워드 매칭 (LIKE 검색)**
   - 장점: 구현 간단, 빠름
   - 단점: 유연성 부족, 오타 처리 안됨
   
2. **BM25 (Lexical Search)**
   - 장점: 검증된 알고리즘, 관련도 스코어링
   - 단점: 의미 이해 못함
   
3. **Semantic Search (임베딩 기반)**
   - 장점: 의미 이해, 유사 쿼리 처리
   - 단점: 느림, 리소스 많이 필요
   
4. **Elasticsearch**
   - 장점: 강력한 검색 기능, 확장성
   - 단점: 인프라 복잡도, 오버킬

## 결정
**BM25 기반 Lexical Search + NER(Named Entity Recognition)을 조합한다.**

### 구현 방식

1. **BM25 Lexical Search**
   - 영화 제목, 장르, 줄거리에서 키워드 추출
   - TF-IDF 기반 관련도 스코어링
   
2. **NER (Named Entity Recognition)**
   - 쿼리에서 영화 제목, 배우, 감독, 장르 등 엔티티 추출
   - LLM 기반 엔티티 인식 (실험적)

3. **하이브리드 접근**
   - NER로 엔티티 추출 → 구조화된 필터링
   - BM25로 나머지 키워드 검색
   - 두 결과를 결합해서 최종 랭킹

### 선택 이유
1. **균형**: 정확도와 성능의 밸런스
2. **점진적 개선**: 기본 BM25 → NER 추가 → 향후 임베딩 추가 가능
3. **리소스 효율**: 임베딩보다 가볍고 빠름
4. **설명 가능성**: 왜 이 결과가 나왔는지 설명 가능

## 구현 세부사항

### BM25
- 라이브러리: `rank-bm25`
- 인덱싱: 영화 제목 + 장르 + 줄거리 (TMDB)
- 전처리: 소문자 변환, 불용어 제거

### NER
- 방식 1: 규칙 기반 (장르 키워드 매칭)
- 방식 2: LLM 기반 (실험적)
- 모델: [TBD - 사용한 모델 명시]

## 결과
- `modeling/models/query_search/lexical_search/` - BM25 구현
- `modeling/models/query_search/ner/` - NER 구현
- `dataset_generation/` - 쿼리 데이터셋 생성

## 성능 지표
- [TBD - 검색 정확도, 속도 등 측정 결과]

## 향후 개선 방향
- [ ] Semantic Search 추가 (하이브리드)
- [ ] 사용자 피드백 기반 랭킹 개선
- [ ] 자동완성 기능
- [ ] 검색 로그 분석

## 참고 자료
- [BM25 알고리즘 설명]
- `modeling/models/query_search/README.md`

## 관련 결정
- [ADR 002: 추천 알고리즘 선택](./002-recommendation-algorithm.md)

