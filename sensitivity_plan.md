# 민감도 분석 계획

## 목표
현재 모델이 파라미터 변동에 얼마나 민감한지 측정. 결과가 unstable하면 M6/M7 확장은 위험.

## 실험 A: Pruning Probability 민감도

| 변수 | 값 |
|------|-----|
| pruning_probability | 0.3, 0.6, 0.85(default), 1.0 |
| 고정 | n_candidates=200, n_eval_seeds=3 |

측정:
- 각 조건 Top5 목록
- Rank Overlap Ratio (기준 0.85 대비 같은 설계가 Top5에 몇 개나 남는가)
- 1등의 점수 ± std 변화

## 실험 B: Score Weight 민감도

| 변수 | 값 |
|------|-----|
| pruning_weight 상하 | 4.0, 5.0(default), 6.0 |
| soil_loss_weight 상하 | 40.0, 50.0(default), 60.0 |
| 고정 | pruning_prob=0.85, n_candidates=200, n_eval_seeds=3 |

측정: weight 바꿨을 때 Top5 순위 변동

## 실험 C: 재현성

같은 config로 5번 독립 실행 (master seed = 42, 99, 177, 255, 333)

측정:
- 5번 실행 간 Top5 중복도
- 1등 점수의 CV (coefficient of variation)

## 출력

- 실험별 `output/sensitivity/`에 JSON + PNG 저장
- `sensitivity_report.md`로 요약
