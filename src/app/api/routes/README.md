# API Routes 구조

이 디렉토리는 FastAPI 라우트 파일들을 역할별로 구분하여 관리합니다.

## 라우트 분류

### 🔍 검색 관련 (Search)
- `search.py` - 자연어 검색 (BM25 기반)
  - `GET /search/natural-language` - 자연어 쿼리로 영화 검색
  - 필터: `min_rating`, `min_vote_count`, `search_genre`, `search_language`

- `poster_search.py` - 포스터 검색 (CLIP 기반)
  - `GET /search/poster` - 텍스트 설명으로 포스터 검색
  - 필터: `min_rating`, `min_vote_count`, `poster_genre`, `poster_language`

- `movies.py` - 기본 영화 검색
  - `GET /movies/search` - 제목 기반 영화 검색
  - 필터: `min_rating`, `min_vote_count`

### 🎬 추천 관련 (Recommendation)
- `movies.py` - 영화 기반 추천
  - `GET /movies/{movie_id}/similar` - 유사 영화 추천
  - 필터: `movie_genre`, `movie_language`, `min_year`, `max_year`

- `users.py` - 사용자 기반 추천
  - `GET /users/{user_id}/recommendations` - 사용자 맞춤 추천

### 👤 사용자 관련 (User)
- `auth.py` - 인증
  - `POST /auth/signup` - 회원가입
  - `POST /auth/login` - 로그인
  - `POST /auth/logout` - 로그아웃

- `ratings.py` - 평점 관리
  - `POST /rating/add` - 평점 추가/수정
  - `POST /rating/delete` - 평점 삭제
  - `POST /rating/explore` - 랜덤 영화 탐색

- `activity.py` - 활동 로깅
  - `POST /activity/click` - 클릭 이벤트 로깅
  - `GET /activity/ctr-data` - CTR 데이터 조회
  - `GET /activity/stats` - 활동 통계 조회

### 🏠 기타 (Others)
- `home.py` - 프론트엔드 렌더링
  - `GET /` - HTML 페이지 렌더링

- `health.py` - 헬스체크
  - `GET /health` - API 상태 확인

## 필터링 기능

모든 검색 엔드포인트는 다양한 필터를 지원합니다:

### 1. 평점/평가수 필터 ⭐👥
- `min_rating` (float): 최소 평균 평점 (0-10)
- `min_vote_count` (int): 최소 평가 수

**적용 대상:**
- 자연어 검색 (`/search/natural-language`)
- 포스터 검색 (`/search/poster`)
- 영화 검색 (`/movies/search`)

### 2. 장르/언어 필터 🎭🌍

#### API 엔드포인트 파라미터
- **자연어 검색 API** (`/search/natural-language`)
  - `genre` (List[str]): 장르 필터 (중복 선택 가능)
  - `language` (List[str]): 언어 필터 (중복 선택 가능)

- **포스터 검색 API** (`/search/poster`)
  - `genre` (List[str]): 장르 필터 (중복 선택 가능)
  - `language` (List[str]): 언어 필터 (중복 선택 가능)

#### 프론트엔드 파라미터 (home.py)
자연어 검색과 포스터 검색은 프론트엔드에서 별도 파라미터를 사용:
- `search_genre` / `search_language`: 자연어 검색용
- `poster_genre` / `poster_language`: 포스터 검색용
- `movie_genre` / `movie_language`: 영화 기반 추천용

### 프론트엔드 UI 🎨
- 모든 검색 페이지에 "고급 필터 옵션" 섹션 추가
- 접을 수 있는 `<details>` 요소로 깔끔한 UX
- 장르/언어는 체크박스로 다중 선택 가능
- 사용자가 입력한 필터 값은 검색 후에도 유지됨
- 비슷한 영화 추천과 동일한 UI 패턴 적용

## 개발 규칙

1. **URL 경로는 변경하지 않기** - 프론트엔드 호환성 유지
2. **파일 위치만 조정** - 관련 기능끼리 그룹화
3. **문서화 유지** - 각 라우트의 역할과 파라미터 명시
4. **필터 일관성** - 모든 검색 엔드포인트에 동일한 필터 패턴 적용
