# Activity Logs

이 디렉토리는 사용자 활동 로그를 저장합니다.

## 파일 구조

- `searches.jsonl` - 검색 이벤트 (자연어 검색, 포스터 검색)
- `clicks.jsonl` - 클릭 이벤트 (IMDb, 구글 검색 등)
- `ratings.jsonl` - 평점 이벤트
- `views.jsonl` - 영화 조회 이벤트
- `recommendations.jsonl` - 추천 이벤트

## 로그 형식

모든 로그는 JSONL (JSON Lines) 형식으로 저장됩니다.

### 검색 로그 예시
```json
{
  "ip": "127.0.0.1",
  "session_id": "uuid",
  "query": "action movie",
  "search_type": "natural_language",
  "result_count": 10,
  "result_movie_ids": ["1", "2", "3"],
  "timestamp": "2025-11-23T18:00:00",
  "activity_type": "search"
}
```

### 클릭 로그 예시
```json
{
  "ip": "127.0.0.1",
  "session_id": "uuid",
  "movie_id": "1",
  "position": 0,
  "search_query": "action movie",
  "link_type": "imdb",
  "timestamp": "2025-11-23T18:01:00",
  "activity_type": "search_result_click"
}
```

## 주의사항

- IP 주소는 개인정보로 분류될 수 있으므로 Git에 커밋하지 마세요
- `.gitignore`에 `*.jsonl` 패턴이 포함되어 있어 자동으로 무시됩니다
