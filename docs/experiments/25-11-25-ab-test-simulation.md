# A/B 테스트 LLM 시뮬레이션

## 실험 개요

LLM을 활용하여 영화 추천 시스템의 A/B 테스트를 시뮬레이션했습니다. 두 가지 추천 리스트를 다양한 사용자 컨텍스트에 대해 평가하여 어떤 리스트가 더 선호되는지 분석했습니다.

## 실험 설정

### 추천 리스트 A (System A)

| 영화 ID | 제목 | 연도 | 장르 | 설명 |
|---------|------|------|------|------|
| 1 | Interstellar | 2014 | sci-fi, drama | A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival. |
| 2 | Inception | 2010 | sci-fi, action | A thief who steals corporate secrets through dream-sharing technology is given the task of planting an idea. |
| 3 | The Matrix | 1999 | sci-fi, action | A computer hacker learns about the true nature of his reality and his role in the war against its controllers. |

### 추천 리스트 B (System B)

| 영화 ID | 제목 | 연도 | 장르 | 설명 |
|---------|------|------|------|------|
| 4 | Arrival | 2016 | sci-fi, drama | A linguist works with the military to communicate with alien lifeforms after mysterious spacecraft appear around the world. |
| 5 | Ex Machina | 2014 | sci-fi, thriller | A young programmer is selected to participate in a ground-breaking experiment in synthetic intelligence. |
| 6 | Blade Runner 2049 | 2017 | sci-fi, thriller | A young blade runner's discovery of a long-buried secret leads him to track down former blade runner Rick Deckard. |

## 사용자 컨텍스트

### 1. Sci-Fi 애호가 (sci_fi_context)
- **설명**: "A sci-fi enthusiast who loves mind-bending plots, visual effects, and thought-provoking narratives. Age 25-35."

### 2. 스릴러/다크 테마 선호자 (thriller_dark_context)
- **설명**: "Loves thriller and dark-themed movies, enjoys intense suspense and mysterious atmospheres. Prefers movies with twists and psychological depth. Age 28-40."

## 실험 결과

### 실험 1: Sci-Fi 애호가 사용자

**선호 리스트**: B

**선호 이유**:
List B offers more recent films with visually stunning effects and complex narratives, aligning well with the user's preference for mind-bending plots and high-quality visuals. Blade Runner 2049 and Ex Machina are particularly praised for their thematic depth and technical achievements, while Arrival provides a unique blend of sci-fi and emotional storytelling.

**클릭한 영화 ID**:
- 🎬 List A (System A): `['1', '2', '3']` (모든 영화 클릭)
- 🎬 List B (System B): `['4', '5', '6']` (모든 영화 클릭)

**분석**: 두 리스트 모두 모든 영화를 클릭했지만, System B가 더 최신 영화와 시각적 효과가 뛰어난 작품들을 포함하여 선호되었습니다.

---

### 실험 2: 스릴러/다크 테마 선호자 사용자

**선호 리스트**: B

**선호 이유**:
List B aligns better with the user's preference for psychological thrillers and suspense. Ex Machina and Blade Runner 2049 offer dark atmospheres, mysterious plots, and existential themes, while List A's films lean more toward action/sci-fi with less psychological depth. Arrival lacks the intense suspense required.

**클릭한 영화 ID**:
- 🎬 List A (System A): `['3']` (The Matrix만 클릭)
- 🎬 List B (System B): `['5', '6']` (Ex Machina, Blade Runner 2049 클릭)

**분석**: System B의 Ex Machina와 Blade Runner 2049가 심리적 스릴러와 다크한 분위기를 제공하여 더 높은 선호도를 보였습니다. System A는 액션 중심의 작품들이라 심리적 깊이가 부족하다고 평가되었습니다.

## 결론

두 가지 사용자 컨텍스트 모두에서 **System B가 선호**되었습니다:

1. **Sci-Fi 애호가**: System B의 최신 영화들과 시각적 효과가 뛰어난 작품들이 선호됨
2. **스릴러/다크 선호자**: System B의 심리적 깊이와 다크한 분위기의 작품들이 더 잘 맞음

System B는 더 다양한 장르 조합(sci-fi + thriller)과 최신 작품들을 포함하여 다양한 사용자 선호도에 더 잘 대응하는 것으로 나타났습니다.
