# 메모리 디버깅 가이드

## 문제 상황
서버(Streamlit 앱)가 실행 중 메모리 부족으로 죽는 문제

## 디버깅 방법

### 1. 디버그 모드로 앱 실행

```bash
# 방법 1: 쉘 스크립트 사용 (권장)
chmod +x run_debug.sh
./run_debug.sh

# 방법 2: 직접 환경변수 설정
export DEBUG_MEMORY=true
streamlit run streamlit_app.py
```

디버그 모드에서는:
- 사이드바에 실시간 메모리 사용량 표시
- 각 추천/검색 작업 전후 메모리 변화 표시
- "메모리 정리" 버튼으로 수동 가비지 컬렉션 가능

### 2. 독립 메모리 프로파일링

특정 함수의 메모리 사용량을 자세히 분석하려면:

```python
from debug_memory import memory_profiler, print_memory_usage

# 함수에 데코레이터 추가
@memory_profiler
def my_function():
    # 코드
    pass

# 또는 현재 메모리 확인
print_memory_usage("현재 상태")
```

### 3. 상세 메모리 추적

어떤 코드 라인이 메모리를 많이 사용하는지 확인:

```python
from debug_memory import start_memory_tracking, show_top_memory_usage

# 추적 시작
start_memory_tracking()

# ... 코드 실행 ...

# 메모리 사용량 Top 10 출력
show_top_memory_usage(limit=10)
```

## 주요 메모리 사용 지점

### 1. 데이터 로딩 (load_all_data)
- `df_movies`: 약 10-50MB
- `df_ratings`: 크기에 따라 50-200MB
- `df_ratings_filtered`: 필터링 후 약간 감소

### 2. 모델 초기화 (initialize_recommender)
- SVD 모델: n_factors=20 기준 약 20-50MB
- TF-IDF 매트릭스: max_features=2000 기준 약 10-30MB

### 3. 협업 필터링 기반 유사 영화 검색 (find_similar_movies with method='collaborative')
⚠️ **가장 메모리를 많이 사용하는 부분!**
- 모든 사용자에 대해 예측 수행
- 사용자 수가 많으면 기하급수적으로 증가
- 예: 1000명 사용자 × 5000개 영화 = 5백만 번 예측

### 4. 하이브리드 추천 (hybrid_recommend)
- 모든 영화에 대해 CF + CB 점수 계산
- 중간 크기의 메모리 사용

## 최적화 방법

### 즉시 적용 가능한 방법

1. **사용자 수 제한 강화**
```python
# streamlit_app.py 149, 248번째 줄
user_list = df_ratings_filtered['user_id'].unique()[:50]  # 100 -> 50
```

2. **협업 필터링 유사도 검색 비활성화**
```python
# 메모리가 부족하면 "컨텐츠 기반"만 사용
similarity_method = st.selectbox(
    "유사도 방법",
    ["컨텐츠 기반"],  # "협업 필터링" 제거
)
```

3. **추천 개수 제한**
```python
n_recommendations = st.slider("추천 개수", 5, 10, 5)  # 최대값 10으로 축소
```

### 근본적 해결 방법

1. **배치 처리 구현**
- 모든 영화를 한번에 처리하지 않고 배치로 나눔
- 메모리 사용량 제어 가능

2. **캐싱 전략 개선**
- 자주 사용되는 유사도 계산 결과를 사전 계산
- 디스크에 저장 후 필요시 로드

3. **서버 메모리 증설**
- 최소 2GB 이상 권장
- 4GB 이상이면 안정적

## 모니터링 명령어

### 시스템 메모리 확인 (터미널)
```bash
# Mac/Linux
top -o mem
# 또는
htop

# 현재 Python 프로세스만 확인
ps aux | grep streamlit
```

### Python 메모리 프로파일링
```python
import gc
gc.collect()  # 가비지 컬렉션 수동 실행

# 객체 수 확인
import sys
print(len(gc.get_objects()))
```

## 문제 발생 시 체크리스트

- [ ] 디버그 모드로 실행했는가?
- [ ] 어떤 작업에서 메모리가 급증하는가?
- [ ] 사용자 수/영화 수가 너무 많지 않은가?
- [ ] 협업 필터링 유사도 검색을 사용했는가?
- [ ] 시스템 전체 메모리가 얼마나 남았는가?
- [ ] 다른 프로그램이 메모리를 과다 사용하고 있는가?

## 참고

- `debug_memory.py`: 메모리 모니터링 유틸리티
- `streamlit_app.py`: 메인 앱 (디버그 모드 통합됨)
- `utils/recommender_lite.py`: 추천 알고리즘 (메모리 최적화 버전)

