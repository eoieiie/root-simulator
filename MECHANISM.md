# GWC Root Simulator — 메커니즘 완전 해설

> Garden with Couch 에어프루닝 팟 최적화 엔진
>
> **목적**: 2D r-z 단면 시뮬레이션으로 수천 가지 에어룸 배치를 1초 단위로 평가하여,
> "어디에, 얼마나 큰 에어룸을 배치해야 가장 많은 잔뿌리가 발생하는가"를 수학적으로 찾는다.
>
> **최종 목표**: 에어룸 배치 최적화 → 프루닝(분기) 유도 → 뿌리 표면적 증대 → 양분 흡수율 극대화

---

## 목차

- [Part 0: 처음 보는 사람을 위한 1-page 요약](#part-0-처음-보는-사람을-위한-1-page-요약)
- [Part 1: 시스템 아키텍처와 데이터 흐름](#part-1-시스템-아키텍처와-데이터-흐름)
- [Part 2: 뿌리 성장 알고리즘 (Phase B)](#part-2-뿌리-성장-알고리즘-phase-b)
- [Part 3: 에어프루닝 메커니즘 (Phase B)](#part-3-에어프루닝-메커니즘-phase-b)
- [Part 4: 점수 계산 — G-Health Score (Phase C)](#part-4-점수--계산--g-health-score-phase-c)
- [Part 5: 탐색 및 최적화 (Phase D)](#part-5-탐색-및-최적화-phase-d)
- [Part 6: 시각화 (Phase E)](#part-6-시각화-phase-e)
- [Part 7: 설정 가이드 — 모든 Parameter](#part-7-설정-가이드--모든-parameter)
- [Part 8: 확장성 — 2D → 3D 전략](#part-8-확장성--2d--3d-전략)
- [Part 9: 학술 출처와 근거](#part-9-학술-출처와-근거)
- [부록: 용어 사전 & FAQ](#부록-용어-사전--faq)

---

## Part 0: 처음 보는 사람을 위한 1-page 요약

### 이 시뮬레이터가 푸는 문제

에어프루닝 화분은 흙 속에 **정사면체 빈 공간(에어룸)**을 배치해서 뿌리를 공기로 유도 → 뿌리 끝을 죽임(프루닝) → 그 자리에서 잔뿌리가 폭발적으로 분기하게 만드는 제품이다.

**문제는**: 에어룸을 **어디에, 몇 개나, 얼마나 크게** 배치해야 가장 효과적인지 실험으로 찾으려면 화분을 수백 번 만들어야 한다. 시뮬레이터는 이걸 **컴퓨터에서 수천 가지 경우를 1초에 계산**해서 최적 배치를 찾아준다.

### 핵심 아이디어 3줄

```
1. 뿌리가 아래로 자라면서 중력 + 랜덤 노이즈로 퍼짐
2. 뿌리 끝이 에어룸(공기 구멍)에 닿으면 → 팁 죽고 → 그 자리에서 2~6개 측근 분기 (프루닝)
3. 프루닝이 많을수록 잔뿌리(표면적) ↑ → 양분 흡수 ↑ → 식물 건강 ↑
```

### 2D 단면 쓰는 이유

- 3D 전체를 계산하면 격자 수가 24배 증가해서 탐색 속도가 24배 느려짐
- 화분이 원통형(회전 대칭)이라, 2D 단면(r-z 평면: 반경-높이)으로 잘라도 핵심 정보 유지됨
- 2D로 수만 가지를 빠르게 돌려서 **수학적 최적값**을 찾고, 그 최적값만 3D(Fusion 360 + 3D Python)로 검증

### 최종 목표 연결고리

```
프루닝 횟수 ↑  →  뿌리 표면적 ↑  →  양분 흡수량 ↑  →  식물이 필요한 임계값 돌파
  (분기 유발)     (흡수 면 확보)      (실제 흡수)        (최종 목표)
```

### 출력: G-Health Score

```
Score = S × 1.0 + P × 50.0 - L × 1000.0 + N × 2000.0

S = 표면적 (mm²)       — 클수록 좋음
P = 프루닝 횟수          — 많을수록 좋음 (단, 적정 범위 20~80회)
L = 흙손실률 (0~1)      — 적을수록 좋음
N = 양분 흡수량 (mg)    — M7 활성화 시 (Michaelis-Menten) 계산
```

---

## Part 1: 시스템 아키텍처와 데이터 흐름

### 1.1 파이프라인 개요

```
configs/mvp.json
    ↓
[Phase A] 공간 복셀화 ───── grid.py, geometry.py
    ↓
[Phase B] 뿌리 성장 + 프루닝 ─ root.py
    ↓
[Phase C] 점수 계산 ──────── score.py
    ↓
[Phase D] 탐색/최적화 ───── search.py, ga.py
    ↓
[Phase E] 시각화 ────────── viz.py
```

### 1.2 모듈별 책임

| 모듈 | 파일 | 책임 |
|------|------|-------|
| **Config** | `config.py` | JSON → Python dataclass 로드, 검증 |
| **Grid** | `grid.py` | 2D r-z 복셀 격자 생성, 화분 마스킹 |
| **Geometry** | `geometry.py` | 에어룸 단면 마스크, 프루닝 영역 계산 |
| **Root** | `root.py` | **뿌리 성장 + 프루닝 — 이 엔진의 핵심** |
| **Score** | `score.py` | G-Health Score 계산 |
| **Search** | `search.py` | Random Search 탐색 |
| **GA** | `ga.py` | 유전 알고리즘 최적화 |
| **Viz** | `viz.py` | 단면도 + 점수 시각화 |
| **Pipeline** | `pipeline.py` | Phase A→B→C→E를 1회 연결 |

### 1.3 파일 구조

```
gwc-root-sim/
├── configs/
│   ├── mvp.json              ★ 메인 설정 (모든 파라미터)
│   └── species/
│       ├── monstera.json      몬스테라 프로필
│       ├── ficus.json         피쿠스 프로필
│       └── cactus.json        선인장 프로필
├── src/
│   ├── config.py              설정 로드/검증
│   ├── grid.py                복셀 격자 (2D r-z)
│   ├── geometry.py            에어룸 형상
│   ├── root.py                ★ 뿌리 성장 + 프루닝
│   ├── score.py               G-Health Score
│   ├── viz.py                 시각화
│   ├── ga.py                  유전 알고리즘
│   ├── search.py              탐색 (Random/GA)
│   ├── pipeline.py            전체 연결
│   ├── diffusion.py           M6: CA 자원 확산 (수분/양분 격자)
│   └── uptake.py              M7: Michaelis-Menten 양분 흡수
├── experiments/               검증 스크립트
├── output/                    결과 (PNG + JSON)
├── MECHANISM.md               ★ 이 문서
├── plan.md                    설계 문서 (참고용)
└── README.md                  빠른 시작 가이드
```

### 1.4 데이터 흐름 — 한 번 실행될 때

```python
# pipeline.py run() — 1회 실행 (config 1개로 전체 사이클)
cfg = SimConfig.from_json("configs/mvp.json")
pipe = SimPipeline(cfg)
result = pipe.run(seed=42, max_steps=500, render=True)
# result = {
#   "grid": VoxelGrid,        # Phase A: 복셀 격자
#   "airrooms": [...],         # Phase A: 에어룸 리스트
#   "root_system": RootSystem, # Phase B: 뿌리 + 프루닝 결과
#   "score": {...},            # Phase C: 점수 + 메트릭
#   "fig": Figure              # Phase E: 시각화 (옵션)
# }
```

---

## Part 2: 뿌리 성장 알고리즘 (Phase B)

이 파트가 **가장 중요**. 시뮬레이터의 핵심은 "뿌리 끝이 어디로 자라나, 언제 에어룸을 만나서 프루닝되는가"를 계산하는 것.

### 2.1 뿌리 세대 (Generation) 구조

뿌리는 3세대로 구성. 각 세대는 굵기, 성질, 역할이 다르다:

```
1세대 (Primary): 굵고 곧게 아래로. 수송 담당.
    ↓ (프루닝 or 바닥 도달)
2세대 (Secondary): 중간 굵기, 옆으로 퍼짐. 혼합 역할.
    ↓ (프루닝 or 바닥 도달)
3세대 (Tertiary): 가늘고 짧고 많음. **주 흡수 담당**. 더 이상 분기 안 함.
```

**최대 3세대인 이유** (Schnepf et al. 2018 — CRootBox):
- 3세대 이후의 분기는 뿌리 시스템 전체 표면적에 미미한 영향
- 4세대+는 연산량만 늘리고 실질적 기여도 낮음

### 2.2 초기화 — `_init_roots()`

```
시작점: 화분 상단 중앙 (r=0, z=pot_height=20cm)
초기 뿌리: config.initial_roots = 3개
  ─ 첫 번째: r=0 (정중앙)
  ─ 두 번째: r=voxel_size×0.5 (약간 오른쪽)
  ─ 세 번째: r=voxel_size×1.0 (더 오른쪽)

각 초기 뿌리의 1세대 파라미터:
  - 반경: 0.18cm (config.root.radii_cm[0])
  - 최대 수명: 200 steps (max_segment_steps[0])
  - 초기 각도: 0° (직하)
```

### 2.3 매 스텝 성장 — `step()`

매 스텝마다 **살아있는 모든 뿌리 팁**이 아래 순서를 실행:

```
1. 방향 갱신 ────── 중력 + 노이즈
2. 전진 ────────── step_size 만큼
3. 경계 검사 ────── 반사 또는 사멸
4. 위치 갱신 ────── end_r, end_z, length, steps_lived
5. 수명 검사 ────── max_lifetime 초과 시 사멸
6. 복셀 기록 ────── root_visits[i,j] += 1
7. 프루닝 검사 ──── 에어룸 접촉 시 프루닝
```

#### 2.3.1 방향 계산

```python
# 각도 갱신 = 이전 각도 유지(관성) + 중력(0° 방향으로 당김) + 랜덤 노이즈

# 중력 효과 (tropism.g = 1.5)
angle *= (1.0 - g * 0.02)  # angle이 0(직하) 방향으로 수렴

# 랜덤 노이즈 (σ·√dx 스케일링 적용)
noise_deg *= √(step_size / 0.4)  # step_size 무관 일관된 궤적 보장
noise = uniform(-noise_deg, +noise_deg)  # 균등분포 노이즈

# 최대 각도 제한
angle = clamp(angle, -max_angle_deg, +max_angle_deg)
```

**σ·√dx 스케일링**: step_size를 바꿔도 랜덤 워크의 확산 속도가 일정하게 유지되는 원리.
랜덤 노이즈의 표준편차에 √(step_size)를 곱하면 step_size를 0.5cm에서 0.25cm로 줄여도
동일한 스텝 수 후의 궤적 분포가 같아진다.

#### 2.3.2 세대별 파라미터

| 파라미터 | 1세대 (Primary) | 2세대 (Secondary) | 3세대 (Tertiary) | 근거 |
|---------|:--------------:|:-----------------:|:----------------:|------|
| **반경** | 0.18 cm | 0.0525 cm* | 0.0325 cm* | Pagès 2014 |
| **노이즈** | ±4.0° | ±15.0° | ±25.0° | 1차=곧게, 3차=구불구불 |
| **최대각도** | ±20.0° | ±80.0° | ±85.0° | CRootBox |
| **분기각** | (없음, 줄기에서 직접) | ±75° | ±85° | CRootBox |
| **최대수명** | 200 steps | 200 steps | 150 steps | config |
| **흡수효율** | ×0.1 (수송) | ×0.5 (혼합) | ×1.0 (흡수) | Guo 2008 |

> \* 반경은 Pagès (2014) allometric 공식으로 계산:
> `r_child = 0.01 + 0.25 × (r_parent - 0.01)`
>
> 예: 1세대(r=0.18) → 2세대: 0.01 + 0.25 × (0.18 - 0.01) = 0.0525 cm
> 2세대(r=0.0525) → 3세대: 0.01 + 0.25 × (0.0525 - 0.01) = 0.0206 cm

#### 2.3.3 전진 — 위치 계산

```python
step_size = 0.25 cm  (config, voxel_size보다 작게)

# 이동 벡터
dr = step_size × sin(angle)   # r축 방향 (옆으로)
dz = -step_size × cos(angle)  # z축 방향 (아래로, z는 위로 갈수록 큼)

# 새 위치
new_r = end_r + dr
new_z = end_z + dz
```

### 2.4 경계 처리

뿌리 팁이 화분 경계에 닿으면:

| 상황 | 처리 | 코드 위치 |
|------|------|----------|
| `new_r < 0` (중심축 넘음) | **반사**: `r = -r, angle = -angle` | root.py:166-168 |
| `new_z > pot_height` (윗면) | **반사**: `z = pot_height, angle = π - angle` | root.py:170-172 |
| `new_r > pot.radius` (벽) | **사멸**: `active = False`, 분기 없음 | root.py:174-176 |
| `new_z < 0` (바닥) | **사멸**: `active = False`, 분기 없음 | root.py:174-176 |

**중요**: 경계 사멸은 프루닝과 달리 **분기가 발생하지 않는다.** 그냥 그 뿌리 조각이 죽는다.
→ 이게 시뮬레이션이 80~100스텝 내에 끝나는 주된 이유 (화폰 높이 20cm / step_size 0.25 = 80스텝).

### 2.5 수명 종료

```python
# root.py step() — 각 segment의 steps_lived를 확인
if seg.steps_lived >= seg.max_lifetime:
    seg.active = False  # 자연사
    # 분기 없음
```

| 세대 | max_lifetime | 실제 도달 여부 |
|------|-------------|--------------|
| 1차 | 200 steps | ❌ 거의 못 감 (바닥에 80스텝 내 도달) |
| 2차 | 200 steps | ❌ 마찬가지 |
| 3차 | 150 steps | ❌ 마찬가지 |

**결론**: max_lifetime은 실제로는 거의 쓰이지 않는다. 화분이 작아서 경계 사멸이 항상 먼저 발생.

---

## Part 3: 에어프루닝 메커니즘 (Phase B)

### 3.1 프루닝 감지 — `_check_pruning()`

뿌리 팁이 새 위치(new_r, new_z)로 이동한 후, 모든 에어룸에 대해 "이 팁이 내 영향권 안에 있는가"를 검사한다.

```python
# geometry.py — Airroom.is_in_pruning_zone()
def is_in_pruning_zone(self, r, z):
    dx = r - self.r
    dz = z - self.z
    distance = √(dx² + dz²)
    return distance ≤ self.pruning_zone_radius
    # pruning_zone_radius = airroom.radius × pruning_zone_factor
```

**영향권 반경**:
```
pruning_zone_radius = airroom.radius × pruning_zone_factor
                    = [0.8~1.5]cm × 1.15
                    = [0.92~1.73]cm
```

`pruning_zone_factor = 1.15`의 의미:
- 생물학적 근거: 뿌리가 공기 구멍에 **실제로 노출**되어야 프루닝됨 (North & Nobel 1998)
- 2D 보정: 2D r-z 단면에서는 원주 방향(θ) 접근 기회가 사라지므로, 약간의 여유(×1.15)를 둠
- min: 1.0 (공기 구멍 안으로만 들어가야 프루닝), max: 1.5 (너무 넓음)

### 3.2 프루닝 조건

```python
# root.py step() — 조건 검사
if _check_pruning(new_r, new_z):            # 영향권 안?
    if rng.random() < pruning_probability:  # 확률 통과?
        _do_prune(seg)                      # 프루닝 실행!
```

`pruning_probability = 1.0` (확정적):
- **생물학적 근거**: 공기프루닝은 습도 의존적 과정이 아니라 **확정적인 탈수 과정**임
  - North & Nobel (1998): Opuntia 뿌리, 건조 3일 후 대부분 apical 사멸
  - PLOS ONE (2018): Platycladus orientalis, 프루닝 72h 후 측근 6배 증가
- 즉, "만나면 거의 무조건 프루닝된다"가 학계의 합의된 관점
- 확률을 1.0 미만으로 낮추면: 일부 뿌리가 에어룸을 통과해 더 깊이 내려감
  → 제품 설계 관점에서는 비현실적 (공기 구멍을 만든 의미가 사라짐)

### 3.3 프루닝 실행 — `_do_prune()`

프루닝이 결정되면 **항상 동일한 동작**을 수행한다 (강도 구분 없음):

```python
def _do_prune(self, seg):
    # 1. 현재 팁 사멸
    seg.active = False
    seg.pruned = True
    기록: (end_r, end_z, generation) → pruning_locations 리스트

    # 2. 최대 세대면 분기 없이 종료
    if gen >= max_generation(3): return

    # 3. 자식 뿌리 반경 계산 (Pagès 2014 allometric)
    child_radius = 0.01 + 0.25 × (parent.radius - 0.01)

    # 4. 2~6개 측근 분기
    for _ in range(random.randint(2, 6)):
        분기각 = random.uniform(min_branch_angle, max_branch_angle)
        자식 = 새로운 RootSegment(
            generation = parent.generation + 1,
            radius = child_radius,
            start_r = parent.end_r,
            start_z = parent.end_z,
            initial_angle = 분기각,
            max_lifetime = max_segment_steps[child_gen]
        )
        self.segments.append(자식)
```

#### 3.3.1 분기 각도

자식 뿌리는 부모 사멸 지점에서 일정 각도 범위 내에서 랜덤하게 퍼져나간다:

| 부모 세대 | 자식 분기각 범위 | 자식이 퍼지는 방향 |
|----------|----------------|------------------|
| 1차 → 2차 | ±75° | 옆으로 넓게 퍼짐 |
| 2차 → 3차 | ±85° | 더 넓게, 거의 수평 |

근거: Schnepf et al. (2018) — CRootBox. 2차근은 주축에서 측면으로 탐색, 3차근은
거의 모든 방향으로 흡수 표면을 확보.

#### 3.3.2 Allometric Radius Decay — 수식 해설

```
r_child = D_min + slope × (r_parent - D_min)

D_min = 0.01 cm    — 가장 가는 뿌리의 직경 (≈0.1mm, 세포 수준)
slope = 0.25       — 45종 쌍떡잎식물 평균값 (실측 범위: 0.14~0.36)
```

**의미**: 자식 뿌리의 굵기는 부모의 굵기에 비례하지만, 항상 D_min(0.01cm) 이상은 유지한다.
slope=0.25는 "25%만 유지한다"는 뜻이 아니라 "부모와 자식의 굵기 차이가 75% 줄어든다"는 뜻.

**예시 계산**:

```
1차(r=0.18): 2차 = 0.01 + 0.25 × (0.18 - 0.01) = 0.0525 cm
2차(r=0.0525): 3차 = 0.01 + 0.25 × (0.0525 - 0.01) = 0.0206 cm

(참고: 이전에는 고정값 radii_cm=[0.18, 0.10, 0.04]을 썼음)
```

### 3.4 프루닝 통계 — `pruning_by_zone()` ★ 용어 주의

`pruning_by_zone()`은 **프루닝 강도 레벨이 아니다.** 단순히 z축 기준으로 프루닝이
**어느 위치에서 발생했는지** 세는 통계 함수다:

```python
def pruning_by_zone(self):
    pot_height = 20cm
    lower = 0~6.7cm   (z/pot_height ≤ 1/3)    — 바닥 쪽
    middle = 6.7~13.3cm (1/3 < z ≤ 2/3)       — 중간
    upper = 13.3~20cm  (z > 2/3)              — 표면 쪽
```

**이것은 점수에 반영되지 않는다.** 결과 지표로만 출력된다 (search 출력에서 `L/M/U` 표시).

> **왜 점수에 안 넣나?** (plan.md §5.2)
> 하단 프루닝이 많은 게 좋다는 직관은 있지만, 가중치 근거가 없다.
> 먼저 데이터로 "하단 프루닝이 많은 설계가 실제로 더 좋은가"를 확인한 후에
> 점수에 반영할지 결정한다.

---

## Part 4: 점수 계산 — G-Health Score (Phase C)

### 4.1 기본 공식

```
Score = S × w_surface + P × w_pruning - L × w_soil_loss + N × w_uptake
      = S × 1.0       + P × 50.0      - L × 1000.0      + N × 2000.0
```

각 항목의 존재 이유:

| 항목 | 왜 필요한가 | 의도한 효과 |
|------|-----------|-----------|
| **S (표면적)** | 큰 표면적 = 더 많은 흡수 가능 | 에어룸이 뿌리 분기를 유도하는지 측정 |
| **P (프루닝)** | 프루닝 = 분기 유발 = 잔뿌리 증가 | 프루닝이 없는 설계(0-airroom)에 패널티 |
| **L (흙손실)** | 에어룸이 너무 크면 흙이 부족 | 과도한 에어룸 개수/크기 억제 |
| **N (양분흡수)** | 실제 흡수량 (M7) | Michaelis-Menten 동역학 기반 정량 |

### 4.2 각 항목 상세

#### S — 표면적 (Surface Area)

```
각 뿌리 조각을 원통으로 근사:
  A_i = 2 × π × r_i × L_i          (cm²)
  S_cm² = A_1 + A_2 + ... + A_N    (모든 조각 합산)
  S = S_cm² × 100                   (cm² → mm²)

π = 3.14159...
r_i = i번째 뿌리 조각의 반경 (cm) — 세대별 allometric radius 사용
L_i = i번째 뿌리 조각의 길이 (cm)

예: 3차 뿌리 150개, 각각 길이 3cm, 반경 0.02cm
  한 개: 2 × 3.14 × 0.02 × 3 = 0.377 cm²
  150개: 56.5 cm² = 5650 mm²
  → S × 1.0 = 5650 점
```

#### P — 프루닝 횟수 (Pruning Count)

```
P = pruning_locations 리스트 길이 (프루닝 발생 총 횟수)

예: 프루닝 50회 발생
  → P × 50.0 = 2500 점

프루닝 점수 근거:
  - PLOS ONE (2018): Platycladus orientalis — 프루닝 72h 후 측근 6배 증가
  - Reid et al. (1998): Arabidopsis 뿌리절단 — 측근 밀도 유의미 증가 (P=0.001)
  - YUC9-mediated auxin (2018): 절단 부위 옥신 축적 → 측근 형성 (분자 메커니즘)
```

#### L — 흙손실률 (Soil Loss Ratio)

```
각 에어룸의 단면적 합 / 화분 전체 단면적:

  L = (π × R_1² + π × R_2² + ... + π × R_N²) / (2 × R_pot × H_pot)

  R_j = j번째 에어룸의 반경 (cm)
  R_pot = 화분 반경 = 12cm
  H_pot = 화분 높이 = 20cm
  화분 단면적: 2 × 12 × 20 = 480 cm²

예: 반경 1cm 에어룸 10개
  L = (10 × π × 1²) / 480 = 31.4 / 480 = 0.065 (6.5%)
  → -L × 1000 = -65 점
```

### 4.3 점수 계산 예시 (실제 최종 설계 데이터)

```python
# V3 최종 설계 (13cm pot, noise=8°, g=1.0)
# 에어룸 6개, 프루닝 50회, 표면적 4657mm², 흙손실 5.6%, N흡수 0.26mg
S 기여: 4657 × 1.0   = +4657
P 기여: 50 × 50.0    = +2500
L 패널티: -0.056 × 1000 = -56
N 기여: 0.26 × 2000  = +520
Score = 4657 + 2500 - 56 + 520 = 7621 (단일시드 기준)

※ 15개 시드 평균 = 6861 ± 823 (시드 편차 존재)
```

### 4.4 추가 메트릭 (점수 미반영, 결과로만 출력)

#### Spread Ratio — 뿌리 퍼짐 정도

```
Spread = (뿌리가 방문한 복셀 수) / (전체 흙 복셀 수)

낮음 (5%): 뿌리가 좁은 영역에 집중
높음 (20%+): 뿌리가 화분 전체에 고르게 퍼짐 → 양호
```

#### N Uptake — 질소 흡수량 (M7)

M7 활성화 시, 선형 또는 Michaelis-Menten 모델로 각 세그먼트 위치의 국소 양분 농도를
반영한 실제 흡수량 계산:

```
Michaelis-Menten:
  Uptake_i = S_i × Eff(gen) × Vmax × C_local / (Km + C_local)

세대별 효율 Eff(gen) (Guo et al. 2008):
  gen1 (수송 위주): 0.1×
  gen2 (혼합): 0.5×   
  gen3 (주 흡수): 1.0×

Vmax = 0.001 mg/mm²/day  (NH₄, Craig et al. 2025 기준)
Km   = 0.05 mg/cm³
C_local: 각 세그먼트 위치의 국소 농도 (M6 확산 결과)
```

M7 비활성화 시에는 이전 선형 추정값을 `n_uptake_mg: 0.0`으로 표시.

---

## Part 5: 탐색 및 최적화 (Phase D)

### 5.1 Random Search

가장 단순한 탐색: config에 정의된 개수만큼 무작위 에어룸 배치를 생성하고 각각 평가.

```python
# search.py
cfg.search.n_candidates = 50   # 후보 설계 수
cfg.search.n_eval_seeds = 5    # 설계당 평가 시드 수 (seed 다양성 확보)

for _ in range(n_candidates):
    배치 = 무작위 생성(max_count 이하)
    점수들 = []
    for seed in range(5):
        r = pipeline.run(seed=seed, airrooms_override=배치)
        점수들.append(r.score.total)
    평균 = mean(점수들)
    if 평균 > Top5 최하위:
        Top5에 추가

print(Top5): # 점수 높은 순
#1: Mean=8302  Airrooms=8  Surface=6190mm2  Pruning=51  Spread=13%
```

### 5.2 Genetic Algorithm (GA)

Random Search보다 효율적인 최적화. 적은 평가 횟수로 더 좋은 설계를 찾는다.

#### Genome (유전자)

```python
# 각 개체 = 에어룸 10개의 위치와 반경
Genome = [
    (r0, z0, radius0),   # 에어룸 1
    (r1, z1, radius1),   # 에어룸 2
    ...
    (r9, z9, radius9),   # 에어룸 10
]
# 총 30개 실수 (10 airrooms × 3 params)
```

#### GA 파라미터

| 파라미터 | 현재값 (V3) | 설명 |
|---------|-----------|------|
| population | **25** | 한 세대의 개체 수 |
| generations | 15 | 총 진화 세대 수 |
| elite_frac | **0.15** | 상위 15%를 다음 세대에 그대로 유지 |
| mutation_sigma | **0.8 cm** | 위치 변이의 표준편차 |
| crossover | single-point | 한 지점에서 유전자 교차 |
| 평가 예산 | 25×15×5시드 = 1875회 | 전체 evolution 비용 (약 30~60분 소요) |

> 💡 **실험 결과**: population=25, elite=0.15, mutation_sigma=0.8 조합이
> population=30, elite=0.2, sigma=1.5보다 더 다양한 설계를 탐색함.
> 너무 큰 mutation sigma(sigma=1.5)는 수렴을 방해함.

#### 진화 과정

```
세대 1: [30개 무작위 생성 → 평가]  최고점: 6864  평균: 6711
세대 2: [선택 → 교차 → 변이 → 평가] 최고점: 7148  평균: 6798
세대 3: ... 최고점: 7355  평균: 6919
...
세대 15: 최고점: 8060  평균: 8026  ← 수렴

(3개 시드 평균 fitness 기준)
```

#### GA vs Random Search 선택 기준

| 상황 | 추천 |
|------|------|
| 초기 아이디어 탐색 | Random Search (100~200개) |
| 생산 최적화 | GA (적은 평가로 꾸준히 좋은 결과) |
| 최고점 단발이 중요 | Random Search (운 좋으면 GA보다 높음) |
| 일관된 성능이 중요 | GA (표준편차 작음) |

### 5.3 확장 예정: GA 개선 방향 (research 완료)

| 개선 사항 | 효과 | 난이도 |
|----------|------|-------|
| elite_frac 0.2 → 0.1 | elite 6→3마리, 다양성 증가 | 쉬움 |
| BLX-α crossover (α=0.5) | 연속변수에 최적화된 교차 | 중간 |
| Deterministic Crowding | 같은 평가 예산으로 multiple layouts 유지 | 중간 |
| Latin Hypercube 초기화 | 초기 population이 search space를 더 고르게 커버 | 쉬움 |
| 적응형 mutation sigma | 다양성에 따라 변이율 자동 조절 | 중간 |

---

## Part 6: 시각화 (Phase E)

### 6.1 단면도 — r-z 평면

가장 중요한 시각화. 화분을 중심축으로 세로로 반 자른 단면.

```
pot_height(cm)
20 ───────────────────┤ 상단 (z축 최대)
    ···················
15                     ⭕ ← 에어룸 (원으로 근사)
    ·· ~~~ ············
10                     ● ← 프루닝 지점
    ·· ~~~ ············
5                      ~~~ ← 뿌리 경로
    ···················
0  ───────────────────┤ 바닥
   r → 0    4    8    12cm
        (중앙)         (벽)
```

- 갈색 = 배양토 (100%, 단일 비율)
- 흰 원 = 에어룸
- 초록 선 = 뿌리 경로 (세대별 색상 구분 가능)
- 빨간 점 = 프루닝 발생 지점

### 6.2 프루닝 분포 히스토그램

프루닝이 z축 기준 lower/middle/upper 중 어디에 집중되었는지 막대그래프로 표시.
(참고: 현재는 lower 쏠림 현상 관찰 — 뿌리가 거의 직하 방향으로만 자라서)

### 6.3 정보 박스

우측 상단에 점수 구성요소, 표면적, 프루닝 횟수, Spread Ratio, 추정 N 흡수량 표시.

---

## Part 7: 설정 가이드 — 모든 Parameter

### 7.1 핵심 설정 (`configs/mvp.json`)

| 필드 | 현재값 (V3) | 설명 | 바꾸면? |
|------|-----------|------|---------|
| **pot.radius_cm** | 12.0 | 화분 반경 (cm) | 크게: 뿌리 더 오래 삶, 느려짐 |
| **pot.height_cm** | 20.0 | 화분 높이 (cm) | 크게: 뿌리 더 오래 삶, 느려짐 |
| **pot.voxel_size_cm** | 0.3 | 복셀 해상도 | 작게: 정밀, 느림 (0.3이 적정) |
| **airroom.max_count** | 10 | 최대 에어룸 개수 | 많게: 프루닝 기회 ↑, 흙손실 ↑ |
| **airroom.radius_range** | [0.8, 1.5] | 에어룸 반경 범위 (cm) | 크게: 프루닝 영역 ↑, 흙손실 ↑ |
| **airroom.pruning_zone_factor** | 1.15 | 프루닝 감지 반경 배율 | 크게: 더 멀리서도 프루닝 감지 |
| **root.initial_roots** | 3 | 시작 뿌리 개수 | 많게: 커버리지 ↑, 느려짐 |
| **root.pruning_probability** | 1.0 | 프루닝 확률 | 낮게: 일부 뿌리가 에어룸 통과 |
| **root.branches_per_pruning** | [2, 6] | 프루닝당 측근 개수 | 넓게: 분기 다양성 ↑ |
| **root.step_size_cm** | 0.25 | 1스텝 전진 거리 (cm) | 작게: 정밀, 느림 |
| **root.noise_deg** | **[8, 15, 25]** 🌟 | 세대별 노이즈 (°) | 4→8°: **실험으로 찾은 최적값** |
| **root.max_angle_deg** | [20, 80, 85] | 세대별 최대 각도 (°) | 크게: 더 옆으로 퍼짐 |
| **tropism.g** | **1.0** 🌟 | 중력 편향 세기 | 1.5→1.0: **실험으로 찾은 최적값** |
| **score.surface_area_weight** | 1.0 | 표면적 가중치 | 크게: 표면적 중시 |
| **score.pruning_weight** | 50.0 | 프루닝 가중치 | 크게: 프루닝 중시 |
| **score.soil_loss_weight** | 1000.0 | 흙손실 패널티 | 크게: 에어룸 개수 억제 |
| **score.uptake_weight** | 2000.0 | 양분흡수 가중치 | M7 활성화 시 |
| **ga.population** | **25** | GA 개체 수 | 30→25: 다양성 ↑ |
| **ga.generations** | 15 | GA 세대 수 | 크게: 더 진화, 느려짐 |
| **ga.elite_frac** | **0.15** | 엘리트 비율 | 0.2→0.15: 다양성 ↑ |
| **ga.mutation_sigma_cm** | **0.8** | 변이 표준편차 (cm) | 1.5→0.8: 세밀한 탐색 |

### 7.2 식물 종 프로필

`configs/species/` 아래에 JSON 파일로 저장:

```json
// monstera.json — 열대식물 (왕성한 성장)
{
  "root": { "initial_roots": 4, "max_generation": 4, "noise_deg": [3, 10, 15] },
  "tropism": { "g": 1.2 }
}

// cactus.json — 건조식물 (느린 성장)
{
  "root": { "initial_roots": 2, "max_generation": 3, "noise_deg": [5, 20, 30] },
  "tropism": { "g": 1.8 }
}
```

사용법: `SimConfig.from_json("configs/species/monstera.json")`

### 7.3 실전 튜닝 순서

에어룸 배치 최적화를 할 때는 **하나씩만 바꿔가며** 효과를 확인:

```
1. airroom.max_count        ← 몇 개가 적정인가? (4→6→8→10)
2. airroom.radius_range     ← 얼마나 커야 효과적인가? ([0.6,1.2] → [0.8,1.5] → [1.0,2.0])
3. root.initial_roots       ← 뿌리가 몇 개나 있어야 에어룸을 잘 만나는가?
4. root.pruning_probability ← 확률을 낮추면 어떤 효과인가? (1.0→0.85→0.7)
5. score.pruning_weight     ← 프루닝을 얼마나 중시할 것인가? (50→30→100)
```

---

## Part 8: 확장성 — 2D → 3D 전략

### 8.1 전체 로드맵

```
[M1~M5] 2D 단면 MVP ── ✅ 구현 완료
    |
[M6] 자원 확산 (diffusion.py) ── ✅ 구현 완료 (pot_13.json 기본 활성화)
    |
[M7] 자원 흡수 (uptake.py)    ── ✅ 구현 완료 (Michaelis-Menten)
    |
[M8] GA 고도화 ── 실험 완료 (V1~V4: 최적 파라미터 도출)
    |   - population=25, elite=0.15, mutation_sigma=0.8
    |   - Deterministic Crowding, 적응형 파라미터 → 계획 수립
    |
[M9] 3D 검증 ── 준비 중
```

### 8.2 2D → 3D 전략 (핵심 비전)

```
┌─────────────────────────────────────────────────────┐
│                    전체 파이프라인                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Step 1] 2D 알고리즘 (탐색용)                         │
│  ─────────────────────────────                       │
│  • 수만 가지 경우의 수를 1초 단위로 스윕                  │
│  • "에어룸 크기 2.3cm, 높이 12cm 일 때 최적" 같은         │
│    수학적 최적값(스윗스팟) 도출                          │
│  • 용도: GA 파라미터 스윕, 설계 공간 탐색                │
│                                                     │
│        ↓ (최적값 전달)                                │
│                                                     │
│  [Step 2] 3D 검증 (검증 및 전시용)                      │
│  ─────────────────────────────                       │
│  • 최적값을 Fusion 360으로 3D 모델링                   │
│  • 3D Python 코드로 소수 케이스만 정밀 실행               │
│  • 예쁜 렌더링 결과물 + 최종 데이터                     │
│  • 용도: IR 자료, 사업계획서, 특허 출원                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 8.3 M6 — 자원 확산 (Cellular Automata) ✅

`src/diffusion.py`에서 구현됨. 2D (r, z) 격자 기반 CA로 수분/양분 분포 계산:

```
run_diffusion(grid, config) → grid.water_map + grid.nutrient_map

알고리즘 (100회 반복 or 수렴까지, convergence_threshold=1e-6):
  1. 초기화: 모든 복셀 water = 0.8 (에어룸은 0)
  2. 중력: gravity_bias(0.2) 비율을 아래 복셀로 이동
  3. 확산: water_diffusion_rate(0.1)로 이웃 4방향 확산
  4. 증발: 표면 복셀에서 evaporation_rate(0.02)만큼 손실
  5. 배수: 바닥 복셀에서 5%씩 배수
  6. 에어룸 복셀은 항상 water=0 유지

nutrient_map: water × nutrient_concentration + 깊이별 보정 (depth_bonus)
  → 표면 근처 양분 높음 (급수/비료 효과: +0.015 mg/cm³)
  → 아래로 갈수록 감소

파이프라인 위치: Phase A(격자 생성) 직후, Phase B(뿌리 성장) 직전
```

### 8.4 M7 — 자원 흡수 (Mass Balance) ✅

`src/uptake.py`에서 구현됨. 각 뿌리 세그먼트의 위치에서 국소 양분 농도를 읽고 흡수량 계산:

```
compute_uptake(root_system, grid, config) → float (mg)

알고리즘:
  각 세그먼트에 대해:
    1. 표면적 (mm²) = 2π × radius × length × 100
    2. 세대별 효율 (Guo 2008): gen1=0.1×, gen2=0.5×, gen3=1.0×
    3. 국소 농도 C_local (grid.nutrient_map에서 위치 조회)

    if model == "mm" (Michaelis-Menten):
      uptake = area × eff × Vmax × C / (Km + C)
      Vmax = 0.001 mg/mm²/day, Km = 0.05 mg/cm³

    elif model == "linear":
      uptake = area × eff × C × uptake_rate
      uptake_rate = 0.0003 mg/mm²/day

    4. 전체 합산

점수 반영: Score += N_uptake × uptake_weight (기본 2000)
  → 0.3mg 흡수 시 약 +600점 기여

파이프라인 위치: Phase B(뿌리 성장) 직후, Phase C(점수 계산) 내에서 실행
```

### 8.5 M8 — GA 고도화

| 현재 | 확장 예정 |
|------|----------|
| Single-point crossover | BLX-α, Simulated Binary Crossover |
| 고정 elite_frac | 적응형 elite pressure |
| 무작위 초기화 | Latin Hypercube Sampling |
| 단일 population | Deterministic Crowding |
| 고정 mutation sigma | 적응형 (population diversity 기반) |

### 8.6 M9 — 3D 시각화

2D 단면을 회전체(Solid of Revolution)로 변환:

```python
# 2D r-z 데이터 → 3D 회전체 (예비 코드)
theta = np.linspace(0, 2*np.pi, 36)  # 36각형 근사
R, T = np.meshgrid(r_coords, theta)
X = R * np.cos(T)
Y = R * np.sin(T)
Z = np.tile(z_coords, (len(theta), 1))
```

### 8.7 외부 데이터베이스 연동 (TRY / FRED)

시뮬레이션 파라미터 보정을 위해 두 외부 DB 사용 예정:

| DB | URL | 특징 | GWC 활용 |
|----|-----|------|---------|
| **FRED 3.0** | roots.ornl.gov | 루트 특화, 330+ traits, 즉시 CSV 다운로드 (112MB) | root diameter → radius 검증, branching intensity, N uptake |
| **TRY** | try-db.org | 전식물, 305K taxa, 요청 시스템 | FRED에 없는 종 커버리지 보완 |

**둘 다 무료, 일반 이메일로 가입 가능** (`.edu`/`.ac.kr` 불필요).

---

## Part 9: 학술 출처와 근거

모든 시뮬레이션 파라미터는 아래 학술 문헌에 근거한다.
DOI/PMC ID로 원문 확인 가능.

| # | 출처 | 인용 | 적용 항목 |
|---|------|------|----------|
| 1 | **Schnepf et al. (2018)** *Ann Bot* 121(5):1033-1053. [PMC5906965](https://pmc.ncbi.nlm.nih.gov/articles/PMC5906965/) | CRootBox 뿌리 아키텍처 프레임워크 | 세대별 분기각, 분기간격 |
| 2 | **Pagès (2014)** *Ann Bot* 114(3):591-598. [PMC4204672](https://pmc.ncbi.nlm.nih.gov/articles/PMC4204672/) | **Allometric radius**: r_child = Dmin + 0.25 × (r_parent − Dmin) | 자식뿌리 반경 계산 |
| 3 | **Pagès (2016)** *Front Plant Sci* 7:1522. [PMC5155602](https://pmc.ncbi.nlm.nih.gov/articles/PMC5155602/) | 140종 단자엽/쌍자엽 IBD 비교 | 분기 간격 검증 |
| 4 | **Guo et al. (2008)** *New Phytol* 180(4):807-818. | 23수종 fine root order 분석 | 세대별 흡수효율 가중치 |
| 5 | **Craig et al. (2025)** *New Phytol* (dataset). [DOI: 10.15485/2524531](https://doi.org/10.15485/2524531) | 77수종 783개 관측, NH₄⁺ Vmax | 양분흡수율 기준 |
| 6 | **North & Nobel (1998)** *New Phytol* 138(2):307-317. | Opuntia 뿌리 탈수 실험 | 프루닝 확정적 과정 근거 |
| 7 | **PLOS ONE (2018)** *Platycladus orientalis* air-pruning | 프루닝 72h 후 측근 6배 증가 | 프루닝→분기 메커니즘 |
| 8 | **YUC9-mediated auxin pathway (2018)** [PMC5921505](https://pmc.ncbi.nlm.nih.gov/articles/PMC5921505/) | 뿌리 절단 → YUC9 활성화 → 옥신 축적 | 프루닝 분자 메커니즘 |
| 9 | **Reid et al. (1998)** *Arabidopsis* root-tip excision [PMC34753](https://pmc.ncbi.nlm.nih.gov/articles/PMC34753/) | 뿌리끝 절단 → 측근 밀도 유의미 증가 | 프루닝→분기 통계 검증 |
| 10 | **McDonald et al.** 사탕수수 뿌리 흡수 | NH₄⁺ Imax 97.5 nmol/cm²/h | 단위면적당 흡수율 |
| 11 | **Iversen et al. (2021)** FRED 3.0 [roots.ornl.gov](https://roots.ornl.gov/) | 4500+ 종 뿌리 형질 데이터베이스 | 종별 파라미터 참조 |
| 12 | **Osmont et al. (2007)** *J Exp Bot* 58(5):909-920. | 측근 형성 호르몬 조절 리뷰 | 3세대 모델 검증 |

---

## 부록: 용어 사전 & FAQ

### 용어 사전

| 용어 | 뜻 |
|------|-----|
| **에어프루닝 (Air-pruning)** | 뿌리 끝이 공기에 닿아 세포 사멸 → 측근 분기 유도 |
| **에어룸 (Airroom)** | 화분 내부의 빈 공간 (정사면체), 프루닝 발생 지점 |
| **프루닝 (Pruning)** | 뿌리 끝 사멸 + 측근 분기 이벤트 |
| **r-z 단면** | 원통 화분의 반경-높이 2D 단면 |
| **복셀 (Voxel)** | 격자 단위 (0.3cm × 0.3cm) |
| **세대 (Generation)** | 뿌리 분기 깊이 (1차→2차→3차) |
| **Genome** | GA에서 하나의 설계안 (에어룸 위치 리스트) |
| **G-Health Score** | 설계안의 우수성을 정량화한 점수 |
| **Spread Ratio** | 뿌리가 방문한 복셀 비율 (공간 활용도) |
| **σ·√dx 스케일링** | step_size 무관 일관된 궤적 보장 기법 |
| **Allometric radius** | 부모-자식 뿌리 반경 간 상관 관계식 |
| **흡수효율** | 세대별 단위면적당 양분 흡수 능력 차이 |

### FAQ

**Q: 왜 2D인가? 3D는 언제?**
A: 지금은 2D 탐색 단계. 수천 가지 배치를 빠르게 스크리닝해서 최적값을 찾는 게 목적.
최적값이 나오면 그 구조로 Fusion 360에서 3D 모델링 후 3D Python으로 검증할 예정.

**Q: 프루닝 확률이 1.0이면 너무 확정적인 거 아닌가?**
A: 생물학적 근거에 따르면 공기프루닝은 습도/온도에 덜 민감한 **확정적 과정**임.
North & Nobel (1998)의 Opuntia 실험에서 뿌리 끝이 공기에 노출되면 거의 항상 사멸.

**Q: 하단(lower)에 프루닝이 몰리는 게 문제인가?**
A: 현재는 중력+노이즈로 인해 관찰되는 현상. 점수에는 반영 안 함 (일단 데이터 수집).
장기적으로는 하단 프루닝이 많은 게 좋은 설계일 수도 있음 (뿌리가 깊이 내려가서
넓게 퍼졌다는 증거).

**Q: GA가 랜덤 서치보다 항상 좋은가?**
A: "평균적으로는" GA가 좋지만, 시드에 따라 랜덤 서치가 더 높은 최고점을 찾을 수도 있음.
GA는 일관성(낮은 표준편차)이 장점. 둘 다 실행해보고 비교하는 걸 권장.

**Q: 최종 목표인 "양분 임계값"은 아직 점수에 없는데?**
A: M7이 구현되어 흡수량 자체는 점수에 반영 중. `uptake_weight=2000` 기본값으로
Score = S×1.0 + P×50 - L×1000 + N×2000. 다만 "식물별 임계값(N mg/day 필요)"
은 종 프로필에 추가 예정 (M8+). 현재는 높은 흡수량 = 높은 점수로 간접 반영.

**Q: 외부 DB(TRY/FRED)는 어떻게 쓰나?**
A: 지금 시뮬레이션 파라미터(뿌리 반경, 분지 각도, 흡수율)는 학술 문헌 기반 추정치.
FRED CSV를 받아서 실제 측정 데이터로 이 값들을 검증/보정할 예정.
필요하면 더보기: 이 문서 §8.7 참조.
