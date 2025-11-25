# ADR 006: LLM 기반 추천 평가 시스템

**날짜**: 2024-11-25 (업데이트: 2024-11-25)
**상태**: ✅ Accepted  
**결정자**: AI Team  

## 컨텍스트

영화 추천 시스템 개발 과정에서 다음과 같은 문제에 직면했습니다:

1. **초기 단계 검증 어려움**: 실제 사용자 트래픽이 없어 추천 알고리즘의 효과를 검증하기 어려움
2. **A/B 테스트 비용**: 실제 A/B 테스트는 충분한 트래픽과 시간이 필요
3. **빠른 반복 필요**: 여러 알고리즘을 빠르게 비교하고 최적화해야 함
4. **정량적 평가 부재**: Precision, Recall 같은 오프라인 메트릭은 실제 사용자 만족도와 괴리 가능

## 결정

**LLM을 활용하여 추천 결과를 평가하고 클릭 여부를 예측하는 경량 시스템 구축**

### 핵심 아이디어

1. **LLM as Evaluator**: LLM을 가상 사용자 역할로 설정하여 추천 결과를 평가
2. **Click Probability Prediction**: 각 추천 리스트의 클릭 가능성 추정
3. **Simple & Focused**: 복잡한 시뮬레이터 대신 평가 기능에만 집중
4. **Flexible Integration**: 기존 추천 시스템과 쉽게 통합 가능

### 시스템 구성 (단순화)

```
src/ab_testing/
├── models.py              # 데이터 모델 (MovieRecommendation, RecommendationList, EvaluationResult)
├── config.yaml            # LLM 설정
├── llm/
│   ├── evaluator.py       # LLM 평가기
│   └── prompts.py         # 프롬프트 템플릿
├── example.py             # 사용 예제
└── README.md              # 문서
```

### 주요 기능

1. **추천 결과 평가**:
   - 입력: 사용자 컨텍스트, 추천 리스트 A, 추천 리스트 B
   - 출력: 선호 리스트, 이유, 클릭 확률, 관련성 점수

2. **LLM 기반 판단**:
   - 프롬프트: "당신은 X 취향의 사용자입니다. 두 추천 리스트를 평가하세요."
   - JSON 출력: preferred_list, reasoning, click_probability_A/B, relevance_score_A/B

3. **커스텀 프롬프트 지원**:
   - Pydantic 기반 구조화된 프롬프트 시스템
   - 시스템 프롬프트, 평가 기준 등 커스터마이즈 가능

## 사용 예시

### Python API 사용

```python
from ab_testing import LLMEvaluator, MovieRecommendation, RecommendationList, UserContext

# 평가기 초기화
evaluator = LLMEvaluator()

# 사용자 컨텍스트
user_context = UserContext(
    user_description="A sci-fi fan who loves mind-bending plots"
)

# 추천 리스트 A
list_a = RecommendationList(
    list_id="A",
    system_name="System A",
    recommendations=[
        MovieRecommendation(
            movie_id="1",
            title="Interstellar",
            year=2014,
            genres=["sci-fi", "drama"],
            description="A team of explorers travel through a wormhole"
        ),
        # ... more movies
    ]
)

# 추천 리스트 B
list_b = RecommendationList(...)

# 평가 실행
result = evaluator.evaluate_lists(user_context, list_a, list_b)

print(f"선호 리스트: {result.preferred_list}")
print(f"이유: {result.reasoning}")
print(f"List A 클릭 확률: {result.click_probability_A:.3f}")
print(f"List B 클릭 확률: {result.click_probability_B:.3f}")
```

### 예제 실행

```bash
python -m ab_testing.example
```

## 장점

### 1. 단순하고 명확
- 핵심 기능(평가)에만 집중
- 복잡한 시뮬레이터 제거로 유지보수 용이
- 빠른 이해와 사용 가능

### 2. 유연한 통합
- 기존 추천 시스템에 쉽게 추가 가능
- 다양한 평가 시나리오에 활용 가능
- 커스텀 프롬프트로 확장 가능

### 3. 비용 효율적
- 오픈소스 LLM 사용 가능 (Qwen, Llama 등)
- 사용자 확보/유지 비용 없음

### 4. 상세한 인사이트
- LLM의 reasoning을 통해 "왜" 특정 시스템이 선호되는지 파악
- 클릭 확률과 관련성 점수로 정량적 평가

### 5. 포트폴리오 가치
- 혁신적인 평가 방법론
- ML + LLM 융합 역량 입증

## 단점 및 한계

### 1. LLM ≠ 실제 사용자
- LLM의 평가가 실제 사용자와 완전히 일치하지 않을 수 있음
- 특정 편향이 존재 가능 (모델 훈련 데이터 기반)

### 2. 컴퓨팅 리소스
- LLM 실행에 메모리/GPU 필요
- 첫 실행 시 모델 로딩 시간

### 3. 일관성 문제
- Temperature > 0일 때 평가 결과가 매번 다를 수 있음

### 4. 사전 검증 도구
- 최종 의사결정은 실제 사용자 데이터로 해야 함
- "사전 필터" 역할로 활용하는 것이 적절

## 대안

### 1. 오프라인 메트릭만 사용
- **장점**: 빠르고 간단
- **단점**: 실제 만족도와 괴리 가능

### 2. 실제 A/B 테스트만 사용
- **장점**: 가장 정확
- **단점**: 초기에 불가능, 비용 높음

### 3. 크라우드소싱 평가
- **장점**: 실제 사람의 평가
- **단점**: 비용, 시간, 품질 관리 어려움

### 4. 선택한 방법 (LLM 평가)
- **장점**: 빠름, 저렴함, 인사이트 풍부, 간단함
- **단점**: LLM 한계
- **결론**: 초기 검증 + 실제 A/B 테스트 조합이 최적

## 구현 세부사항

### LLM 선택
- **기본**: Qwen/Qwen2.5-3B-Instruct (가볍고 빠름, 한국어 지원)
- **대안**: GPT-4 API (더 정확하지만 비용 발생)

### 프롬프트 엔지니어링

Pydantic 기반 구조화된 프롬프트 시스템:

```python
system_prompt = """
You are an expert movie recommendation evaluator.
Your expertise includes:
- Understanding user preferences and behavior
- Evaluating recommendation quality
- Simulating realistic user responses
"""

user_prompt = f"""
User: {user_description}

List A: {list_a_movies}
List B: {list_b_movies}

Task: Evaluate these two lists from the user's perspective.

Respond in JSON:
{{
    "preferred_list": "A" or "B" or "none",
    "reasoning": "...",
    "click_probability_A": 0.0 to 1.0,
    "click_probability_B": 0.0 to 1.0,
    "relevance_score_A": 0 to 10,
    "relevance_score_B": 0 to 10
}}
"""
```

### 데이터 모델

```python
class MovieRecommendation(BaseModel):
    movie_id: str
    title: str
    year: Optional[int]
    genres: Optional[List[str]]
    description: Optional[str]

class RecommendationList(BaseModel):
    list_id: str
    system_name: str
    recommendations: List[MovieRecommendation]

class EvaluationResult(BaseModel):
    preferred_list: Literal["A", "B", "none"]
    reasoning: str
    click_probability_A: float  # 0.0 ~ 1.0
    click_probability_B: float  # 0.0 ~ 1.0
    relevance_score_A: Optional[float]  # 0 ~ 10
    relevance_score_B: Optional[float]  # 0 ~ 10
```

## 성공 지표

### 단기 (완료)
- ✅ 간단하고 사용하기 쉬운 시스템 구현
- ✅ 예제 및 문서화 완료
- ✅ 커스텀 프롬프트 지원

### 중기 (1-3개월)
- [ ] 실제 추천 시스템과 통합
- [ ] 다양한 시나리오에서 테스트
- [ ] 실제 A/B 테스트 결과와 비교 검증

### 장기 (6개월)
- [ ] 다른 도메인으로 확장 (음악, 음식 등)
- [ ] 오픈소스 프로젝트로 공개
- [ ] 커뮤니티 피드백 및 개선

## 참고 자료

### 관련 연구
- LLM as a Judge (GPT-4 평가 논문)
- Synthetic Data Generation for ML

### 구현 기술
- Pydantic: 데이터 검증 및 프롬프트 구조화
- Transformers: LLM 실행
- PyYAML: 설정 관리

## 의사결정 이력

### 2024-11-25: 초기 구현 완료
- 복잡한 시뮬레이터 구조에서 간단한 평가 모듈로 단순화
- 핵심 기능(평가, 클릭 예측)에만 집중
- 문서화 완료

### 향후 계획
1. 실제 추천 시스템과 통합 (BM25, SVD 등)
2. 다양한 평가 시나리오 테스트
3. 커뮤니티 공유 및 피드백 수집

## 결론

LLM 기반 추천 평가 시스템은 초기 단계의 추천 시스템 개발에 유용한 도구입니다. 복잡한 시뮬레이터 대신 **평가 기능에만 집중**하여 간단하고 사용하기 쉬운 시스템을 구축했습니다.

이 시스템을 통해:
- ✅ 추천 결과를 빠르게 평가
- ✅ 클릭 확률 예측으로 정량적 비교
- ✅ LLM reasoning으로 인사이트 획득
- ✅ 기존 시스템과 쉬운 통합

**권장 사용법**: 
새로운 추천 알고리즘 개발 시 → LLM 평가로 빠른 검증 → 유망한 후보 선택 → 실제 A/B 테스트

---

**Status**: 구현 완료  
**Next Review**: 실제 통합 및 테스트 후

