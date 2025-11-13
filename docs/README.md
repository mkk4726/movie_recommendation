# 프로젝트 문서

> 영화 추천 시스템 개발 과정 기록

## 📚 문서 구조

### 1. [JOURNAL.md](./JOURNAL.md)
**시간순 작업 일지**
- 날짜별로 무엇을 했는지 기록
- 문제 해결 과정, 배운 점 정리
- 다음 할 일 체크리스트

### 2. [decisions/](./decisions/)
**주요 의사결정 기록 (ADR - Architecture Decision Records)**
- 왜 이런 기술/방법을 선택했는지
- 어떤 대안들을 고려했는지
- 트레이드오프와 결과

현재 문서:
- [001: 데이터 소스 선택](./decisions/001-data-source-selection.md)
- [002: 추천 알고리즘 선택](./decisions/002-recommendation-algorithm.md)
- [003: 데이터베이스 선택](./decisions/003-database-choice.md)
- [004: 검색 시스템](./decisions/004-search-system.md)

### 3. [templates/](./templates/)
**문서 작성 템플릿**
- [Journal Template](./templates/journal-template.md) - 일지 작성용
- [Decision Template](./templates/decision-template.md) - 의사결정 기록용

---

## 🚀 빠른 시작

### 작업 일지 작성하기
1. `JOURNAL.md` 열기
2. `templates/journal-template.md`에서 템플릿 복사
3. 날짜와 내용 채우기
4. 최상단에 추가 (최신이 위로)

### 의사결정 기록하기
1. `templates/decision-template.md` 복사
2. `decisions/` 폴더에 `[번호]-[제목].md`로 저장
3. 내용 작성
4. `decisions/README.md`의 목록에 추가

---

## 📖 작성 가이드

### 언제 JOURNAL에 기록하나?
- ✅ 매일 작업 종료 시
- ✅ 중요한 문제를 해결했을 때
- ✅ 새로운 것을 배웠을 때
- ✅ 마일스톤 달성 시

### 언제 ADR을 작성하나?
- ✅ 기술 스택 선택 (프레임워크, 라이브러리)
- ✅ 아키텍처 패턴 결정
- ✅ 알고리즘 선택
- ✅ 데이터베이스/인프라 선택
- ✅ 중요한 설계 결정

### 작성 원칙
1. **구체적으로**: "모델 학습함" ❌ → "SVD 모델 학습 (RMSE: 0.85)" ✅
2. **솔직하게**: 실패와 시행착오도 기록
3. **미래의 나를 위해**: 6개월 후에도 이해할 수 있게
4. **코드/명령어 포함**: 재현 가능하게

---

## 🎯 이 문서의 목적

### 1. **학습 기록**
- 무엇을 배웠는지 정리
- 같은 실수 반복 방지

### 2. **의사결정 추적**
- "왜 이렇게 했지?" 질문에 답하기
- 더 나은 결정을 위한 피드백

### 3. **포트폴리오**
- 문제 해결 능력 증명
- 기술적 깊이 보여주기

### 4. **협업 준비**
- 다른 사람이 프로젝트 이해하기 쉽게
- 온보딩 자료로 활용

---

## 📊 프로젝트 타임라인

```
[데이터 수집] → [모델링] → [API 개발] → [배포]
     ↓              ↓            ↓           ↓
  Scraping      SVD/CF      FastAPI    Firebase
  TMDB API      BM25/NER    Auth       Hosting
```

자세한 내용은 [JOURNAL.md](./JOURNAL.md) 참고

---

## 🔗 관련 문서

### 프로젝트 루트
- [메인 README](../README.md) - 프로젝트 개요
- [requirements.txt](../requirements.txt) - 의존성 목록

### 모듈별 README
- [Data Scraping](../data_scraping/README.md)
- [Dataset Generation](../dataset_generation/README.md)
- [Modeling](../modeling/README.md)
- [User System](../user_system/README.md)
- [App](../app/README.md)

---

## 💡 팁

### 정기적으로 리뷰하기
- 주말마다 이번 주 작업 요약
- 월말마다 한 달 회고
- 프로젝트 완료 후 전체 회고

### 다른 사람과 공유하기
- GitHub에 올려서 피드백 받기
- 블로그 포스트로 재가공
- 면접 시 포트폴리오로 활용

### 지속적으로 업데이트
- 문서는 살아있는 것
- 새로운 인사이트 생기면 추가
- 잘못된 결정은 Superseded로 표시

---

## 📝 작성 현황

- ✅ 문서 구조 설정
- ✅ 템플릿 생성
- 📝 기존 작업 내역 정리 중
- 📝 ADR 초안 작성 중

**다음 할 일:**
- [ ] 프로젝트 시작부터 현재까지 JOURNAL 작성
- [ ] 각 ADR 초안 완성 (날짜, 구체적 수치 추가)
- [ ] 스크린샷/다이어그램 추가
- [ ] 주요 코드 스니펫 추가

---

**Last Updated**: 2024-11-13

