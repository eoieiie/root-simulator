# GWC Root Simulator — 에어프루닝 팟 최적화

> Garden with Couch (GWC) — 스마트 에어프루닝 화분의 뿌리 성장 최적화 시뮬레이터

---

## 목차

- [1. 프로젝트 개요](#1-프로젝트-개요)
- [2. 시작하기](#2-시작하기)
  - [2.1 빠른 시작](#21-빠른-시작)
  - [2.2 GA로 최적화](#22-ga로-최적화)
  - [2.3 시각화](#23-시각화)
- [3. 설정 — 뭘 정해야 하는가?](#3-설정--뭘-정해야-하는가)
  - [3.1 설정 파일](#31-설정-파일)
  - [3.2 식물 종 프로필](#32-식물-종-프로필)
  - [3.3 뿌리 세대별 파라미터](#33-뿌리-세대별-파라미터)
- [4. 출력 — 뭐가 나오는가?](#4-출력--뭐가-나오는가)
  - [4.1 G-Health Score (점수)](#41-g-health-score-점수)
  - [4.2 추가 메트릭](#42-추가-메트릭)
  - [4.3 시각화](#43-시각화)
  - [4.4 JSON 결과](#44-json-결과)
- [5. 시뮬레이션 동작 원리](#5-시뮬레이션-동작-원리)
  - [5.1 전체 파이프라인](#51-전체-파이프라인)
  - [5.2 Phase A: 격자 + 에어룸](#52-phase-a-격자--에어룸)
  - [5.3 Phase B: 자원 확산 (CA)](#53-phase-b-자원-확산-ca)
  - [5.4 Phase B: 뿌리 성장 + 프루닝](#54-phase-b-뿌리-성장--프루닝)
  - [5.5 Phase C: G-Health Score 계산](#55-phase-c-g-health-score-계산)
  - [5.6 Phase D: 탐색 (유전 알고리즘)](#56-phase-d-탐색-유전-알고리즘)
- [6. 시각화 이미지 해설](#6-시각화-이미지-해설)
  - [6.1 2D 6패널 (IR 주력)](#61-2d-6패널-ir-주력)
  - [6.2 3D 6패널 (홍보용)](#62-3d-6패널-홍보용)
  - [6.3 2패널 단면도](#63-2패널-단면도)
  - [6.4 에어룸 배치도](#64-에어룸-배치도)
- [7. 모든 메트릭 사전](#7-모든-메트릭-사전)
- [8. 결과 해석 — 뭘 봐야 하는가?](#8-결과-해석--뭘-봐야-하는가)
  - [8.1 기본 판단 기준](#81-기본-판단-기준)
  - [8.2 상세 판단 기준](#82-상세-판단-기준)
- [9. 실험 결과 요약 — 13cm 화분](#9-실험-결과-요약--13cm-화분)
- [10. 파라미터 튜닝 가이드](#10-파라미터-튜닝-가이드)
- [11. 실전 워크플로우](#11-실전-워크플로우)
- [12. 주의사항](#12-주의사항)
- [13. 파일 구조](#13-파일-구조)
- [14. 용어 설명](#14-용어-설명)
- [15. 학술 출처 및 근거](#15-학술-출처-및-근거)
- [16. 빠른 명령어 모음](#16-빠른-명령어-모음)

---

## 1. 프로젝트 개요

**최종 목표:**

```
에어룸 배치를 최적화해서 → 식물이 필요한 양분 임계값을 넘게 만든다.
```

이 목표는 세 가지가 순차적으로 연결되어 달성된다:

```
① 프루닝 횟수  →  ② 뿌리 표면적  →  ③ 양분 흡수량
(분기 유발)     (흡수 표면 확보)   (실제 흡수 = 임계값 돌파)
```

- **프루닝이 많아야** → 측근이 많이 분기하고
- **표면적이 커야** → 영양분/수분을 흡수할 면이 많아지고
- **양분 흡수량이 임계값을 넘어야** → 식물이 실제로 잘 자란다

> ✅ **모든 메커니즘 구현 완료:**
> - ① 프루닝: 에어룸 접촉 → 뿌리 끝 사멸 → 2~6개 측근 분기
> - ② 표면적: 3세대 뿌리 + allometric radius로 정밀 계산
> - ③ 양분흡수: 자원 확산(CA) + Michaelis-Menten 흡수
>
> **최종 Score = S×1.0 + P×50 - L×1000 + N×2000**
>
> 최적화 결과: 13cm 화분 최적 에어룸 배치 도출 완료 (`RESULTS.md` 참고)

**핵심 가정:**

- 뿌리는 아래로 자라면서 중력 방향 + 랜덤 노이즈로 퍼짐
- 에어룸(공기 구멍)에 닿은 뿌리 끝은 죽고(프루닝), 그 자리에서 2~6개의 측근이 분기
- 분기할수록 전체 뿌리 표면적 증가 → 영양분/수분 흡수 효율 상승
- 이걸 점수(G-Health Score)로 정량화해서 **"이 설계가 기존 샅태보다 얼마나 좋은가 "** 를 판단

**왜 2D r-z 단면인가:**

- 3D는 격자 수 24배 증가 → 탐색 속도 24배 느림
- 회전 대칭 화분(원통형)이라 2D 단면으로도 충분히 정확
- 3D 전환은 코드 구조 유지하면서 가능 (확장 예정)
- 나온 배치의 결과 토대로 3d시각화

---

## 2. 시작하기

### 2.1 빠른 시작

```python
from src.config import SimConfig
from src.search import run_search, save_results

# 설정 로드
cfg = SimConfig.from_json("configs/mvp.json")

# 탐색 실행 (200개 후보, 각 3개 시드)
cfg.search.n_candidates = 200
cfg.search.n_eval_seeds = 3
top5 = run_search(cfg)

# 결과 출력
from src.search import RandomSearch
print(RandomSearch.format_top5(top5))

# 결과 저장
save_results(top5, cfg, "output/results_20240523.json")
```

### 2.2 GA로 최적화

```python
cfg.search.method = "ga"
cfg.ga.population = 30
cfg.ga.generations = 20
top5 = run_search(cfg)
```

### 2.3 시각화

```python
from src.viz import plot_search_results
fig = plot_search_results(top5, save_path="output/top5_viz.png")
```

### 테스트 한 방에 실행

```powershell
python experiments\test_m4m5.py   # 프루닝 + 표면적 검증
python experiments\test_ga.py      # GA 검증
```

---

## 3. 설정 — 뭘 정해야 하는가?

### 3.1 설정 파일: `configs/mvp.json`

모든 파라미터는 JSON 수정만으로 동작 변경 가능.

| 항목 | 현재값 (V3) | 설명 |
|------|-----------|------|
| `pot.radius_cm` | 12.0 | 화분 반경 (cm). 13cm 제품용: `configs/pot_13.json` |
| `pot.height_cm` | 20.0 | 화분 높이 (cm). 13cm 제품용: `configs/pot_13.json` |
| `pot.voxel_size_cm` | 0.3 | 복셀 해상도 (cm/칸) |
| `soil.mix` | 배양토 100% | 흙 배합 비율 |
| `airroom.max_count` | 10 | 에어룸 최대 개수 |
| `airroom.radius_range_cm` | [0.8, 1.5] | 에어룸 반경 범위 (cm) |
| `root.initial_roots` | 3 | 처음 시작하는 뿌리 개수 |
| `root.max_generation` | 3 | 뿌리 세대 수 (1차→2차→3차) |
| `root.pruning_probability` | 1.0 | 프루닝 확률 (**생물학적 근거: 공기프루닝은 확정적 과정**) |
| `root.branches_per_pruning` | [2, 6] | 프루닝당 새 뿌리 개수 범위 |
| `root.step_size_cm` | 0.25 | 1스텝 전진 거리 (cm) |
| `root.noise_deg` | **[8.0, 15.0, 25.0]** | 세대별 방향 랜덤성 (°). **V3에서 4→8°로 증가 (실험 최적값, 일반적인 뿌리의 성장성을 고려)** |
| `root.max_angle_deg` | [20.0, 80.0, 85.0] | 세대별 최대 휘어짐 각도(근거없음 주의) (°) |
| `tropism.g` | **1.0** | 중력 편향 세기.  (실험 최적값) |
| `score.surface_area_weight` | 1.0 | 표면적 가중치 |
| `score.pruning_weight` | 50.0 | 프루닝 횟수 가중치 |
| `score.soil_loss_weight` | 1000.0 | 흙손실 패널티 가중치 |
| `score.uptake_weight` | 2000.0 | 양분흡수량 가중치 |
| `search.method` | "ga" | 탐색 방식 (GA 권장) |
| `search.n_candidates` | 200 | (random 시) 후보 수 |
| `search.n_eval_seeds` | 5 | 설계당 평가 시드 수 (10~15 권장) |
| `ga.population` | **25** | GA 개체 수 (30→25: 실험 최적값) |
| `ga.generations` | 15 | GA 세대 수 |
| `ga.elite_frac` | **0.15** | 엘리트 비율 (0.2→0.15: 다양성 ↑) |
| `ga.mutation_sigma_cm` | **0.8** | 변이 표준편차 (cm). (1.5→0.8: 세밀한 탐색) |

### 3.2 식물 종 프로필: `configs/species/`

| 파일 | 특징 |
|------|------|
| `monstera.json` | 왕성한 성장. initial_roots=4, 4세대, 노이즈 낮음 |
| `ficus.json` | 균형형. initial_roots=3, 3세대 |
| `cactus.json` | 느린 성장. initial_roots=2, 3세대, 노이즈 높음 |

사용법: mvp.json 통째로 종 프로필로 교체.

```python
# mvp.json 대신 monstera.json 로드
SimConfig.from_json("configs/species/monstera.json")
```

### 3.3 뿌리 세대별 파라미터

뿌리는 세대가 내려갈수록 가늘어지고 더 휘어짐:

| 세대 | 반경(cm) | 노이즈(°) | 최대각도(°) | 분기각(°) | 최대수명(step) | 흡수효율 |
|------|---------|-----------|------------|----------|--------------|---------|
| 1차 (primary) | 0.18 | **4.0** | **20** | 0 (직하) | 200 | **0.1×** (수송) |
| 2차 (secondary) | 0.0525\* | 15.0 | 80 | ±75 | 200 | **0.5×** (혼합) |
| 3차 (tertiary) | 0.0325\* | 25.0 | 85 | ±85 | 150 | **1.0×** (흡수) |

> \* 반경은 Pagès (2014) allometric 공식으로 계산: `r_child = 0.01 + 0.25 × (r_parent - 0.01)`.
>   slope=0.25는 45종 쌍떡잎식물 평균 (범위 0.14~0.36).
>
> 흡수효율: Guo et al. (2008) 23수종 분석 기준. 1차근=수송위주, 3차근=주흡수.

---

## 4. 출력 — 뭐가 나오는가?

### 4.1 G-Health Score (점수) — v3 (양분 흡수 반영)

```
Score = S × 1.0 + P × 50.0 - L × 1000.0 + N × 2000.0
```

| 기호 | 의미 | 계산식 | 단위 | 일반적 범위 |
|------|------|--------|------|-----------|
| **S** | 전체 뿌리 표면적 | Σ(2π × r_i × L_i) × 100 | mm² | 3000~12000 |
| **P** | 프루닝 총 횟수 | 단순 카운트 | 회 | 0~100 |
| **L** | 흙손실률 (체적비) | Σ(πR_j²) / (2 × R_pot × H_pot) | 비율 (0~1) | 0.01~0.15 |
| **N** | 질소 흡수량 | Σ(S_i × Eff_i × Vmax × C / (Km + C)) | mg | 0.1~1.0 |

**S (표면적):**

```
각 뿌리 조각을 원통으로 근사:
  A_i = 2 × π × r_i × L_i     (cm²)
  π = 3.14159...
  r_i = i번째 뿌리 조각의 반경 (cm)
        gen1=0.18cm, gen2~0.05cm, gen3~0.03cm
  L_i = i번째 뿌리 조각의 길이 (cm)

전체:
  S_cm2 = A_1 + A_2 + ... + A_N    (모든 조각 합산)
  S = S_cm2 × 100                   (cm² → mm²)
  
예: gen3 뿌리 150개, 각각 길이 3cm, 반경 0.03cm
  한 개: 2 × 3.14 × 0.03 × 3 = 0.565 cm²
  150개: 84.8 cm² = 8480 mm²
```

**P (프루닝 횟수):**

```
뿌리 끝이 에어룸 영향권에 진입 → pruning_probability(1.0) 검사 → 성공 시 카운트+1

프루닝 점수 근거 (학술):
  - Platycladus orientalis (PLOS ONE 2018): 프루닝 72h 후 측근 6배 증가
  - Reid et al. (1998) Arabidopsis 뿌리절단: 측근 밀도 유의미 증가 (P=0.001)
  - YUC9-mediated auxin (2018): 절단 부위 옥신 축적 → 측근 형성 (분자 메커니즘)
```

**L (흙손실률):**

```
각 에어룸의 단면적 합 / 화분 단면적:
  L = (π × R_1² + π × R_2² + ... + π × R_N²) / (2 × R_pot × H_pot)
  
  R_j = j번째 에어룸의 반경 (cm)
  R_pot = 화분 반경 = 12cm
  H_pot = 화분 높이 = 20cm
  화분 단면적: 2 × 12 × 20 = 480 cm²

예: 반경 1cm 에어룸 10개
  에어룸 총 면적: 10 × 3.14 × 1² = 31.4 cm²
  L = 31.4 / 480 = 0.065 (6.5%)
```

**점수 계산 예시 (실제 최종 설계, V3):**

```
S 기여: 4657 × 1.0   = +4657   (표면적)
P 기여: 50 × 50.0    = +2500   (프루닝)
L 패널티: -0.056 × 1000 = -56  (흙손실)
N 기여: 0.26 × 2000  = +520   (질소 흡수)
Score = 4657 + 2500 - 56 + 520 = 7621 (시드 1개 기준)

※ 15개 시드 평균 = 6861 ± 823 (시드에 따라 점수 변동)
```

### 4.2 추가 메트릭

| 메트릭 | 의미 | 계산식 | 근거 |
|-------|------|--------|------|
| Spread Ratio | 뿌리 퍼짐 정도 | 방문복셀/전체흙복셀 | 공간 활용도 |
| N Uptake | 질소 흡수량 | Σ세그먼트(면적×효율×MM(C_local)) | Michaelis-Menten |
| Pruning by Zone | 상/중/하 프루닝 분포 | z축 3등분 카운트 | 깊이별 프루닝 편향 |

**양분 흡수 활성화 시:**

```
Michaelis-Menten 모델:
  Uptake_i = S_i × Eff(gen) × Vmax × C_local / (Km + C_local)
  
  Vmax = 0.001 mg/mm²/day, Km = 0.05 mg/cm³
  C_local = 국소 양분 농도 (CA 확산 결과)

비활성화 시 → n_uptake_mg = 0.0
```

### 4.3 시각화

`output/` 디렉토리에 PNG 파일로 저장됨:

- **단면도**: r-z 평면에 뿌리 경로 + 에어룸 표시
- **프루닝 분포**: 상/중/하 프루닝 발생 위치 히스토그램
- **Top5 막대그래프**: 상위 5개 설계 점수 비교 + 에어룸 개수/표면적 표시
- **정보 박스**: 점수 구성요소 + Spread Ratio

> 각 이미지에 대한 상세 해설은 [6장 시각화 이미지 해설](#6-시각화-이미지-해설) 참고.

### 4.4 JSON 결과

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
        {"r_cm": 3.2, "z_cm": 12.5, "radius_cm": 1.2}
      ]
    }
  ]
}
```

---

## 5. 시뮬레이션 동작 원리

### 5.1 전체 파이프라인

```
pot_13.json (설정 파일)
     ↓
SimConfig.from_json()   ← 모든 파라미터 로드
     ↓
SimPipeline.run(seed=42, airrooms_override=[...])
     ├── Phase A: VoxelGrid 생성 + 에어룸 배치
     ├── Phase B (자원 확산): CA로 water/nutrient map 생성
     ├── Phase B (뿌리 성장): RootSystem.run() — 성장 + 프루닝
     ├── Phase C: compute_score() — G-Health Score 계산
     └── Phase E: plot_single_run() — 시각화 (옵션)
     ↓
return {grid, root_system, airrooms, score}
```

GA 탐색은 이 `SimPipeline.run()`을 **개체 수 × 세대 수 × 평가 시드 수** 만큼 반복:

```
GA: 25개체 × 15세대 × 5시드 = 1,875회 실행
    각 실행마다 위 파이프라인 전부 수행
```

### 5.2 Phase A: 격자 + 에어룸

**VoxelGrid 생성:**

```
nr = ceil(pot_radius / voxel_size_cm)     # 반경 방향 셀 수
nz = ceil(pot_height / voxel_size_cm)     # 높이 방향 셀 수
```

- pot_13.json 기준: `nr=33`, `nz=75`, 총 **2,475개** 복셀
- 각 복셀은 `soil_type` (배양토/펄라이트/에어룸 등), `water_map`, `nutrient_map`, `root_visits` 배열을 가짐

**에어룸 배치:**

- 2D r-z 평면에서 원형으로 표현
- 각 에어룸은 `(r, z, radius)`로 정의
- **영향권 반경** (pruning zone) = `radius × 1.15` — 뿌리가 이 영역에 진입하면 프루닝 발생
- 배치 시 화분 벽면/바닥에서 1cm 마진, 에어룸끼리 최소 간격 유지

**흙손실률 계산:**

```
L = Σ(π × R_j²) / (2 × R_pot × H_pot)

예: 6개 에어룸, 각 반경 0.5~0.9cm
  L ≈ 0.049 (4.9%)
```

### 5.3 Phase B: 자원 확산 (CA)

Cellular Automata 방식으로 물과 양분이 확산됨. 뿌리 성장 **전에** 실행되어 안정적인 농도장 형성.

**초기 조건:** 모든 흙 복셀 = `initial_water_content` (0.8), 에어룸 복셀 = 0.

**매 반복(최대 100회):**

1. **중력**: 물이 아래로 이동 (gravity_bias × 0.2)
2. **확산**: 4방향 이웃으로 확산 (diffusion_rate × 0.25)
3. **증발**: 표면 복셀에서 증발 (evaporation_rate × 0.02)
4. **배수**: 바닥 복셀에서 5% 손실
5. **에어룸 장벽**: 에어룸 복셀은 항상 0으로 유지

**양분 농도:** `nutrient_map = water_map × 0.05 + depth_bonus × 0.05`

- 깊이에 따라 표면 쪽에 양분 가중치 추가 (표면 +0.3, 바닥 0.0)

### 5.4 Phase B: 뿌리 성장 + 프루닝

**초기화:**

- `initial_roots`(3개) 뿌리를 화분 상단(z=height)에서 시작
- 각 뿌리는 gen1, 반경 0.18cm, 아래 방향(angle=0)으로 설정

**1스텝 성장 과정:**

```
1. 각도 갱신:  angle ×= (1.0 - g × 0.02)  ← 중력이 아래로 당김
              angle += 노이즈 (±noise_deg)
              angle = clamp(-max_angle, +max_angle)

2. 전진:      dr = step_size × sin(angle)
              dz = -step_size × cos(angle)
              new_r = end_r + dr
              new_z = end_z + dz

3. 경계 처리: 벽면 반사, 바닥/천장 충돌 시 사멸

4. 수명 확인: max_lifestyle 초과 시 자연사

5. 프루닝 검사: 에어룸 영향권 진입 → 프루닝!
```

**프루닝 발생 시:**

```
1. 현재 뿌리 끝 사멸 (active = False)
2. 프루닝 위치 기록: (r, z, generation)
3. 2~6개 측근 분기:
   - 자식 세대 = 부모 세대 + 1
   - 자식 반경 = 0.01 + 0.85 × (부모_반경 - 0.01)
   - 분기각: gen1→gen2: ±75°, gen2→gen3: ±85°
4. 분기한 측근이 각자 새로운 뿌리로 성장
```

**세대별 특성:**

| 세대 | 역할 | 흡수 효율 | 굵기 | 움직임 |
|------|------|-----------|------|--------|
| 1차 (primary) | 수송 담당 | 10% | 두꺼움 (0.18cm) | 곧게 아래로 |
| 2차 (secondary) | 혼합 | 50% | 중간 (~0.05cm) | 옆으로 퍼짐 |
| 3차 (tertiary) | 흡수 담당 | 100% | 가냊 (~0.03cm) | 자유분방 |

### 5.5 Phase C: G-Health Score 계산

```
Score = S × 1.0 + P × 50.0 - L × 1000.0 + N × 2000.0
```

| 항목 | 계산 상세 | 영향 |
|------|----------|------|
| **S** (표면적) | Σ(2π × r_i × L_i) × 100 (mm²) | + 클수록 좋음 |
| **P** (프루닝) | 총 프루닝 발생 횟수 | + 많을수록 좋음 (분기 ↑) |
| **L** (흙손실) | Σ(πR²) / (2×R_pot×H_pot) | - 낮을수록 좋음 (패널티) |
| **N** (질소흡수) | Σ(면적 × 효율 × Vmax × C / (Km + C)) | + 클수록 좋음 |

**추가 메트릭:**

| 메트릭 | 계산 | 의미 |
|--------|------|------|
| Spread Ratio | 방문 복셀 / 전체 흙 복셀 | 뿌리가 공간을 얼마나 활용하는가 |
| Unused Airrooms | 뿌리가 한 번도 안 닿은 에어룸 수 | 낮을수록 효율적 배치 |
| Pruning by Zone | z축 3등분(L/M/U) 프루닝 수 | 깊이별 프루닝 분포 |

### 5.6 Phase D: 탐색 (유전 알고리즘)

**Genome (유전자):** 각 개체 = 6개 에어룸 위치의 리스트

```
[(r1, z1, radius1), (r2, z2, radius2), ..., (r6, z6, radius6)]
```

- r: 0.5~6.0cm, z: 0.5~14.5cm, radius: 0.5~0.9cm

**세대 진행:**

```
Generation 0: 25개체 랜덤 생성 → 각각 5시드 평가
     ↓
상위 15% (≈4개체) 엘리트 선발
     ↓
Crossover: 엘리트 두 개체의 유전자 섞어 자식 생성
Mutation: 50% 확률로 유전자 위치 변이 (±0.8cm)
     ↓
새 개체군 25개체 → 평가 → 반복
     ↓
15세대 후 → 최종 best 선정
```

**랜덤 서치 (대안):**

GA 대신 단순히 `n_candidates`개의 랜덤 에어룸 배치를 생성하고, 각각 `n_eval_seeds`개의 시드로 평가한 뒤 점수 순으로 정렬.

- GA: 적은 평가로도 꾸준히 좋은 설계 (수렴성 ↑)
- 랜덤: 운 좋게 최고점을 찾을 수도 있지만 일관성 ↓

---

## 6. 시각화 이미지 해설

실행 결과는 `output/YYYY-MM-DD/run-NNN/viz/` 디렉토리에 4종류의 PNG 파일이 생성됨.

### 6.1 2D 6패널 (IR 주력)

**파일명:** `gwc_2d_ir_visualization.png`
**용도:** 과학적 검증, IR 자료

| 패널 | 내용 | 보는 법 |
|------|------|---------|
| **(A) Control 단면도** | 에어룸 없는 자연 성장 상태. 갈색 복셀 격자 배경 위에 3개 뿌리가 직하 성장 | 프루닝 없음 → Segments 적음, 분기 거의 없음 |
| **(B) GwC Experimental 단면도** | 6개 에어룸(주황 원) + 프루닝 지점(노란 별표). Gen2 뿌리가 옆으로 퍼져 에어룸에 닿음 | 별표 근처에서 gen3(연초록) 가는 뿌리가 폭발적 분기 |
| **(C) Pruning by Depth Zone** | 깊이별 프루닝 분포 가로 막대. 초록=하단, 노랑=중단, 빨강=상단 | 고루 분포할수록 좋은 설계. run-001은 상단=0 |
| **(D) Quantitative Metrics** | 3개 독립 차트: Segments / Absorption Area / G-Health Score. Ctrl(회색) vs Exp(초록) | 각각 독립 Y축 스케일. Exp가 2~10배 우세 |
| **(E) Info Box** | GA 설정, 최적 에어룸 6개 위치와 성능 지표 | 설계 스펙 요약 |
| **(F) Key Insight** | 핵심 발견 요약 (before/after 비교) | "프루닝이 이렇게 효과가 있다"는 메시지 |

### 6.2 3D 6패널 (홍보용)

**파일명:** `gwc_ir_visualization_v2.png`
**용도:** 투자자 피칭, 마케팅 — 시각적 임팩트

| 패널 | 차이점 |
|------|--------|
| **(A) Control 3D** | 3D 원통 와이어프레임. 뿌리는 procedural 렌더링 (엔진 데이터 아님) |
| **(B) Experimental 3D** | 파란 정사면체=에어룸. 6개 위치 × 3방향(120°) = 18개. 노란 별표=프루닝 |
| **(C) Pruning Detail** | Experimental 확대. 프루닝 후에도 뿌리가 계속 자라는 모습 |
| **(D) Quantitative Metrics** | 2D와 동일한 3개 차트 (Segments / Area / Score) |
| **(E) Info Box** | 2D보다 상세 (N uptake, spread ratio 포함) |
| **(F) Key Insight** | 생물학적 해석: "프루닝이 뿌리 구조를 어떻게 바꾸는가" |

> **2D vs 3D 차이:** 2D는 실제 엔진 복셀 데이터, 3D는 procedurally generated roots (위치는 유사하지만 형태는 근사). 과학적 검증엔 2D, 홍보용으론 3D 사용.

### 6.3 2패널 단면도

**파일명:** `gwc_2d_cross_section.png`
**용도:** 간단한 비교 (A: Control / B: Experimental)

- 사다리꼴 화분 형태 (구버전)
- 통계가 각 패널 우상단에 인라인 표시
- 빠른 비교가 필요할 때 사용

### 6.4 에어룸 배치도

**파일명:** `gwc_airroom_layout.png`
**용도:** 제조/설계용 — CAD 모델링 참조

| 구분 | 내용 |
|------|------|
| **좌측: 3D 뷰** | 6개 그룹 × 3방향(120°) = 18개 정사면체. 각 그룹은 동일 (r,z) 위치에서 회전 복제 |
| **우측: 탑뷰** | 위에서 본 단면. 각 그룹의 3개 위치가 120° 간격으로 균등 배치 확인 |
| **색상** | 그룹별 6색 (#1 테라코타 ~ #6 골드). 각 그룹에 r/z/radius 라벨 |

---

## 7. 모든 메트릭 사전

| 변수 | 출처 | 단위 | 의미 |
|------|------|------|------|
| `mean_score` | GA 결과 | 점수 | 5시드 평균 G-Health Score. **설계 성능의 대표값** |
| `std_score` | GA 결과 | 점수 | 5시드 표준편차. 낮을수록 시드에 덜 민감 = 견실 |
| `surface_area_mm2` | 뿌리 시스템 | mm² | 모든 뿌리 세그먼트의 총 표면적 |
| `eff_surface_area` | 뿌리 시스템 | mm² | 흡수효율 가중 적용 면적 (3차세대는 10× 가중) |
| `pruning_count` | 뿌리 시스템 | 회 | 총 프루닝 발생 횟수 |
| `pruning_by_zone` | 뿌리 시스템 | {L,M,U} | 깊이별 프루닝 분포 |
| `soil_loss_ratio` | 에어룸 | 비율 | 에어룸 체적 / 화분 체적 |
| `spread_ratio` | 뿌리 시스템 | 비율 | 방문 복셀 / 전체 흙 복셀 |
| `n_uptake_mg` | 양분 흡수 | mg | 총 질소 흡수량 (Michaelis-Menten) |
| `total_segments` | 뿌리 시스템 | 개 | 전체 뿌리 세그먼트 수 |
| `gen1/2/3_segments` | 뿌리 시스템 | 개 | 세대별 세그먼트 수 |
| `unused_airrooms` | 점수 | 개 | 뿌리가 한 번도 방문하지 않은 에어룸 수 |
| `ga_history_best` | GA | 점수[] | 세대별 최고 점수 (수렴 추이) |
| `ga_history_mean` | GA | 점수[] | 세대별 평균 점수 (집단 향상 추이) |

---

## 8. 결과 해석 — 뭘 봐야 하는가?

### 8.1 기본 판단 기준

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

### 8.2 상세 판단 기준

**1차: 점수 (mean_score)**

| 점수대 | 평가 |
|--------|------|
| 15,000+ | 매우 좋음 (run-001 #1은 14,662로 근접) |
| 10,000+ | 양호 |
| 8,000+ | 보통 |
| 6,000+ | Control 수준 (에어룸 없는 기본) |

**2차: 안정성 (std_score)**

| 표준편차 | 평가 |
|----------|------|
| < 1,000 | 매우 안정적. 시드 바꿔도 비슷한 성능 |
| 1,000~2,000 | 보통 |
| > 3,000 | 불안정. 운 좋으면 높지만 실패 리스크 큼 |

**3차: 프루닝 분포 (pruning_by_zone)**

| 분포 | 평가 |
|------|------|
| L=30~50, M=30~50, U=10~30 | 이상적 — 모든 깊이에서 프루닝 발생 |
| L/M에 편중, U=0 | 개선 필요 — run-001이 이 상태 |
| 한쪽에만 집중 | 비효율적 배치 |

**4차: Spread Ratio**

| 비율 | 평가 |
|------|------|
| > 0.20 | 뿌리가 화분 전체에 고르게 퍼짐 (좋음) |
| 0.10~0.20 | 보통 |
| < 0.05 | 뿌리가 한 곳에만 몰림 (나쁨) |

**5차: Soil Loss vs Surface Trade-off**

```
에어룸 크기 ↑ → 프루닝 ↑ → 표면적 ↑ (좋음)
            → 흙손실 ↑ (나쁨)

최적점: soil_loss < 0.07 이면서 pruning_count > 50
```

**최종 목표(양분 임계값) 관점의 판단:**

| 단계 | 지표 | 목표 |
|------|------|------|
| ① 프루닝 | pruning_count | 20~50회 (적정 범위) |
| ② 표면적 | surface_area_mm2 | 클수록 좋음 (10000mm²+) |
| ③ 흡수량 | n_uptake_mg | ≥ 식물별 임계값 (추후 종 프로필 추가) |

---

## 9. 실험 결과 요약 — 13cm 화분

> 자세한 실험 이력: [`RESULTS.md`](RESULTS.md)

**최종 선정 설계 (V3 — g=1.0, noise=8°)**

```
Mean±Std = 6861 ± 823 (15개 시드)
Surface  = 4657 mm²
Pruning  = 50회 (하단 30 + 중간 20 ✅ 분산 성공)
Soil Loss = 5.6%
N Uptake = 0.26 mg
```

**에어룸 배치 (6개):**

| # | r(cm) | z(cm) | 반경(cm) | 위치 |
|---|-------|-------|---------|------|
| 1 | 2.05 | 3.55 | 0.71 | 하단 |
| 2 | 1.96 | 6.26 | 0.82 | 중간 |
| 3 | 3.91 | 5.70 | 0.50 | 중간-외곽 |
| 4 | 3.12 | 12.15 | 0.70 | 상단 |
| 5 | 2.46 | 4.56 | 0.86 | 하단-중간 |
| 6 | 1.80 | 2.58 | 0.90 | 하단 |

**핵심 통찰:**

- 중력(g) 1.5→1.0 + 노이즈 4°→8°가 최적 균형점
- 너무 강한 중력(g≥1.3)이나 너무 약한 중력(g≤0.8) 모두 비효율
- 5시드 미만 평가는 신뢰도 부족 (시드 편차 최대 20%)
- **상단(U) 프루닝은 아직 미해결 과제** (run-001에서 상단 프루닝 = 0)

---

## 10. 파라미터 튜닝 가이드

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
| 성장 방향 | mvp.json | `tropism.g` (중력), `tropism.h` (수분 방향) |

---

## 11. 실전 워크플로우

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

- 시뮬레이션이 "어디에 에어룸을 배치할지" 설계 도출
- Fusion 360에서 3D 모델링 (STL 출력)
- SimScale에서 CFD 검증 ("공기 흐름이 설계대로 가는가?")
- IR 자료에는 시뮬레이션 결과(점수/비교/시각화)만으로도 충분

---

## 12. 주의사항

**1. 단일 시드 점수는 믿지 마세요.** 3개 이상 시드 평균을 써야 우연히 잘 나온 설계를 걸러냅니다. `n_eval_seeds=3` 기본값 유지 권장.

**2. 2D 단면의 한계:** 2D r-z 단면은 회전 대칭을 가정합니다. 실제 3D에서는 원주 방향 엉킴이나 층류 편차가 발생할 수 있습니다. 최종 검증은 3D로 해야 합니다.

**3. 생물학적 단순화:**

- 에틸렌 호르몬 모델 미적용 (설계 비교 능력 0% 개선)
- 자원 확산 + 흡수는 기본 활성화 가능 (mvp.json에서 제어)
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

## 13. 파일 구조

```
gwc-root-sim/
├── configs/
│   ├── mvp.json               ★ 메인 설정 (V3 파라미터 반영)
│   ├── pot_13.json            ★ 13cm 화분 설정 (최적화 대상)
│   ├── precision.json         고정밀 설정 (0.15cm 해상도)
│   └── species/
│       ├── monstera.json      몬스테라 프로필
│       ├── ficus.json         피쿠스 프로필
│       └── cactus.json        선인장 프로필
├── src/
│   ├── config.py              설정 로드/검증
│   ├── grid.py                복셀 격자 (2D r-z)
│   ├── geometry.py            에어룸 형상 + 프루닝 검사
│   ├── root.py                ★ 뿌리 성장 + 프루닝 엔진
│   ├── score.py               G-Health Score + 양분 흡수
│   ├── diffusion.py           자원 확산 (CA)
│   ├── uptake.py              Michaelis-Menten 양분 흡수
│   ├── pipeline.py            실행 오케스트레이션
│   ├── ga.py                  유전 알고리즘
│   ├── search.py              탐색 (랜덤/GA) + 결과 저장
│   └── viz.py                 시각화 (matplotlib)
├── experiments/               검증 및 실험 스크립트
├── output/                    결과 파일 (JSON + PNG)
├── RESULTS.md                 ★ 실험 이력 (V1~V4)
├── BIOLOGY.md                 생물학적 배경 지식
└── MECHANISM.md               기술 메커니즘 완전 해설
```

---

## 14. 용어 설명

| 용어 | 뜻 |
|------|-----|
| **에어프루닝** | 뿌리 끝이 공기에 닿아 세포 사멸 → 측근 분기 유도 |
| **에어룸** | 화분 벽면의 공기 구멍, 프루닝 발생 지점 |
| **r-z 단면** | 원통 화분의 반경-높이 2D 단면 |
| **복셀** | 3D 픽셀, 격자 단위 |
| **G-Health Score** | 뿌리 건강도를 수치화한 점수 |
| **Spread Ratio** | 방문한 복셀 수 / 전체 흙 복셀 수 |
| **시드(seed)** | 난수 시작값. 같은 시드 = 같은 결과 (재현성) |
| **Monte Carlo** | 여러 시드로 반복 실행 → 평균 내는 방식 |
| **세대(generation)** | 뿌리 분기 깊이 (1차→2차→3차) |
| **σ√dx 스케일링** | step_size 무관 일관된 궤적 보장 |

---

## 15. 학술 출처 및 근거

시뮬레이터의 파라미터와 알고리즘은 아래 학술 문헌을 기반으로 함.

| # | 출처 | 인용 | 적용 항목 |
|---|------|------|----------|
| 1 | **Schnepf et al. (2018)** *Ann Bot* 121(5):1033-1053. [PMC5906965](https://pmc.ncbi.nlm.nih.gov/articles/PMC5906965/) | CRootBox 뿌리 아키텍처 프레임워크. 분기각(80°/85°), 분기간격(0.5/1.2cm). | 세대별 분기각, 최대각도 |
| 2 | **Pagès (2014)** *Ann Bot* 114(3):591-598. [PMC4204672](https://pmc.ncbi.nlm.nih.gov/articles/PMC4204672/) | 45종 쌍떡잎식물 분기 패턴. **Allometric radius 공식: r_child = Dmin + 0.25 × (r_parent − Dmin)**. | 자식뿌리 반경 계산 |
| 3 | **Pagès (2016)** *Front Plant Sci* 7:1522. [PMC5155602](https://pmc.ncbi.nlm.nih.gov/articles/PMC5155602/) | 140종 단자엽/쌍자엽 비교. IBD 중간값 1.4mm(단)/2.7mm(쌍). | 분기 간격 검증 |
| 4 | **Guo et al. (2008)** *New Phytol* 180(4):807-818. | 23수종 fine root order 분석. 1~3차근이 전체 흡수길이의 ~75% 차지. | 뿌리 세대별 흡수 효율 가중치 |
| 5 | **Craig et al. (2025)** *New Phytol* (dataset). [DOI: 10.15485/2524531](https://doi.org/10.15485/2524531) | 77수종 783개 관측. NH₄⁺ Vmax 중간값 6.67 µmol/g/h. | 양분흡수율(Imax) 기준 |
| 6 | **North & Nobel (1998)** *New Phytol* 138(2):307-317. | Opuntia 뿌리 탈수 실험. 건조 3일 후 대부분의 apical 사멸. | 프루닝 확정적 과정 근거 |
| 7 | **PLOS ONE (2018)** *Platycladus orientalis* air-pruning. | 프루닝 72h 후 측근 6배 증가 (branch당 ~7개). | 프루닝→분기 메커니즘 |
| 8 | **YUC9-mediated auxin pathway (2018)** [PMC5921505](https://pmc.ncbi.nlm.nih.gov/articles/PMC5921505/) | 뿌리 절단 → YUC9 활성화 → 옥신 축적 → 측근 형성. | 프루닝 분자 메커니즘 |
| 9 | **Reid et al. (1998)** *Arabidopsis* root-tip excision [PMC34753](https://pmc.ncbi.nlm.nih.gov/articles/PMC34753/). | 뿌리끝 절단 후 측근 밀도 유의미 증가 (P=0.001). | 프루닝→분기 검증 |
| 10 | **McDonald et al.** 사탕수수 뿌리 흡수. NH₄⁺ Imax 97.5 nmol/cm²/h ≈ 30 µg/cm²/day. | 단위면적당 흡수율 기준 |
| 11 | **Iversen et al. (2021)** FRED 3.0 database. [roots.ornl.gov](https://roots.ornl.gov/) | 4500+ 종 뿌리 형질 데이터. SRL, 직경, N 농도. | 종별 파라미터 참조 |
| 12 | **Osmont et al. (2007)** *J Exp Bot* 58(5):909-920. | 측근 형성 호르몬 조절 리뷰. "LRs themselves undergo branching to form tertiary and higher order LRs." | 3세대 모델 검증 |

---

## 16. 빠른 명령어 모음

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
python experiments\test_m4m5.py
python experiments\test_ga.py
```
