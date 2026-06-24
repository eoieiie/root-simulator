# GWC Root Simulator — 식물 생장 및 뿌리 생물학 지식

> 이 프로젝트를 이해하는 데 필요한 식물 생물학(뿌리 구조, 생장, 호르몬, 영양 흡수)을 정리.
> 시뮬레이션 파라미터의 **생물학적 근거**를 이해하기 위한 참고 자료.

---

## 목차

- [1. 뿌리 시스템 아키텍처 (Root System Architecture)](#1-뿌리-시스템-아키텍처-root-system-architecture)
- [2. 뿌리 세대와 기능 분화 (Root Order)](#2-뿌리-세대와-기능-분화-root-order)
- [3. 뿌리 생장 메커니즘](#3-뿌리-생장-메커니즘)
- [4. 에어프루닝의 생물학 — 분자 수준](#4-에어프루닝의-생물학--분자-수준)
- [5. 굴성 (Tropism)](#5-굴성-tropism)
- [6. Allometric Scaling — 뿌리 굵기 관계](#6-allometric-scaling--뿌리-굵기-관계)
- [7. 영양 흡수 메커니즘](#7-영양-흡수-메커니즘)
- [8. Monstera deliciosa 뿌리 특성](#8-monstera-deliciosa-뿌리-특성)
- [9. Peperomia 뿌리 특성](#9-peperomia-뿌리-특성)
- [10. 시뮬레이션 파라미터의 생물학적 근거 요약](#10-시뮬레이션-파라미터의-생물학적-근거-요약)
- [참고 문헌](#참고-문헌)

---

## 1. 뿌리 시스템 아키텍처 (Root System Architecture)

### 1.1 두 가지 기본 유형

```
[방사형 (Allorhizic)]                       [수상형 (Homorhizic)]
   │                                             │
   ├─ 주근 (taproot) ← 굵고 깊게                   ├─ 여러 개의 가는 뿌리 (fibrous)
   │   ├─ 측근 (lateral root)                     ├─ 모두 비슷한 굵기
   │   ├─ 측근                                    ├─ 얕고 넓게 퍼짐
   │   └─ 측근                                    └─ 벼, 보리, 코코야자 등
   └─ 뿌리털 (root hair)
   (쌍떡잎식물: 참나무, 민들레 등)
```

| 유형 | 특징 | 예 |
|------|------|-----|
| **방사형 (Allorhizic)** | 주근(primary root)이 우세, 거기서 측근 분기 | 쌍떡잎식물, 나무 |
| **수상형 (Homorhizic)** | 주근 없음, 여러 개의 가는 뿌리 | 외떡잎식물, 벼, 보리 |

**Monstera / Peperomia는?**
- Monstera: **부정근형 (adventitious)** — 줄기에서 뿌리가 직접 발생. 전형적인 열대 착생(hemiepiphyte) 구조
- Peperomia: **섬유근형 (fibrous)** — 가늘고 많은 뿌리, 얕게 퍼짐

### 1.2 Root Order (뿌리 차수) 개념

뿌리는 분기 차수(branching order)로 계층을 구분한다 (Fitter 1987, Guo et al. 2008):

```
1차근 (First order): 줄기/주근에서 직접 나온 뿌리. 가장 굵음. 수송 담당.
  ↓
2차근 (Second order): 1차근에서 분기. 중간 굵기. 수송 + 흡수 혼합.
  ↓
3차근 (Third order): 2차근에서 분기. 가늘고 많음. **주요 흡수 담당**.
  ↓
4차근+ (Fourth order+): 더 가늘어지지만, 표면적 기여는 미미.
```

**중요**: 1~3차근이 전체 뿌리 길이의 약 75%를 차지한다 (Guo et al. 2008).
→ 시뮬레이터가 3세대까지인 이유.

```
세대별 기능 분화:

1차근 = "고속도로"
  ─ 굵고 길게 뻗음
  ─ 물/양분을 위로 운송하는 게 주 역할
  ─ 흡수 효율은 낮음 (표피가 코르크화됨)

2차근 = "국도"
  ─ 중간 굵기
  ─ 수송 + 흡수 병행
  ─ 측면으로 퍼져서 토양 탐색

3차근 = "골목길 + 대문"
  ─ 가늘고 많고 짧음
  ─ **실제 흡수의 70% 이상 담당**
  ─ 가장 활발하게 물/양분 흡수
```

---

## 2. 뿌리 세대와 기능 분화 (Root Order)

### 2.1 세대별 형태적 차이 (Guo et al. 2008, 23수종 분석)

| 특성 | 1차근 (First order) | 2차근 (Second order) | 3차근 (Third order) |
|------|:------------------:|:-------------------:|:------------------:|
| **평균 직경** | 1.5~3.0 mm | 0.5~1.5 mm | 0.2~0.5 mm |
| **표피** | 코르크화 (수송 전문화) | 부분 코르크화 | **비코르크화 (흡수 전문화)** |
| **균근 감염** | 거의 없음 | 부분적 | **높음** |
| **생명주기** | 길다 (년 단위) | 중간 | 짧다 (주~월 단위) |
| **측근 분기** | 활발 | 중간 | 드물거나 없음 |
| **흡수 기여도** | 5~10% | 15~25% | **65~80%** |

### 2.2 시뮬레이션에 적용된 세대별 설정

```
┌────────────────────────────────────────────────────────┐
│                    뿌리 세대 구조                        │
├────────────────────────────────────────────────────────┤
│                                                        │
│  초기 뿌리 (initial_roots = 3)                         │
│    │  (r=0, r=voxel/2, r=voxel, z=pot_height)         │
│    ▼                                                    │
│  ┌──────────────────────────────────┐                  │
│  │  1세대 (Primary)                  │                  │
│  │  반경: 0.18 cm                     │                  │
│  │  각도 제한: ±20°, 노이즈: ±4°       │                  │
│  │  흡수효율: ×0.1 (수송 위주)         │                  │
│  │  최대수명: 200 steps               │                  │
│  └────────┬─────────────────────────┘                  │
│           │ 프루닝 or 바닥                             │
│           ▼                                            │
│  ┌──────────────────────────────────┐                  │
│  │  2세대 (Secondary)                │                  │
│  │  반경: 0.0525 cm (allometric)      │                  │
│  │  분기각: ±75°                      │                  │
│  │  각도 제한: ±80°, 노이즈: ±15°      │                  │
│  │  흡수효율: ×0.5 (혼합)             │                  │
│  └────────┬─────────────────────────┘                  │
│           │ 프루닝 or 바닥                             │
│           ▼                                            │
│  ┌──────────────────────────────────┐                  │
│  │  3세대 (Tertiary)                 │                  │
│  │  반경: 0.0206 cm (allometric)      │                  │
│  │  분기각: ±85°                      │                  │
│  │  각도 제한: ±85°, 노이즈: ±25°      │                  │
│  │  흡수효율: ×1.0 (주 흡수)          │                  │
│  │  **더 이상 분기 안 함**             │                  │
│  └──────────────────────────────────┘                  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**3세대에서 멈추는 이유** (Osmont et al. 2007):
- 4차근 이상은 직경이 0.1mm 미만으로, 표면적 기여도가 전체의 5% 미만
- 연산량 대비 효과가 급감
- CRootBox도 기본 3세대 (Schnepf et al. 2018)

---

## 3. 뿌리 생장 메커니즘

### 3.1 정단 성장 (Apical Growth)

뿌리 끝(apical meristem)에서 새로운 세포가 계속 생성되어 **길이가 늘어난다**:

```
뿌리 끝 구조 (종단면):

              뿌리털
  ┌───────●●●●●●●●●●───────┐  ← 성숙대 (maturation zone)
  │                           │     ─ 코르크화, 측근 분기 가능
  ├───●───────────────────────┤
  │                           │  ← 신장대 (elongation zone)
  │                           │     ─ 세포가 길게 늘어남
  ├───●───────────────────────┤
  │                           │  ← 분열대 (meristem zone)
  │        ● ● ●              │     ─ 새 세포 생성 (뿌리 끝)
  └───────┴─────●─────●─────┘
                ↑뿌리골무 (root cap)
```

**팁(tip)이 죽으면**: 분열대가 사라져서 더 이상 길이 생장 불가
→ 이것이 에어프루닝의 본질: **팁 사멸 = 그 뿌리의 길이 생장 종료**

### 3.2 측근 형성 (Lateral Root Formation)

측근은 **내초(pericycle)**에서 발생한다:

```
1. 프루닝/절단 발생
2. 절단 부위에 옥신(auxin) 축적
3. 내초 세포 활성화
4. 세포 분열 시작 → 측근 원기(lateral root primordium)
5. 원기가 표피를 뚫고 나옴 (2~3일)
6. 독립된 정단 분열조직 형성 → 독립 생장 시작
```

**분기 개수 결정 요인**:
- 옥신 농도 (높을수록 더 많은 측근)
- 에틸렌 민감도
- 토양 밀도 (물리적 저항)
- 영양 상태 (질소 부족 시 분기 증가)

시뮬레이션에서는 단순화: `branches_per_pruning = [2, 6]` (균등 분포 랜덤)

### 3.3 생장 속도

실제 뿌리 생장 속도는 종, 온도, 수분에 따라 크게 변한다:

| 식물 | 생장 속도 | 출처 |
|------|----------|------|
| Monstera aerial root | **9.6 ± 5.3 mm/day** | Eskov et al. 2022 |
| Arabidopsis (실험실) | ~0.5 mm/day | 표준 |
| 옥수수 (주근) | ~20 mm/day | 빠른 편 |
| 소나무 (1차근) | ~2 mm/day | 느린 편 |

시뮬레이션은 step 단위의 상대적 생장이라 절대 속도는 중요하지 않음.
step_size는 해상도 결정 파라미터 (0.25cm/step).

---

## 4. 에어프루닝의 생물학 — 분자 수준

### 4.1 정단우성 (Apical Dominance)

```
정상 상태:
  ┌──────────────┐
  │  Auxin (옥신) │→→→→→ 뿌리 끝 (auxin maximum 형성)
  └──────────────┘    ↓
            ↓      정단우성 유지
            ↓      측근 형성 억제
          Cytokinin (사이토카닌)
          - 뿌리 끝에서 합성
          - 측근 원기 발생 억제
```

뿌리 끝에 고농도의 옥신이 유지되면:
- 정단 분열조직이 계속 성장 방향 지시
- 측근 형성에 필요한 내초 세포 분열이 억제됨
- 이게 "주근이 죽어야 측근이 나오는" 이유

### 4.2 프루닝 후 호르몬 변화 (분자 메커니즘)

```
프루닝 발생 (뿌리 끝 사멸):

1. 옥신 소비처(뿌리끝) 소멸
   → 줄기에서 내려오던 옥신이 절단면 위에 축적 (YUC9 경로 활성화)

2. 사이토카닌 공급 중단
   → 측근 억제 신호 제거

3. 절단면 부근 내초 세포 활성화
   → 옥신 농도 ↑ + 사이토카닌 ↓ → 측근 원기 폭발적 형성

4. 2~6개의 측근이 절단면 근처에서 동시 발생
   → 이것이 "프루닝 → 측근 폭발적 분기"의 분자 메커니즘
```

**학술 근거**:
- YUC9-mediated auxin accumulation (2018, PMC5921505): 뿌리 절단 시 YUC9 유전자가 활성화되어 절단 부위에 옥신이 축적됨 → 측근 형성 유도
- Reid et al. (1998, PMC34753): Arabidopsis 뿌리끝 절단 후 측근 밀도가 유의미하게 증가 (P=0.001)

### 4.3 왜 프루닝 확률이 1.0인가

```
공기프루닝(Air-pruning) vs 기계적 절단(mechanical pruning):

공기프루닝:
  - 뿌리 끝이 낮은 습도(<90%)에 노출
  - 세포 내 수분이 급속히 증발
  - 세포막 붕괴 → 세포 사멸
  - **결과: 확정적(death is inevitable)**

기계적 절단:
  - 가위 등으로 자름
  - 상처 부위에서 즉시 호르몬 반응 시작
  - **결과: 확정적(death + response is immediate)**

North & Nobel (1998): Opuntia 뿌리 실험
  - 건조 3일 후 대부분의 apical meristem 사멸 확인
  - 공기 노출 조건에서는 회복 불가능

PLOS ONE (2018): Platycladus orientalis 공기프루닝
  - 에어룸 접촉 후 72h 내 측근 6배 증가 관측
  - 프루닝은 확정적 과정
```

따라서 시뮬레이션에서 `pruning_probability = 1.0`은 생물학적으로 정당화됨.
낮추면 "공기 구멍을 만든 의미가 사라짐"을 의미함.

### 4.4 왜 pruning_zone_factor = 1.15인가

```
pruning_zone_radius = airroom.radius × 1.15

1.15 = 2D 보정 계수 (pragmatic, not biological):

  3D 현실: 뿌리가 원주 방향(θ)으로도 접근 가능
  2D 단면: r-z 평면으로만 접근 가능 (회전 대칭 가정)

  → 2D에서 동일한 접촉 확률을 얻으려면
    영향권 반경을 약간 키워야 함 (2D 기하 보정)

순수 생물학: 뿌리가 공기 구멍에 **실제로 들어가야** 프루닝됨 (×1.0)
2D 보정: ×1.15는 "바로 옆까지 왔으면 접촉한 것으로 간주"하는 정도
```

---

## 5. 굴성 (Tropism)

### 5.1 중력굴성 (Gravitropism) — 현재 유일하게 활성화

모든 식물 뿌리는 **중력 방향으로 자라는** 성질이 있다 (positive gravitropism):

```
mechanism:
  1. 뿌리 끝의 columella 세포에서 전분 입자(statolith)가 중력 방향으로 가라앉음
  2. auxin transporter(PIN 단백질) 재배치
  3. 옥신이 아래쪽으로 집중 → 아래쪽 세포 신장 억제
  4. 위쪽이 더 빨리 자라서 뿌리가 아래로 휨

simulation:
  angle *= (1.0 - tropism.g × 0.02)
  g=1.5: 각 스텝마다 angle이 0(직하) 방향으로 3% 수렴
  g=0.0: 굴성 없음, 순수 랜덤 워크
```

**세대별 중력 반응 차이:**
- 1차근: 중력 반응 강함 (깊이 내려가야 함)
- 2차근: 중력 반응 약함 (옆으로 퍼져야 함)
- 3차근: 중력 반응 최소 (모든 방향으로 흡수 표면 확보)

현재 시뮬레이션은 1차/2차/3차 모두 동일한 `tropism.g` 사용.
→ 생물학적으로는 세대별 중력 가중치가 달라야 하지만 MVP에서는 단순화.

### 5.2 수분굴성 (Hydrotropism) — M6 확장

물이 많은 쪽으로 뿌리가 휘는 성질:

```
v_hydro = ∇(water_concentration) 방향
  → 수분이 많은 쪽으로 뿌리 성장 방향 편향

mechanism:
  - 수분 기울기를 감지하는 별도의 수용체 존재 (MIZ1 유전자)
  - 중력굴성과 독립적으로 작동 가능
  - 중력굴성보다 약함 (보통 가중치 0.2~0.5)

simulation (M6 이후):
  v_target = w_grav × v_grav + w_hydro × v_hydro + w_noise × v_rand
```

### 5.3 화학굴성 (Chemotropism) — M6 확장

영양분이 많은 쪽으로 뿌리가 휘는 성질:

```
v_chem = ∇(nitrate_concentration) 방향
  → 질산염 농도가 높은 쪽으로 성장

현재 관련: 에어룸 근처는 공기 노출로 수분이 적음
  → 수분굴성 활성화 시 뿌리가 에어룸을 오히려 회피할 가능성
  → 에어프루닝 vs 수분 추구의 트레이드오프 발생
  → 이 트레이드오프 자체가 흥미로운 최적화 문제가 됨
```

---

## 6. Allometric Scaling — 뿌리 굵기 관계

### 6.1 부모-자식 뿌리 반경 관계

자식 뿌리는 부모보다 가늘다. 이 관계는 **allometric(상대성장)** 공식으로 설명된다:

```
Pagès (2014) 공식:

  r_child = D_min + slope × (r_parent - D_min)

  D_min = 0.01 cm    — 가장 가는 기능성 뿌리의 직경 (≈0.1mm)
  slope = 0.25       — 45종 쌍떡잎식물 평균값

  의미: 자식은 부모 굵기의 25%만 유지한다 (75% 감소)
```

**왜 D_min이 필요한가**:
- slope가 아무리 작아도 뿌리 직경이 0이 될 수는 없음
- D_min = 0.01cm는 세포 수준의 최소 기능성 뿌리 직경
- 실제로 이 이하로 가늘어지면 물관부가 형성될 공간이 부족

### 6.2 적용 예시

```
Parent radius = 0.18 cm (1차근):
  r_child = 0.01 + 0.25 × (0.18 - 0.01)
         = 0.01 + 0.25 × 0.17
         = 0.01 + 0.0425
         = 0.0525 cm (2차근)

Parent radius = 0.0525 cm (2차근):
  r_child = 0.01 + 0.25 × (0.0525 - 0.01)
         = 0.01 + 0.25 × 0.0425
         = 0.01 + 0.010625
         = 0.0206 cm (3차근)

비교: 이전 고정값 [0.18, 0.10, 0.04]
  → 2차근이 0.10→0.0525로 절반 감소
  → 3차근이 0.04→0.0206로 절반 감소
  → 생물학적으로 더 현실적 (Guo et al. 2008: 3차근 직경 0.2~0.5mm)
```

### 6.3 표면적에 미치는 영향

뿌리 표면적 = 2π × r × L (원통 근사).

반경이 절반이 되면 → 같은 길이일 때 표면적도 절반.
그러나 3차근이 1차근보다 **훨씬 많고** (분기로 인해), **흡수 효율이 높아서**
(×1.0 vs ×0.1), 전체 양분 흡수량은 오히려 증가함.

---

## 7. 영양 흡수 메커니즘

### 7.1 기본 개념

뿌리는 **수동(apoplast) + 능동(symplast)** 경로로 양분을 흡수:

```
토양 용액 → 뿌리 표면 → 표피 → 피층 → 중심주 → 물관부 → 줄기
            (apoplast)          (symplast)   (xylem)
```

### 7.2 Michaelis-Menten 흡수 동역학

뿌리의 영양 흡수는 효소 반응과 유사한 포화 곡선을 따른다:

```
Uptake = S × Vmax × C / (Km + C)

S = 뿌리 표면적 (mm²)
Vmax = 최대 흡수 속도 (µg/mm²/h)
C = 토양 용액 내 영양 농도 (µM)
Km = 반포화 상수 (µM) — 흡수율이 Vmax의 절반이 되는 농도
```

**중요**: 저농도에서는 선형 근사 (C << Km일 때 Uptake ∝ C × S)
고농도에서는 포화 (C >> Km일 때 Uptake = S × Vmax)

M7 구현 완료: 기본값 Michaelis-Menten 모델 사용 (config `uptake.model: "mm"`).
선형 모델(`"linear"`)도 지원.

### 7.3 세대별 흡수 효율 차이

```
1차근: 효율 ×0.1 (코르크화된 표피, 수송 전문화)
2차근: 효율 ×0.5 (부분 흡수 가능)
3차근: 효율 ×1.0 (비코르크화 표피, 활발한 흡수)

전체 추정 흡수량 = Σ(S_gen × efficiency_gen) × 0.0003 mg/mm²/day
```

흡수율 0.0003 mg/mm²/day의 근거:
- McDonald et al.: 사탕수수 NH₄⁺ Imax = 97.5 nmol/cm²/h
- ≈ 30 µg/cm²/day ≈ 0.0003 mg/mm²/day
- Craig et al. (2025): 77수종 NH₄⁺ Vmax 중간값 6.67 µmol/g/h

### 7.4 뿌리 깊이와 영양 흡수

뿌리가 lower(하단)에 집중되어도 전체 양분 흡수에 문제가 없는 이유:

```
1. 토양 내 영양분 이동:
   - 질산염(NO₃⁻): 물과 함께 이동, 깊이까지 도달 가능
   - 인산(PO₄³⁻): 확산 속도 느림, 표면 근처 필요
   - 칼륨(K⁺): 중간 정도 이동성

2. 물의 이동:
   - 화분 상단에서 급수 → 중력으로 아래로 이동
   - 하단 뿌리도 물 흡수 가능 (물이 내려오니까)

3. 그러나 M6(자원 확산) 추가 후:
   - 상단: 물/양분 많음 (급수 지점과 가까움)
   - 하단: 물 빠지고 산소 많음
   → 이때는 lower 쏠림이 실제로 상단 양분을 못 먹게 할 수도 있음
   → "하단 프루닝 쏠림이 좋은가"는 M6 이후 데이터로 결정
```

---

## 8. Monstera deliciosa 뿌리 특성

### 8.1 기본 정보

| 항목 | 내용 |
|------|------|
| 학명 | Monstera deliciosa Liebm. |
| 과 | Araceae (천남성과) |
| 생태형 | Nomadic vine / Secondary hemiepiphyte |
| 원산 | 멕시코~파나마 열대우림 |
| 생장형태 | 착생 시작 → 지상으로 내려와 정착 → 다시 상승 |

### 8.2 뿌리 유형 (3가지, Hinchee 1981)

```
1. Anchor roots (부착근):
   - 회색, 짧고 가지 침
   - 지름: 5~8 mm
   - 기능: 나무 표면에 부착
   - 흙에 닿지 않음

2. Feeder roots (급양근):
   - 암갈색, 길게 늘어짐 (최대 10m+)
   - 지름: 7~15 mm (가장 굵음)
   - 자연 상태에서는 **가지치 않음** (pruning되면 분기)
   - 기능: 물/양분 흡수 + 수송
   - 자유롭게 공중에 매달림

3. Lateral-subterranean roots (지중 측근):
   - 지름: ~2~5 mm
   - 기능: 토양 내에서 흡수
   - 유일하게 토양 내에서 분기하는 뿌리
```

**시뮬레이션 관점**: Monstera의 지중 뿌리는 대부분 **제한된 분기**를 가짐.
자연 상태에서는 feeder root는 거의 분기하지 않음 (pruning이 필요).

### 8.3 생장 데이터

| 측정 항목 | 값 | 출처 |
|----------|-----|------|
| 공중뿌리 생장 속도 | 9.6 ± 5.3 mm/일 | Eskov et al. 2022 |
| 공중뿌리 직경 | 5.3 ± 1.4 mm | Eskov et al. 2022 |
| 급양근 직경 | 7~15 mm | Cedeño-Fonseca et al. 2020 |
| 부착근 직경 | 5~8 mm | Cedeño-Fonseca et al. 2020 |
| 신장대 길이 | ~3~10 cm (굵은 뿌리일수록 김) | Eskov et al. 2022 |
| 뿌리압 | 최대 225 kPa (M. acuminata) | López-Portillo et al. 2000 |

### 8.4 시뮬레이션 파라미터 권장

```
화분: 15 cm diameter (radius=7.5cm), 높이 13.1cm
초기 뿌리: 3개 (adventitious roots from stem base)
1차근 반경: 0.25 cm (Monstera 지중 뿌리 ~5mm 직경의 절반)
분기: feeder roots는 자연에서 거의 분기 안 함
  → pruning 유도가 특히 중요함 (안 하면 1차근만 죽 계속 감)
```

---

## 9. Peperomia 뿌리 특성

### 9.1 기본 정보

| 항목 | 내용 |
|------|------|
| 학명 | Peperomia obtusifolia (L.) A.Dietr. |
| 과 | Piperaceae (후추과) |
| 생태형 | Facultative epiphyte (선택적 착생) |
| 원산 | 플로리다~멕시코~카리브 |
| 생장형태 | 낮게 퍼짐, 덤불형 |

### 9.2 뿌리 특성

```
뿌리 유형: 섬유근 (fibrous root system)
  - 가늘고 많은 뿌리 (0.5~1mm 직경)
  - 주근(primary root) 없음
  - 얕고 넓게 퍼짐 (25cm 식물 → 뿌리 깊이 ~10~13cm)
  - 표면적이 넓은 흡수 시스템

생장 형태:
  - Epiphytic: 수목 표면에 얕게 퍼짐
  - Terrestrial: 배수가 잘 되는 토양에서도 얕게 퍼짐
  
화분 특성:
  - 넓고 얕은 화분(azalea pot) 선호
  - 깊은 화분은 하단에 산소 부족(oxygen desert) 발생
  - 권장 화분 깊이: 10~15cm
```

### 9.3 생장 데이터

| 측정 항목 | 값 | 출처 |
|----------|-----|------|
| 지상부 높이 | 15~35 cm | UF/IFAS, 상업 자료 |
| 퍼짐 | 30~60 cm | UF/IFAS |
| 권장 화분 | 직경 9~12 cm | IKEA care guide |
| 뿌리 깊이 | 10~13 cm (allometric) | PeperomiaObtusifolia.com |
| 생장 속도 | 느림~중간 | 일반 관찰 |
| 근권 특성 | 얕고, 넓고, 조밀 | 다수 출처 |

### 9.4 시뮬레이션 파라미터 권장

```
화분: 12 cm diameter (radius=6.0cm), 높이 10.3cm
초기 뿌리: 5개 (fibrous이므로 Monstera보다 많게)
1차근 반경: 0.05 cm (Peperomia는 원래 얇음, 1차/2차 구분이 모호)
분기: 활발함 (fibrous system의 특징)
잔뿌리 중심: 3차근의 비중이 큼 (전체 표면적의 80%+)
```

---

## 10. 시뮬레이션 파라미터의 생물학적 근거 요약

| 파라미터 | 값 | 생물학적 근거 |
|---------|-----|-------------|
| initial_roots = 3 | 여러 adventitious root / fibrous root 시작점 대표 |
| max_generation = 3 | 1~3차근이 전체 흡수 길이의 75% (Guo 2008) |
| pruning_probability = 1.0 | 공기프루닝은 확정적 탈수 과정 (North & Nobel 1998) |
| pruning_zone_factor = 1.15 | 2D 기하 보정, 생물학적 근거는 ×1.0 |
| radii_cm allometric slope=0.25 | 45종 평균 (Pagès 2014, 범위 0.14~0.36) |
| noise_deg [4, 15, 25] | 1차=곧게, 3차=구불구불 (CRootBox 패턴) |
| max_angle_deg [20, 80, 85] | 세대별 분기각 제한 (Schnepf 2018) |
| branch_angle [±75, ±85] | CRootBox 분기각 규칙 |
| tropism.g = 1.5 | 강한 중력굴성 (뿌리는 원래 아래로 감) |
| 흡수효율 gen1=0.1, gen3=1.0 | Guo et al. (2008) 23수종 정량 분석 |
| 흡수율 0.0003 mg/mm²/day | McDonald et al. 사탕수수 Imax, Craig et al. 2025 검증 |
| max_segment_steps [200, 200, 150] | 기술적 제한 (생물학적 수명 대신 시뮬레이션 예산) |

---

## 참고 문헌

1. **Hinchee, M.A. (1981)** *Morphogenesis of aerial and subterranean roots of Monstera deliciosa.* Bot. Gaz. 142(3):347-359.
2. **Cedeño-Fonseca, M. et al. (2020)** *A comparison of Monstera deliciosa and M. tacanaensis.* Aroideana 43(1-2):32-73.
3. **Eskov, A.K. et al. (2022)** *Cellular Growth in Aerial Roots Differs From That in Typical Substrate Roots.* Front. Plant Sci. 13:894647. [PMC9199517](https://pmc.ncbi.nlm.nih.gov/articles/PMC9199517/)
4. **Guo, D. et al. (2008)** *Endogenous and exogenous controls of root life span.* New Phytol. 180(4):807-818.
5. **Pagès, L. (2014)** *Branching patterns of root systems.* Ann. Bot. 114(3):591-598. [PMC4204672](https://pmc.ncbi.nlm.nih.gov/articles/PMC4204672/)
6. **Schnepf, A. et al. (2018)** *CRootBox: a structural-functional modelling framework.* Ann. Bot. 121(5):1033-1053. [PMC5906965](https://pmc.ncbi.nlm.nih.gov/articles/PMC5906965/)
7. **North, G.B. & Nobel, P.S. (1998)** *Water uptake and structural plasticity of roots.* New Phytol. 138(2):307-317.
8. **Reid, J.B. et al. (1998)** *Root-tip excision and lateral root formation in Arabidopsis.* Plant Physiol. [PMC34753](https://pmc.ncbi.nlm.nih.gov/articles/PMC34753/)
9. **Osmont, K.S. et al. (2007)** *Hidden branches: developments in root system architecture.* J. Exp. Bot. 58(5):909-920.
10. **Craig, M.E. et al. (2025)** *Global root trait dataset.* New Phytol. [DOI: 10.15485/2524531](https://doi.org/10.15485/2524531)
11. **McDonald, A.J.S. et al.** *Sugarcane root NH4+ uptake kinetics.* Imax ≈ 97.5 nmol/cm²/h.
12. **Fitter, A.H. (1987)** *An architectural approach to the comparative ecology of plant root systems.* New Phytol. 106:61-77.
