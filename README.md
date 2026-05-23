# GWC Root Simulator — 에어프루닝 팟 최적화

> Garden with Couch (GWC) — 스마트 에어프루닝 화분의 뿌리 성장 최적화 시뮬레이터

---

## 1. 이게 뭐 하는 거야?

**목적:** 에어프루닝 팟 내부의 **에어룸(구멍) 배치**를 최적화해서 뿌리 표면적을 극대화하는 설계를 찾는 시뮬레이터.

**핵심 가정:**
- 뿌리는 아래로 자라면서 중력 방향 + 랜덤 노이즈로 퍼짐
- 에어룸(공기 구멍)에 닿은 뿌리 끝은 죽고(프루닝), 그 자리에서 2~6개의 측근이 폭발적으로 분기
- 분기할수록 전체 뿌리 표면적 증가 → 영양분/수분 흡수 효율 상승
- 이걸 점수(G-Health Score)로 정량화해서 **"이 설계가 얼마나 좋은가"** 를 판단

**왜 2D r-z 단면인가:**
- 3D는 격자 수 24배 증가 → 탐색 속도 24배 느림
- 회전 대칭 화분(원통형)이라 2D 단면으로도 충분히 정확
- 3D 전환은 코드 구조 유지하면서 가능 (확장 예정)

---

## 2. 입력 — 뭘 정해야 하는가?

### 2.1 설정 파일: `configs/mvp.json`

모든 파라미터가 여기 있음. JSON 수정만으로 동작 변경 가능.

| 항목 | 예시 | 설명 |
|------|------|------|
| `pot.radius_cm` | 12.0 | 화분 반경 (cm) |
| `pot.height_cm` | 20.0 | 화분 높이 (cm) |
| `soil.mix` | 배양토 60%, 펄라이트 40% | 흙 배합 비율 |
| `airroom.max_count` | 10 | 에어룸 최대 개수 |
| `airroom.radius_range_cm` | [0.8, 1.5] | 에어룸 반경 범위 |
| `root.initial_roots` | 3 | 처음 시작하는 뿌리 개수 |
| `root.max_generation` | 3 | 뿌리 세대 수 |
| `root.pruning_probability` | 0.4 | 프루닝 발생 확률 |
| `root.branches_per_pruning` | [2, 6] | 프루닝당 새 뿌리 개수 범위 |
| `tropism.g` | 1.0 | 중력 방향 편향 세기 |
| `search.method` | "random" / "ga" | 탐색 방식 |
| `search.n_candidates` | 200 | 랜덤 탐색 후보 수 |
| `search.n_eval_seeds` | 3 | 설계당 평가 시드 수 (높을수록 정확하지만 느림) |
| `ga.population` | 20 | GA 개체 수 |
| `ga.generations` | 10 | GA 세대 수 |

### 2.2 식물 종 프로필: `configs/species/`

| 파일 | 특징 |
|------|------|
| `monstera.json` | 왕성한 성장. initial_roots=4, 4세대, 노이즈 낮음 |
| `ficus.json` | 균형형. initial_roots=3, 3세대 |
| `cactus.json` | 느린 성장. initial_roots=2, 3세대, 노이즈 높음 |

사용법: mvp.json 통째로 종 프로필로 교체.
```
# mvp.json 대신 monstera.json 로드
SimConfig.from_json("configs/species/monstera.json")
```

### 2.3 뿌리 세대별 파라미터

뿌리는 세대가 내려갈수록 가늘어지고 더 휘어짐:

| 세대 | 반경(cm) | 노이즈(°) | 최대각도(°) | 분기각(°) | 최대수명(step) |
|------|---------|-----------|------------|----------|--------------|
| 1차 (primary) | 0.18 | 8.0 | 40 | 0 (직하) | 200 |
| 2차 (secondary) | 0.10 | 15.0 | 80 | ±75 | 200 |
| 3차 (tertiary) | 0.04 | 25.0 | 85 | ±85 | 150 |

---

## 3. 출력 — 뭐가 나오는가?

### 3.1 G-Health Score (점수)

```
Score = 1.0 × 표면적(mm²) + 50.0 × 프루닝_횟수 - 200.0 × 흙손실률
```

| 구성요소 | 의미 | 높을수록 |
|---------|------|---------|
| 표면적 | 전체 뿌리 표면적 합계 | 영양분/수분 흡수 효율 ↑ |
| 프루닝 횟수 | 에어프루닝 발생 횟수 | 분기 활성도 ↑ |
| 흙손실률 | 루트존 이탈 흙 비율 | 낮을수록 좋음 |
| Spread Ratio | 뿌리가 화분 전체에 퍼진 정도 | 균일한 분포 (점수 미반영) |

### 3.2 시각화: `output/*.png`

- **단면도**: r-z 평면에 뿌리 경로 + 에어룸 표시
- **프루닝 분포**: 상/중/하 프루닝 발생 위치 히스토그램
- **Top5 막대그래프**: 상위 5개 설계 점수 비교 + 에어룸 개수/표면적 표시
- **정보 박스**: 점수 구성요소 + Spread Ratio

### 3.3 JSON 결과: `output/results_*.json`

탐색 완료 후 `save_results()`로 저장:
```json
{
  "timestamp": "2026-05-23T...",
  "config_method": "random",
  "results": [
    {
      "rank": 1,
      "mean_score": 12856,
      "std_score": 2142,
      "all_scores": [11011, 15859, 11699],
      "surface_area_mm2": 9907,
      "pruning_count": 36,
      "spread_ratio": 0.22,
      "airroom_positions": [
        {"r_cm": 3.2, "z_cm": 12.5, "radius_cm": 1.2},
        ...
      ]
    }
  ]
}
```

---

## 4. 어떻게 실행하는가?

### 4.1 빠른 시작

```python
# 1. 설정 로드
from src.config import SimConfig
from src.search import run_search, save_results

cfg = SimConfig.from_json("configs/mvp.json")

# 2. 탐색 실행 (200개 후보, 각 3개 시드)
cfg.search.n_candidates = 200
cfg.search.n_eval_seeds = 3
top5 = run_search(cfg)

# 3. 결과 출력
from src.search import RandomSearch
print(RandomSearch.format_top5(top5))

# 4. 결과 저장
save_results(top5, cfg, "output/results_20240523.json")
```

### 4.2 GA로 최적화

```python
cfg.search.method = "ga"
cfg.ga.population = 30
cfg.ga.generations = 20
top5 = run_search(cfg)
```

### 4.3 시각화

```python
from src.viz import plot_search_results
fig = plot_search_results(top5, save_path="output/top5_viz.png")
```

### 4.4 테스트 한 방에 실행

```powershell
python experiments/test_m4m5.py    # M4+M5 전체 검증
python experiments/test_ga.py       # GA 검증
```

---

## 5. 결과 해석 — 뭘 봐야 하는가?

```
#1: Mean=12856±2142  Airrooms=6  Surface=9907mm2  Pruning=36  Spread=22%
#2: Mean=12605±3124  Airrooms=1  Surface=9596mm2  Pruning=5   Spread=20%
```

| 지표 | 판단 기준 |
|------|----------|
| **Mean** | 설계의 기대 성능. 높을수록 좋음 |
| **±Std** | 일관성. 낮을수록 뿌리 성장 패턴에 덜 민감 (=견실한 설계) |
| **Airrooms** | 최적 에어룸 개수. 너무 많아도 뿌리 공간 부족 |
| **Surface** | 클수록 좋음. 단, 흙손실과 트레이드오프 |
| **Pruning** | 적절한 프루닝 횟수 (100+는 너무 많음) |
| **Spread** | 높을수록 화분 전체에 고르게 퍼짐 |

**설계 선택 기준:**
1. Mean이 높고 Std가 낮은 설계가 최우선
2. Airrooms 개수는 4~8개가 적절 (너무 적으면 프루닝 부족, 너무 많으면 뿌리 공간 부족)
3. Spread Ratio 30%+면 공간 활용 우수

---

## 6. 실전 워크플로우

```
Phase A — 탐색 (랜덤 200개 or GA 20개체×10세대)
    ↓
Phase B — Top5 상세 분석 (점수 구성요소 + 시각화 검토)
    ↓
Phase C — 3D 변환 후 재검증 (선택사항, 준비 중)
    ↓
Phase D — Fusion 360 모델링 (경주)
    ↓
Phase E — 프로토타입 제작
```

**Fusion 360 / SimScale 연동:**
- 우리 시뮬이 "어디에 에어룸을 배치할지" 설계 도출
- Fusion 360에서 3D 모델링 (STL 출력)
- SimScale에서 CFD 검증 ("공기 흐름이 설계대로 가는가?")
- IR 자료에는 우리 시뮬 결과(점수/비교/시각화)만으로도 충분

---

## 7. 파라미터 튜닝 가이드

| 바꾸고 싶은 것 | 수정할 파일 | 필드 |
|---------------|-----------|------|
| 화분 크기 | mvp.json | `pot.radius_cm`, `pot.height_cm` |
| 에어룸 개수 | mvp.json | `airroom.max_count` |
| 뿌리 왕성함 | species/`종`.json | `initial_roots`, `noise_deg`, `max_angle_deg` |
| 프루닝 빈도 | mvp.json | `pruning_probability` (0~1) |
| 점수 기준 | mvp.json | `score.pruning_weight`, `score.soil_loss_weight` |
| 탐색 정밀도 | mvp.json | `search.n_eval_seeds`, `search.n_candidates` |
| GA 집중도 | mvp.json | `ga.population`, `ga.generations` |
| 뿌리 굵기 | mvp.json | `root.radii_cm` |
| 성장 방향 | mvp.json | `tropism.g` (중력), `tropism.h` (수분, M6+) |

---

## 8. 주의사항

**1. 단일 시드 점수는 믿지 마세요.** 3개 이상 시드 평균을 써야 우연히 잘 나온 설계를 걸러냅니다. `n_eval_seeds=3` 기본값 유지 권장.

**2. 2D 단면의 한계:** 2D r-z 단면은 회전 대칭을 가정합니다. 실제 3D에서는 원주 방향 엉킴이나 층류 편차가 발생할 수 있습니다. 최종 검증은 3D로 해야 합니다.

**3. 생물학적 단순화:**
- 에틸렌 호르몬 모델 미적용 (설계 비교 능력 0% 개선)
- 자원 확산/흡수 미적용 (M6/M7에서 추가 예정)
- 실제 뿌리는 환경에 더 복잡하게 반응

**4. 적정 탐색 범위:**
- 200개 후보 × 3시드 = 600회 실행 → ~5분 소요
- 500개 후보 × 5시드 = 2,500회 실행 → ~20분 소요
- 너무 많이 돌리면 시간 대비 효율 감소

**5. GA vs 랜덤 서치:**
- GA는 적은 평가로도 꾸준히 좋은 설계를 찾음 (수렴성 ↑)
- 랜덤 서치는 운 좋게 최고점을 찾을 수도 있지만 일관성 ↓
- 실전 = GA 추천. 초기 아이디어 탐색 = 랜덤 추천.

**6. config 수정 후 검증:**
```python
cfg = SimConfig.from_json("configs/mvp.json")
errors = cfg.validate()
if errors:
    print("설정 오류:", errors)  # 절대 무시하지 말 것
```

---

## 9. 파일 구조

```
gwc-root-sim/
├── configs/
│   ├── mvp.json              # 메인 설정
│   └── species/
│       ├── monstera.json     # 몬스테라 프로필
│       ├── ficus.json        # 피쿠스 프로필
│       └── cactus.json       # 선인장 프로필
├── src/
│   ├── config.py             # 설정 로드/검증
│   ├── grid.py               # 복셀 격자 (2D r-z)
│   ├── geometry.py           # 에어룸 형상
│   ├── root.py               # 뿌리 성장 + 프루닝
│   ├── score.py              # G-Health Score
│   ├── viz.py                # 시각화 (matplotlib)
│   ├── pipeline.py           # 실행 오케스트레이션
│   ├── ga.py                 # 유전 알고리즘
│   └── search.py             # 탐색 (랜덤/GA) + 결과 저장
├── experiments/
│   ├── test_m4m5.py          # 통합 검증
│   ├── test_ga.py            # GA 검증
│   ├── test_root.py          # 뿌리 성장 검증
│   ├── test_m3.py            # 점수/시각화 검증
│   └── baseline_2d.py        # 격자/에어룸 검증
├── output/                   # 시각화 PNG + JSON 결과
│   ├── search_top5_viz.png
│   └── results_*.json
└── plan.md                   # 설계 문서 (참고용)
```

---

## 10. 용어 설명

| 용어 | 뜻 |
|------|-----|
| **에어프루닝** | 뿌리 끝이 공기에 닿아 세포 사멸 → 측근 분기 유도 |
| **에어룸** | 화분 벽면의 공기 구멍, 프루닝 발생 지점 |
| **r-z 단면** | 원통 화분의 반경-높이 2D 단면 |
| **복셀** | 3D 픽셀, 격자 단위 (0.5cm³) |
| **G-Health Score** | 뿌리 건강도를 수치화한 점수 |
| **Spread Ratio** | 방문한 복셀 수 / 전체 흙 복셀 수 |
| **시드(seed)** | 난수 시작값. 같은 시드 = 같은 결과 (재현성) |
| **Monte Carlo** | 여러 시드로 반복 실행 → 평균 내는 방식 |
| **세대(generation)** | 뿌리 분기 깊이 (1차→2차→3차) |
| **σ√dx 스케일링** | step_size 무관 일관된 궤적 보장 |

---

## 11. 빠른 명령어 모음

```powershell
# 1회 실행
python -c "from src.pipeline import SimPipeline; from src.config import SimConfig; p=SimPipeline(SimConfig.from_json('configs/mvp.json')); r=p.run(seed=42); print(r['score'])"

# 50개 탐색 + 결과 저장
python -c "
from src.config import SimConfig
from src.search import run_search, save_results
cfg = SimConfig.from_json('configs/mvp.json')
cfg.search.n_candidates = 50
top5 = run_search(cfg)
print(cfg.search.method, 'done')
save_results(top5, cfg, 'output/results_quick.json')
"

# GA 20개체 × 10세대
python -c "
cfg = SimConfig.from_json('configs/mvp.json')
cfg.search.method = 'ga'
top5 = run_search(cfg)
from src.search import RandomSearch
print(RandomSearch.format_top5(top5))
"

# 모든 검증 실행
python experiments/test_m4m5.py
python experiments/test_ga.py
```
