# 🔥 Firebase 영화 추천 시스템 설정 가이드

Firebase 기반 영화 추천 시스템을 설정하는 완전한 가이드입니다.

## 📋 사전 준비사항

- Google 계정
- Python 3.8+
- 기존 영화 추천 시스템 모델 파일들

## 🚀 단계별 설정

### 1단계: Firebase 프로젝트 생성

#### 1.1 Firebase Console 접속
1. [Firebase Console](https://console.firebase.google.com) 접속
2. Google 계정으로 로그인

#### 1.2 새 프로젝트 생성
1. "프로젝트 추가" 클릭
2. 프로젝트 이름 입력: `movie-recommendation`
3. Google Analytics 활성화 (선택사항)
4. "프로젝트 만들기" 클릭

### 2단계: Authentication 설정

#### 2.1 Authentication 활성화
1. 좌측 메뉴에서 "Authentication" 클릭
2. "시작하기" 클릭
3. "Sign-in method" 탭 클릭

#### 2.2 이메일/비밀번호 인증 활성화
1. "이메일/비밀번호" 클릭
2. "사용 설정" 토글 활성화
3. "저장" 클릭

### 3단계: Firestore Database 설정

#### 3.1 Firestore Database 생성
1. 좌측 메뉴에서 "Firestore Database" 클릭
2. "데이터베이스 만들기" 클릭
3. 보안 규칙: "테스트 모드" 선택 (개발용)
4. 위치: `asia-northeast3` (서울) 선택
5. "완료" 클릭

#### 3.2 보안 규칙 설정
1. "규칙" 탭 클릭
2. 다음 규칙 입력:

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

3. "게시" 클릭

### 4단계: 서비스 계정 키 생성

#### 4.1 프로젝트 설정 접속
1. 좌측 메뉴에서 "프로젝트 설정" (⚙️) 클릭
2. "서비스 계정" 탭 클릭

#### 4.2 서비스 계정 키 생성
1. "새 비공개 키 생성" 클릭
2. "키 생성" 클릭
3. JSON 파일 다운로드
4. 파일을 안전한 위치에 저장

### 5단계: Python 환경 설정

#### 5.1 의존성 설치
```bash
cd user_system
pip install -r requirements.txt
```

#### 5.2 환경변수 설정 (선택사항)
```bash
export FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/your/service-account-key.json"
```

### 6단계: 앱 실행

#### 6.1 기본 앱 실행
```bash
streamlit run firebase_app.py
```

#### 6.2 통합 앱 실행
```bash
streamlit run firebase_integrated_app.py
```

## 🔧 고급 설정

### Firebase 보안 규칙 최적화

#### 개발 환경
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if true;
    }
  }
}
```

#### 프로덕션 환경
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 사용자 데이터
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // 평점 데이터
    match /user_ratings/{ratingId} {
      allow read, write: if request.auth != null;
      allow read: if resource.data.user_id == request.auth.uid;
    }
    
    // 영화 메타데이터
    match /movie_metadata/{movieId} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

### Firebase 인덱스 설정

#### 복합 인덱스 생성
1. Firestore Console에서 "인덱스" 탭 클릭
2. "복합 인덱스 만들기" 클릭
3. 다음 인덱스들 생성:

**user_ratings 컬렉션:**
- `user_id` (오름차순) + `created_at` (내림차순)
- `movie_id` (오름차순) + `rating` (내림차순)

**movie_metadata 컬렉션:**
- `genre` (오름차순) + `avg_score` (내림차순)
- `year` (내림차순) + `popularity` (내림차순)

## 🧪 테스트

### 1. Firebase 연결 테스트
```python
from user_system.firebase_config import init_firebase

if init_firebase():
    print("✅ Firebase 연결 성공!")
else:
    print("❌ Firebase 연결 실패")
```

### 2. 인증 테스트
```python
from user_system.firebase_auth import FirebaseAuthManager

auth_manager = FirebaseAuthManager()
auth_manager.init_session_state()

# 데모 로그인 테스트
if auth_manager.login_with_custom_token("demo_token"):
    print("✅ 인증 성공!")
else:
    print("❌ 인증 실패")
```

### 3. 데이터베이스 테스트
```python
from user_system.firebase_firestore import FirestoreManager

firestore_manager = FirestoreManager()

# 평점 추가 테스트
success = firestore_manager.add_user_rating("test_user", "test_movie", 4.5)
if success:
    print("✅ 평점 저장 성공!")
else:
    print("❌ 평점 저장 실패")
```

## 🐛 문제 해결

### 일반적인 문제

#### 1. Firebase 연결 실패
**증상:** "Firebase가 초기화되지 않았습니다" 오류
**해결책:**
- 서비스 계정 키 파일 경로 확인
- JSON 파일 형식 확인
- Firebase 프로젝트 ID 확인

#### 2. 인증 실패
**증상:** 로그인이 되지 않음
**해결책:**
- Firebase Console에서 Authentication 설정 확인
- 이메일/비밀번호 인증 활성화 확인
- 보안 규칙 확인

#### 3. 권한 오류
**증상:** "권한이 없습니다" 오류
**해결책:**
- Firestore 보안 규칙 확인
- 사용자 인증 상태 확인
- 서비스 계정 권한 확인

### 로그 확인

#### Streamlit 로그
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Firebase 로그
1. Firebase Console에서 "Functions" 탭
2. "로그" 섹션에서 오류 확인

## 📊 모니터링

### Firebase Console 모니터링
1. **Authentication**: 사용자 수, 로그인 통계
2. **Firestore**: 읽기/쓰기 작업 수
3. **Storage**: 사용량 및 비용

### 성능 최적화
1. **인덱스**: 자주 조회되는 쿼리에 인덱스 생성
2. **캐싱**: 클라이언트 사이드 캐싱 활용
3. **페이징**: 대량 데이터 처리 시 limit 사용

## 🔒 보안 체크리스트

- [ ] Firebase 보안 규칙 설정
- [ ] 서비스 계정 키 파일 보안
- [ ] 사용자 데이터 암호화
- [ ] API 키 보안
- [ ] 로그 모니터링

## 📞 지원

문제가 발생하면:
1. Firebase Console에서 로그 확인
2. GitHub Issues에 보고
3. Firebase 문서 참조

## 🔗 유용한 링크

- [Firebase Console](https://console.firebase.google.com)
- [Firebase 문서](https://firebase.google.com/docs)
- [Firestore 보안 규칙](https://firebase.google.com/docs/firestore/security/get-started)
- [Firebase Authentication](https://firebase.google.com/docs/auth)
- [Streamlit 문서](https://docs.streamlit.io)
