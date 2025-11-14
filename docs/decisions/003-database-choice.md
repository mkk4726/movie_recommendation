# ADR 003: 데이터베이스 선택 - Firebase

## 상태
✅ Accepted

## 날짜
2025-10-25

## 컨텍스트
사용자 인증, 프로필, 평점 저장을 위한 데이터베이스가 필요했다. 특히 **Google Authentication을 통한 간편한 사용자 인증**이 중요했고, 빠른 프로토타이핑과 배포 용이성을 중시했다.

### 고려한 옵션

1. **Firebase (Firestore + Auth)**
   - 장점:
     - **Google Authentication 기본 제공** (OAuth 2.0)
     - 몇 줄의 코드로 로그인 구현
     - 인증 + DB + 호스팅 통합
     - 무료 티어 (Spark Plan)
     - NoSQL 유연성
     - 실시간 동기화
   - 단점:
     - 벤더 락인
     - 복잡한 쿼리 제한
   
2. **PostgreSQL + OAuth 직접 구현**
   - 장점:
     - 강력한 쿼리 (JOIN, 집계)
     - ACID 보장
     - 무료 (Supabase 등)
   - 단점:
     - **Google OAuth 직접 구현 필요** (복잡)
     - 세션 관리, 토큰 검증 등 보안 구현
     - 서버 관리 필요
   
3. **MongoDB + Auth0/Clerk**
   - 장점:
     - 유연한 스키마
     - 확장성
   - 단점:
     - **인증 서비스 별도 비용**
     - 호스팅 비용
     - 통합 복잡도 증가
   
4. **SQLite + 자체 인증**
   - 장점:
     - 간단, 서버 불필요
   - 단점:
     - **Google 로그인 불가능**
     - 다중 사용자 지원 약함
     - 배포 제한

## 결정
**Firebase (Firestore + Authentication)를 사용한다.**

### 선택 이유

1. **Google Authentication 간편 통합** ⭐
   ```python
   # Firebase는 이것만으로 Google 로그인 완성
   from firebase_admin import auth
   
   # 프론트엔드에서 받은 ID 토큰 검증
   decoded_token = auth.verify_id_token(id_token)
   user_id = decoded_token['uid']
   ```
   - OAuth 2.0 플로우 자동 처리
   - 토큰 검증, 갱신 자동
   - 사용자 정보 자동 동기화
   - **직접 구현 시 수백 줄 코드 필요**

2. **통합 솔루션**
   - 인증 + DB + 호스팅 한 번에 해결
   - 별도 인증 서비스(Auth0 등) 불필요
   - 프론트엔드 SDK 제공

3. **빠른 개발**
   - 백엔드 인프라 걱정 없이 기능 구현에 집중
   - 보안 규칙으로 권한 관리
   - 실시간 업데이트 지원

4. **무료 티어**
   - Spark Plan: 무료
   - 읽기 50K/일, 쓰기 20K/일
   - 프로토타입 단계 충분

5. **확장성**
   - 사용자 증가해도 자동 스케일링
   - 글로벌 CDN

### 트레이드오프

| 제약사항 | 영향 | 해결책 |
|---------|------|--------|
| 제한된 쿼리 | 복잡한 JOIN 불가 | 추천 모델은 로컬에서 학습, Firestore는 사용자 데이터만 |
| 비용 | 사용량 증가 시 비용 | 캐싱으로 읽기 최소화, 무료 티어 내 사용 |
| 벤더 락인 | 마이그레이션 어려움 | 데이터 구조 단순화, export 주기적 백업 |

## 구현 세부사항

### 인증 플로우
```python
# 1. 프론트엔드: Google 로그인 버튼 클릭
# Firebase SDK가 자동으로 OAuth 처리

# 2. 백엔드: ID 토큰 검증
from firebase_admin import auth

def verify_user(id_token: str):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return {
            "uid": decoded_token['uid'],
            "email": decoded_token['email'],
            "name": decoded_token.get('name')
        }
    except Exception as e:
        raise AuthenticationError("Invalid token")
```

### 데이터 구조
```
Firestore:
users/
  {userId}/
    - email: string
    - displayName: string
    - photoURL: string
    - createdAt: timestamp
    - provider: "google.com"
    
ratings/
  {userId}/
    ratings/
      {movieId}/
        - rating: float (0.5-5.0)
        - timestamp: timestamp
        - movieTitle: string (비정규화)
```

### 보안 규칙
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 사용자는 자신의 데이터만 접근
    match /users/{userId} {
      allow read, write: if request.auth.uid == userId;
    }
    
    match /ratings/{userId}/ratings/{movieId} {
      allow read, write: if request.auth.uid == userId;
    }
  }
}
```

## 결과
- `user_system/firebase_*.py` - Firebase 통합 모듈
  - `firebase_auth.py` - Google 인증 처리
  - `firebase_firestore.py` - 사용자 데이터 CRUD
- `movie-recommendation-*-firebase-adminsdk-*.json` - 서비스 계정 키 (gitignore)

## 실제 사용 예시

### Google 로그인 구현
```python
# FastAPI 엔드포인트
@app.post("/auth/google")
async def google_login(token: str):
    user = verify_user(token)
    
    # Firestore에 사용자 정보 저장/업데이트
    db.collection('users').document(user['uid']).set({
        'email': user['email'],
        'displayName': user['name'],
        'lastLogin': firestore.SERVER_TIMESTAMP
    }, merge=True)
    
    return {"user_id": user['uid']}
```

## 대안 시나리오

**PostgreSQL로 마이그레이션 고려 시점:**
- 월 비용이 $50 초과
- 복잡한 분석 쿼리 필요 (사용자 행동 분석 등)
- 데이터 주권 이슈 (특정 국가 서버 필요)

**하지만 현재는:**
- Google 로그인의 편의성 > 다른 모든 이점
- 프로토타입 단계에서 최적의 선택

## 참고 자료
- [Firebase Authentication - Google](https://firebase.google.com/docs/auth/web/google-signin)
- [Firestore 보안 규칙](https://firebase.google.com/docs/firestore/security/get-started)
- `user_system/setup_guide.md`

## 관련 결정
- [ADR 005: 벡터 저장소 선택](./005-vector-database.md) - Firebase(사용자) vs FAISS(벡터) 역할 분리

