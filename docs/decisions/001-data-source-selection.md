# ADR 001: 데이터 소스 선택 - MovieLens 32M

## 상태
📝 Draft

## 날짜
[작성 날짜]

## 컨텍스트
영화 추천 시스템을 구축하기 위해서는 대량의 영화 정보와 사용자 평점 데이터가 필요했다.

### 고려한 옵션
1. **MovieLens 데이터셋**
   - 장점: 깨끗한 데이터, 학술 연구용으로 검증됨, 무료
   - 단점: 실시간 업데이트 안됨
   
2. **직접 스크래핑 (왓챠 등)**
   - 장점: 최신 데이터, 한국 사용자 취향 반영
   - 단점: 법적 이슈, 유지보수 부담
   
3. **TMDB API**
   - 장점: 공식 API, 최신 데이터, 이미지/메타데이터 풍부
   - 단점: 평점 데이터 부족

## 결정
**MovieLens 32M 데이터셋을 메인 데이터 소스로 사용하고, TMDB API로 메타데이터를 보강한다.**

### 선택 이유
1. **데이터 품질**: 3200만 개의 검증된 평점 데이터
2. **법적 안정성**: 공개 데이터셋으로 라이선스 문제 없음
3. **학습 목적**: 추천 알고리즘 학습에 집중 가능
4. **확장성**: TMDB로 포스터, 줄거리 등 추가 정보 확보

## 결과
- `data_scraping/data/ml-32m/` 디렉토리에 데이터 저장
- TMDB 데이터는 `data_scraping/data/tmdb/` 에 별도 저장
- 두 데이터를 `movieId`와 `tmdbId`로 연결

## 참고 자료
- [MovieLens Dataset](https://grouplens.org/datasets/movielens/)
- [TMDB API Documentation](https://developers.themoviedb.org/3)

## 관련 결정
- [ADR 002: 추천 알고리즘 선택](./002-recommendation-algorithm.md)

