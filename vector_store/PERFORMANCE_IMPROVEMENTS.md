# 벡터 스토어 생성 성능 개선

## 📈 개선 사항

### 이전 (순차 처리)
```python
for movie in movies:
    image = download_image(url)      # 순차 다운로드
    embedding = encode_image(image)  # 1개씩 인코딩
    add_to_index(embedding)
```

**문제점:**
- 이미지 다운로드 대기 시간 동안 CPU/GPU 유휴
- CLIP 모델을 1개씩 처리하여 GPU 활용도 낮음
- 네트워크 오류 시 재시도 없음

### 개선 후 (배치 + 멀티스레딩)
```python
# 1단계: 멀티스레딩으로 배치 다운로드 (100개)
with ThreadPoolExecutor(max_workers=20):
    images = download_batch(urls)  # 동시 다운로드

# 2단계: GPU 배치 인코딩 (32개씩)
for batch in chunks(images, 32):
    embeddings = encode_batch(batch)  # 배치 처리
    add_to_index(embeddings)
```

**개선점:**
- ✅ 멀티스레딩으로 다운로드 병렬화
- ✅ GPU 배치 처리로 처리량 증가
- ✅ 재시도 로직으로 안정성 향상
- ✅ 메모리 효율적인 청크 처리

## 🚀 성능 향상

### 예상 속도 개선
- **이전**: ~50-100 영화/분
- **개선 후**: ~500-1000 영화/분 (GPU 기준)
- **속도 향상**: **5-10배**

### 처리 시간 예측
| 영화 수 | 이전 | 개선 후 | 절감 시간 |
|--------|------|---------|----------|
| 10,000 | ~100분 | ~10-20분 | ~80-90분 |
| 50,000 | ~500분 | ~50-100분 | ~400-450분 |
| 80,000 | ~800분 | ~80-160분 | ~640-720분 |

## ⚙️ 설정 가이드

### config.yaml
```yaml
build:
  timeout: 10                # HTTP 요청 타임아웃 (초)
  download_batch_size: 100   # 동시 다운로드할 이미지 수
  encoding_batch_size: 32    # GPU 배치 인코딩 크기
  max_workers: 20            # 다운로드 스레드 수
  max_retries: 3             # 다운로드 재시도 횟수
```

### 환경별 권장 설정

#### 1. 고성능 GPU 서버 (A100, V100)
```yaml
download_batch_size: 200
encoding_batch_size: 64
max_workers: 30
```

#### 2. 중급 GPU (RTX 3090, 4090)
```yaml
download_batch_size: 100
encoding_batch_size: 32
max_workers: 20
```

#### 3. 저사양 GPU (GTX 1080, RTX 2060)
```yaml
download_batch_size: 50
encoding_batch_size: 16
max_workers: 10
```

#### 4. CPU 전용
```yaml
download_batch_size: 50
encoding_batch_size: 8
max_workers: 10
```

## 🔧 사용법

### 기본 실행
```bash
python -m vector_store.create_vector_store
```

### 백그라운드 실행 (권장)
```bash
nohup python -m vector_store.create_vector_store > vector_store.log 2>&1 &
```

### 로그 모니터링
```bash
# 실시간 로그 확인
tail -f vector_store.log

# 진행률 확인
grep "전체 진행" vector_store.log

# 성공률 확인
grep "성공률" vector_store.log
```

### 프로세스 관리
```bash
# 프로세스 확인
ps aux | grep create_vector_store

# 프로세스 종료
pkill -f create_vector_store

# 특정 PID 종료
kill <PID>
```

## 📊 모니터링

### 진행률 표시
```
전체 진행: 45%|████▌     | 36000/80000 [12:30<15:20, 47.8영화/s]
success: 35800, error: 200, success_rate: 99.4%
```

### 로그 출력 예시
```
2025-11-18 10:00:00 - INFO - 배치 크기: 다운로드=100, 인코딩=32
2025-11-18 10:00:00 - INFO - 다운로드 스레드: 20개
2025-11-18 10:15:30 - INFO - 처리 완료: 성공 79,500개, 실패 500개
2025-11-18 10:15:30 - INFO - 성공률: 99.38%
```

## 🐛 트러블슈팅

### 메모리 부족
```yaml
# 배치 크기 줄이기
download_batch_size: 50
encoding_batch_size: 16
```

### GPU 메모리 부족
```yaml
# 인코딩 배치만 줄이기
encoding_batch_size: 8
```

### 네트워크 타임아웃 빈번
```yaml
# 타임아웃 늘리고 재시도 증가
timeout: 30
max_retries: 5
```

### 다운로드 속도 느림
```yaml
# 워커 수 증가
max_workers: 50
```

## 🎯 최적화 팁

1. **GPU 활용도 확인**
   ```bash
   watch -n 1 nvidia-smi
   ```
   - GPU 사용률이 낮으면 `encoding_batch_size` 증가

2. **네트워크 대역폭 확인**
   ```bash
   iftop
   ```
   - 대역폭 여유 있으면 `max_workers` 증가

3. **메모리 사용량 확인**
   ```bash
   htop
   ```
   - 메모리 여유 있으면 `download_batch_size` 증가

4. **디스크 I/O 확인**
   ```bash
   iotop
   ```
   - I/O 병목 시 SSD 사용 권장

## 📝 기술 상세

### 멀티스레딩 다운로드
- `ThreadPoolExecutor` 사용
- I/O bound 작업에 최적화
- GIL 영향 없음

### 배치 인코딩
- PyTorch 배치 처리
- GPU 병렬 연산 활용
- 메모리 효율적 처리

### 재시도 로직
- 지수 백오프 없이 즉시 재시도
- 최대 3회 재시도
- 실패 시 로그 기록

### 메모리 관리
- 청크 단위 처리
- 즉시 인덱스 추가
- 이미지 객체 즉시 해제

## 🔗 관련 파일

- `vector_store/create_vector_store.py`: 메인 스크립트
- `vector_store/config.yaml`: 설정 파일
- `vector_store/README.md`: 사용 가이드
- `modeling/models/clip/models/base.py`: CLIP 인코더

