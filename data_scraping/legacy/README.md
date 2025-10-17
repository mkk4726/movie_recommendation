# Legacy Code

이 디렉토리는 리팩토링 이전의 원본 코드를 보관합니다.

## 포함된 파일

- `movie_info.py` - 영화 정보 스크래핑 (구버전)
- `movie_comments.py` - 영화 코멘트 스크래핑 (구버전)
- `custom_movie_rating.py` - 사용자 평점 스크래핑 (구버전)
- `clean_movie_info.py` - 데이터 정제 스크립트
- `test.py` - 테스트 스크립트

## 주의사항

이 파일들은 더 이상 사용되지 않으며, 참고 목적으로만 보관됩니다.

새로운 코드는 상위 디렉토리의 리팩토링된 구조를 사용하세요:
- `scrapers/` - 스크래퍼 클래스
- `common/` - 공통 유틸리티
- `run_*.py` - 실행 스크립트

자세한 내용은 상위 디렉토리의 README.md를 참조하세요.

