# LLM 기반 추천 평가 모듈

LLM을 활용하여 추천 결과를 평가하고 클릭 여부를 예측하는 모듈입니다.

## 특징

- 🤖 **LLM 기반 평가**: 가상의 사용자 관점에서 추천 결과 평가
- 📊 **클릭 확률 예측**: 각 추천 리스트의 클릭 가능성 추정
- ⚡ **간단한 사용**: 최소한의 코드로 평가 가능
- 🎯 **A/B 테스트 지원**: 두 추천 시스템 비교

## 구조

```
ab_testing/
├── __init__.py          # 메인 export
├── models.py            # 데이터 모델 (Pydantic)
├── config.yaml          # 설정 파일
├── llm/                 # LLM 서브모듈
│   ├── evaluator.py     # LLM 평가기
│   └── prompts.py       # 프롬프트 템플릿
└── README.md            # 문서
```

## 사용법

### 기본 사용법

```python
from ab_testing import LLMEvaluator, MovieRecommendation, RecommendationList, UserContext

# 1. 평가기 초기화
evaluator = LLMEvaluator()

# 2. 사용자 컨텍스트 정의
user_context = UserContext(
    user_description="A sci-fi fan who loves mind-bending plots and visual effects"
)

# 3. 추천 리스트 A
list_a = RecommendationList(
    list_id="A",
    system_name="System A",
    recommendations=[
        MovieRecommendation(
            movie_id="1",
            title="Interstellar",
            year=2014,
            genres=["sci-fi", "drama"],
            description="A team of explorers travel through a wormhole in space"
        ),
        MovieRecommendation(
            movie_id="2",
            title="Inception",
            year=2010,
            genres=["sci-fi", "action"],
            description="A thief who steals secrets through dreams"
        ),
    ]
)

# 4. 추천 리스트 B
list_b = RecommendationList(
    list_id="B",
    system_name="System B",
    recommendations=[
        MovieRecommendation(
            movie_id="3",
            title="Arrival",
            year=2016,
            genres=["sci-fi", "drama"],
            description="A linguist works with aliens to prevent global war"
        ),
        MovieRecommendation(
            movie_id="4",
            title="Ex Machina",
            year=2014,
            genres=["sci-fi", "thriller"],
            description="A programmer evaluates an advanced AI"
        ),
    ]
)

# 5. 평가 실행
result = evaluator.evaluate_lists(user_context, list_a, list_b)

# 6. 결과 확인
print(f"선호 리스트: {result.preferred_list}")
print(f"이유: {result.reasoning}")
print(f"List A 클릭 확률: {result.click_probability_A:.3f}")
print(f"List B 클릭 확률: {result.click_probability_B:.3f}")
```

### 출력 예시

```
선호 리스트: B
이유: List B provides more diverse and thought-provoking sci-fi movies that align better with the user's preference for mind-bending plots.
List A 클릭 확률: 0.650
List B 클릭 확률: 0.850
```

## 커스텀 프롬프트

프롬프트를 커스터마이즈할 수 있습니다:

```python
from ab_testing.llm import EvaluationPrompt

# 커스텀 프롬프트 생성
custom_prompt = EvaluationPrompt.create_custom(
    role="a Korean movie enthusiast who values emotional depth",
    considerations=[
        "Emotional resonance of the films",
        "Cultural relevance",
        "Director and cast quality",
    ],
)

# 커스텀 프롬프트로 평가기 초기화
evaluator = LLMEvaluator(prompt_template=custom_prompt)
```

## 설정

`config.yaml`에서 다음을 설정할 수 있습니다:

- **LLM 설정**: 모델명, temperature, max_tokens 등
- **평가 설정**: 영화 설명 포함 여부, 출력 형식 등

```yaml
llm:
  model_name: "Qwen/Qwen2.5-3B-Instruct"
  temperature: 0.7
  max_new_tokens: 1024

evaluation:
  include_movie_descriptions: true
  output_format: "json"
```

## 평가 결과 구조

`EvaluationResult` 객체에는 다음 정보가 포함됩니다:

- `preferred_list`: 선호하는 리스트 ("A", "B", "none")
- `reasoning`: 선호 이유 (텍스트)
- `click_probability_A`: List A의 클릭 확률 (0.0 ~ 1.0)
- `click_probability_B`: List B의 클릭 확률 (0.0 ~ 1.0)
- `relevance_score_A`: List A의 관련성 점수 (0 ~ 10, 선택)
- `relevance_score_B`: List B의 관련성 점수 (0 ~ 10, 선택)
- `timestamp`: 평가 시각

## 주의사항

- LLM 평가는 실제 사용자와 완벽히 동일하지 않습니다
- 첫 실행 시 모델 로딩에 시간이 소요됩니다
- GPU가 없으면 느릴 수 있습니다

## 라이선스

MIT License
