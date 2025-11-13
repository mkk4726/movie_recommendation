# ADR 002: 추천 알고리즘 선택 - SVD + Item-based CF

## 상태
📝 Draft

## 날짜
[작성 날짜]

## 컨텍스트
사용자에게 영화를 추천하기 위한 알고리즘을 선택해야 했다. 정확도와 구현 복잡도, 그리고 설명 가능성을 모두 고려해야 했다.

### 고려한 옵션

1. **Matrix Factorization (SVD)**
   - 장점: 높은 정확도, 잠재 요인 학습
   - 단점: Cold start 문제, 설명 어려움
   
2. **Item-based Collaborative Filtering**
   - 장점: 직관적, "이 영화를 본 사람들은..." 설명 가능
   - 단점: 확장성 이슈, 희소성 문제
   
3. **Deep Learning (Neural CF, Transformers)**
   - 장점: 최신 기술, 복잡한 패턴 학습
   - 단점: 과도한 복잡도, 데이터/컴퓨팅 리소스 필요
   
4. **Content-based Filtering**
   - 장점: Cold start 해결, 설명 가능
   - 단점: 다양성 부족, 메타데이터 의존

## 결정
**SVD와 Item-based CF를 하이브리드로 사용한다.**

### 구현 방식
1. **User-based 추천**: SVD 사용
   - 사용자의 평점 패턴 학습
   - 개인화된 추천 제공
   
2. **Movie-based 추천**: Item-based CF 사용
   - 특정 영화와 유사한 영화 찾기
   - "이 영화를 좋아한다면..." 시나리오

### 선택 이유
1. **상호 보완**: SVD의 정확도 + Item-based의 설명 가능성
2. **다양한 사용 케이스**: 개인화 추천 & 유사 영화 추천
3. **구현 가능성**: Surprise 라이브러리로 빠른 프로토타이핑
4. **성능**: 3200만 평점 데이터에서도 합리적인 학습 시간

## 구현 세부사항

### SVD
- 라이브러리: `surprise`
- 하이퍼파라미터: [TBD]
- 학습 데이터: MovieLens 32M ratings

### Item-based CF
- 유사도 메트릭: Cosine Similarity
- 캐싱: 사전 계산된 유사도 행렬 저장

## 결과
- `modeling/models/svd/` - SVD 모델 구현
- `modeling/models/item_based/` - Item-based CF 구현
- `modeling/models/recommender/` - 통합 추천 시스템

## 향후 개선 방향
- [ ] Cold start 문제 해결 (Content-based 추가)
- [ ] 실시간 업데이트 메커니즘
- [ ] A/B 테스트로 성능 비교

## 참고 자료
- [Surprise Documentation](http://surpriselib.com/)
- [Netflix Prize 논문들]

## 관련 결정
- [ADR 001: 데이터 소스 선택](./001-data-source-selection.md)
- [ADR 004: 검색 시스템](./004-search-system.md)

