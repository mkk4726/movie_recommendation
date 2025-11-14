# Architecture Decision Records (ADR)

> 프로젝트의 주요 의사결정 기록

## 의사결정 목록

| 번호 | 제목 | 날짜 | 상태 |
|------|------|------|------|
| 001 | [데이터 소스 선택: MovieLens 32M](./001-data-source-selection.md) | TBD | 📝 Draft |
| 002 | [추천 알고리즘 선택: SVD + Item-based CF](./002-recommendation-algorithm.md) | TBD | 📝 Draft |
| 003 | [데이터베이스 선택: Firebase (Google Auth)](./003-database-choice.md) | 2025-10-25 | ✅ Accepted |
| 004 | [검색 시스템: BM25 + NER](./004-search-system.md) | TBD | 📝 Draft |
| 005 | [벡터 저장소 선택: FAISS](./005-vector-database.md) | 2025-11-14 | ✅ Accepted |

## 상태 표시
- 📝 Draft: 초안 작성 중
- ✅ Accepted: 승인됨
- 🔄 Superseded: 다른 결정으로 대체됨
- ❌ Rejected: 기각됨

## 작성 가이드

1. `templates/decision-template.md` 복사
2. 파일명: `[번호]-[간단한-제목].md` (예: `005-api-framework.md`)
3. 위 표에 추가
4. JOURNAL.md에서 해당 결정 링크

## ADR이란?

Architecture Decision Record는 프로젝트에서 내린 중요한 기술적 결정을 문서화하는 방법입니다.

**왜 필요한가?**
- 나중에 "왜 이렇게 했지?"라는 질문에 답할 수 있음
- 팀원/미래의 나에게 컨텍스트 제공
- 실수를 반복하지 않기 위해
- 포트폴리오에서 의사결정 능력 증명

**언제 작성하나?**
- 중요한 기술 스택 선택
- 아키텍처 패턴 결정
- 라이브러리/프레임워크 선택
- 데이터 구조 설계
- 성능 최적화 방향

