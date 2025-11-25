# LLM 평가 모듈

LLM을 활용하여 추천 결과를 평가하는 핵심 모듈입니다.

## 구성 요소

### 1. LLMEvaluator (`evaluator.py`)

추천 결과를 LLM으로 평가하는 메인 클래스입니다.

**주요 메서드:**
- `evaluate_lists()`: 두 추천 리스트를 평가하고 클릭 확률 예측

**사용 예시:**

```python
from ab_testing import LLMEvaluator, UserContext, RecommendationList

evaluator = LLMEvaluator()

user_context = UserContext(
    user_description="A thriller fan who loves suspenseful plots"
)

result = evaluator.evaluate_lists(user_context, list_a, list_b)
```

### 2. EvaluationPrompt (`prompts.py`)

프롬프트를 구조화하고 관리하는 클래스입니다.

**주요 기능:**
- 시스템 프롬프트 관리
- 사용자 프롬프트 생성
- 출력 형식 정의
- 커스텀 프롬프트 지원

**사용 예시:**

```python
from ab_testing.llm import EvaluationPrompt

# 기본 프롬프트
prompt = EvaluationPrompt.create_default()

# 커스텀 프롬프트
custom_prompt = EvaluationPrompt.create_custom(
    role="a film critic specializing in independent cinema",
    considerations=[
        "Artistic merit and originality",
        "Director's vision and execution",
        "Cultural significance",
    ],
)
```

## 프롬프트 구조

프롬프트는 다음 컴포넌트로 구성됩니다:

1. **SystemPrompt**: LLM의 역할 및 가이드라인
2. **UserProfilePrompt**: 사용자 컨텍스트 설명
3. **RecommendationListPrompt**: 추천 리스트 표시
4. **TaskInstructionPrompt**: 평가 작업 지시
5. **OutputFormatPrompt**: JSON 출력 형식

각 컴포넌트는 독립적으로 커스터마이즈 가능합니다.

## 출력 형식

LLM은 다음 JSON 형식으로 응답합니다:

```json
{
  "preferred_list": "A" | "B" | "none",
  "reasoning": "Detailed explanation...",
  "click_probability_A": 0.0 ~ 1.0,
  "click_probability_B": 0.0 ~ 1.0,
  "relevance_score_A": 0 ~ 10,
  "relevance_score_B": 0 ~ 10
}
```

## 커스터마이징

### 1. LLM 모델 변경

`config.yaml`에서 모델을 변경할 수 있습니다:

```yaml
llm:
  model_name: "your-model-name"
  temperature: 0.7
  max_new_tokens: 1024
```

### 2. 프롬프트 커스터마이징

```python
from ab_testing.llm import EvaluationPrompt, LLMEvaluator

custom_prompt = EvaluationPrompt.create_custom(
    role="your custom role",
    considerations=["consideration 1", "consideration 2"],
    output_schema={
        "custom_field": "your description"
    }
)

evaluator = LLMEvaluator(prompt_template=custom_prompt)
```

### 3. 외부 LLM 사용

```python
from your_llm_module import YourLLM
from ab_testing import LLMEvaluator

your_llm = YourLLM()
evaluator = LLMEvaluator(llm=your_llm)
```

## 주의사항

- LLM 평가는 확률적이므로 같은 입력에 다른 결과가 나올 수 있습니다
- 첫 실행 시 모델 다운로드에 시간이 걸릴 수 있습니다
- GPU 사용을 권장합니다 (CPU는 매우 느림)
