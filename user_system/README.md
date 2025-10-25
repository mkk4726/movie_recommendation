# 🔥 Firebase 기반 영화 추천 시스템

Firebase를 활용한 확장 가능한 영화 추천 시스템입니다.

## 🏗️ 시스템 구조

```
user_system/
├── __init__.py              # 모듈 초기화
├── firebase_config.py        # Firebase 설정 및 초기화
├── firebase_auth.py         # Firebase Authentication
├── firebase_firestore.py    # Firestore 데이터 관리
├── firebase_app.py         # 메인 Streamlit 앱
├── requirements.txt        # 의존성
└── README.md              # 문서
```

## 🚀 주요 기능

### 1. Firebase Authentication
- **이메일/비밀번호** 인증
- **Google 소셜 로그인** (확장 가능)
- **사용자 프로필** 관리
- **세션 관리** (Streamlit 세션 기반)

### 2. Firestore Database
- **실시간 동기화**: 평점이 즉시 저장
- **확장성**: 수백만 사용자 지원
- **오프라인**: 네트워크 없이도 작동
- **보안**: Firebase 보안 규칙

### 3. 영화 평점 시스템
- **평점 입력**: 0.5~5.0 범위
- **평점 관리**: 조회, 수정, 삭제
- **통계**: 사용자별 평점 통계
- **검색**: 영화 제목 기반 검색

## 🔧 설정 방법

### 1. Firebase 프로젝트 생성
1. [Firebase Console](https://console.firebase.google.com) 접속
2. "프로젝트 추가" 클릭
3. 프로젝트 이름 입력
4. Google Analytics 활성화 (선택사항)

### 2. Authentication 설정
1. 좌측 메뉴에서 "Authentication" 클릭
2. "시작하기" 클릭
3. "Sign-in method" 탭에서 "이메일/비밀번호" 활성화

### 3. Firestore Database 설정
1. 좌측 메뉴에서 "Firestore Database" 클릭
2. "데이터베이스 만들기" 클릭
3. 보안 규칙: "테스트 모드" 선택 (개발용)
4. 위치: asia-northeast3 (서울) 선택

### 4. 서비스 계정 키 생성
1. 좌측 메뉴에서 "프로젝트 설정" 클릭
2. "서비스 계정" 탭 클릭
3. "새 비공개 키 생성" 클릭
4. JSON 파일 다운로드

### 5. 의존성 설치
```bash
pip install -r requirements.txt
```

### 6. 앱 실행
```bash
streamlit run firebase_app.py
```

## 📊 Firestore 데이터 구조

### 컬렉션 구조
```
users/                    # 사용자 정보
├── {uid}/
│   ├── uid: string
│   ├── email: string
│   ├── display_name: string
│   ├── photo_url: string
│   ├── created_at: string
│   ├── updated_at: string
│   ├── profile_data: object
│   └── is_active: boolean

user_ratings/            # 사용자 평점
├── {user_id}_{movie_id}/
│   ├── user_id: string
│   ├── movie_id: string
│   ├── rating: number (0.5-5.0)
│   ├── created_at: string
│   └── updated_at: string

movie_metadata/          # 영화 메타데이터
├── {movie_id}/
│   ├── movie_id: string
│   ├── title: string
│   ├── year: number
│   ├── genre: string
│   ├── country: string
│   ├── runtime: number
│   ├── age_rating: string
│   ├── avg_score: number
│   ├── popularity: number
│   ├── review_count: number
│   ├── plot: string
│   ├── cast: string
│   └── created_at: string
```

## 🔒 보안 설정

### Firestore 보안 규칙
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 사용자는 자신의 데이터만 읽기/쓰기 가능
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // 평점은 인증된 사용자만 작성 가능
    match /user_ratings/{ratingId} {
      allow read, write: if request.auth != null;
    }
    
    // 영화 메타데이터는 모든 사용자가 읽기 가능
    match /movie_metadata/{movieId} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

## 🚀 사용법

### 1. Firebase 초기화
```python
from user_system.firebase_config import init_firebase

# Firebase 초기화
init_firebase("path/to/service-account-key.json")
```

### 2. 사용자 인증
```python
from user_system.firebase_auth import FirebaseAuthManager

auth_manager = FirebaseAuthManager()
auth_manager.init_session_state()

# 로그인 확인
if auth_manager.is_logged_in():
    user = auth_manager.get_current_user()
    print(f"로그인됨: {user['display_name']}")
```

### 3. 평점 관리
```python
from user_system.firebase_firestore import FirestoreManager

firestore_manager = FirestoreManager()

# 평점 추가
firestore_manager.add_user_rating(user_id, movie_id, 4.5)

# 사용자 평점 조회
ratings = firestore_manager.get_user_ratings(user_id)
```

## 📈 성능 최적화

### Firestore 최적화
- **인덱스**: 자주 조회되는 필드에 복합 인덱스 생성
- **쿼리 최적화**: 필요한 필드만 조회
- **페이징**: 대량 데이터 처리 시 limit 사용

### 캐싱 전략
- **사용자 데이터**: 세션에 캐싱
- **영화 메타데이터**: 로컬 캐싱
- **평점 데이터**: 실시간 동기화

## 🧪 테스트

### 단위 테스트
```python
# Firebase 연결 테스트
from user_system.firebase_config import init_firebase

if init_firebase():
    print("Firebase 연결 성공!")

# 사용자 생성 테스트
from user_system.firebase_auth import FirebaseAuthManager

auth_manager = FirebaseAuthManager()
# 테스트 코드...
```

### 통합 테스트
```python
# 전체 시스템 테스트
from user_system.firebase_app import main

# Streamlit 앱 테스트
main()
```

## 🔄 확장 계획

### 단기 계획
- [ ] Google 소셜 로그인
- [ ] 이메일 인증
- [ ] 비밀번호 재설정

### 중기 계획
- [ ] 실시간 추천 시스템
- [ ] 사용자 선호도 분석
- [ ] 영화 리뷰 시스템

### 장기 계획
- [ ] AI 기반 추천
- [ ] 소셜 기능 (친구, 팔로우)
- [ ] 모바일 앱 지원

## 🐛 문제 해결

### 일반적인 문제
1. **Firebase 연결 실패**: 서비스 계정 키 파일 확인
2. **인증 실패**: Firebase Console에서 Authentication 설정 확인
3. **권한 오류**: Firestore 보안 규칙 확인

### 로그 확인
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 📞 지원

문제가 발생하면:
1. Firebase Console에서 로그 확인
2. GitHub Issues에 보고
3. Firebase 문서 참조

## 🔗 관련 링크

- [Firebase Console](https://console.firebase.google.com)
- [Firebase 문서](https://firebase.google.com/docs)
- [Firestore 보안 규칙](https://firebase.google.com/docs/firestore/security/get-started)
- [Firebase Authentication](https://firebase.google.com/docs/auth)