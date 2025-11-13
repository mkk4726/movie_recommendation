# ADR 003: 데이터베이스 선택 - Firebase

## 상태
📝 Draft

## 날짜
[작성 날짜]

## 컨텍스트
사용자 인증, 프로필, 평점 저장을 위한 데이터베이스가 필요했다. 빠른 프로토타이핑과 배포 용이성을 중시했다.

### 고려한 옵션

1. **Firebase (Firestore + Auth)**
   - 장점: 빠른 설정, 인증 통합, 무료 티어, NoSQL 유연성
   - 단점: 벤더 락인, 복잡한 쿼리 제한
   
2. **PostgreSQL**
   - 장점: 강력한 쿼리, ACID 보장, 무료
   - 단점: 서버 관리 필요, 인증 직접 구현
   
3. **MongoDB**
   - 장점: 유연한 스키마, 확장성
   - 단점: 호스팅 비용, 인증 별도 구현
   
4. **SQLite**
   - 장점: 간단, 서버 불필요
   - 단점: 다중 사용자 지원 약함, 배포 제한

## 결정
**Firebase (Firestore + Authentication)를 사용한다.**

### 선택 이유
1. **통합 솔루션**: 인증 + DB + 호스팅 한 번에 해결
2. **빠른 개발**: 백엔드 인프라 걱정 없이 기능 구현에 집중
3. **무료 티어**: 프로토타입 단계에서 비용 부담 없음
4. **실시간 기능**: 실시간 업데이트 지원 (향후 활용 가능)
5. **확장성**: 사용자 증가해도 자동 스케일링

### 트레이드오프
- **제한된 쿼리**: 복잡한 분석 쿼리는 어려움 → 추천 모델은 로컬에서 학습
- **비용**: 사용량 증가 시 비용 발생 가능 → 캐싱으로 읽기 최소화

## 구현 세부사항

### 데이터 구조
```
users/
  {userId}/
    - email
    - displayName
    - createdAt
    
ratings/
  {userId}/
    ratings/
      {movieId}/
        - rating
        - timestamp
```

### 보안 규칙
- 사용자는 자신의 데이터만 읽기/쓰기 가능
- 인증된 사용자만 접근

## 결과
- `user_system/firebase_*.py` - Firebase 통합 모듈
- `movie-recommendation-*-firebase-adminsdk-*.json` - 서비스 계정 키

## 대안 시나리오
만약 다음 상황이 발생하면 PostgreSQL로 마이그레이션 고려:
- 월 비용이 $50 초과
- 복잡한 분석 쿼리 필요
- 데이터 주권 이슈

## 참고 자료
- [Firebase Documentation](https://firebase.google.com/docs)
- `user_system/setup_guide.md`

## 관련 결정
- [ADR 006: API 프레임워크 선택](./006-api-framework.md) (TBD)

