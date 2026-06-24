"""설정 로드/검증/기본값 관리 모듈.

plan.md §13 config.json 예시 구현.
MVP는 JSON 파일에서 로드하고, 누락된 항목은 기본값으로 채운다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── 흙 종류 ID 매핑 ──────────────────────────────────────────
SOIL_TYPES: Dict[str, int] = {
    "배양토": 0,
    "펄라이트": 1,
    "마사토": 2,
    "바크": 3,
}
SOIL_NAMES: Dict[int, str] = {v: k for k, v in SOIL_TYPES.items()}

# ── 하위 Config dataclass ────────────────────────────────────


@dataclass
class PotConfig:
    """화분 형상 및 복셀 해상도."""
    radius_cm: float = 12.0
    height_cm: float = 20.0
    voxel_size_cm: float = 0.5


@dataclass
class SoilConfig:
    """흙 배합. mix는 {이름: 비율} 형태 (비율 합 = 1.0)."""
    mix: Dict[str, float] = field(default_factory=lambda: {"배양토": 0.6, "펄라이트": 0.4})


@dataclass
class AirroomConfig:
    """에어룸 형상 및 생성 파라미터."""
    max_count: int = 10
    radius_range_cm: List[float] = field(default_factory=lambda: [0.8, 1.5])
    pruning_zone_factor: float = 1.25
    shape: str = "tetrahedron"


@dataclass
class TropismConfig:
    """주(방향성) 가중치. phase1.py의 g+h+n softmax 모델 참조.

    g (gravitropism): 아래 방향 편향 (중력)
    h (hydrotropism): 수분 방향 편향 (M6에서 활성화)
    n (nutrient tropism): 영양분 방향 편향 (M7에서 활성화)
    beta: softmax sharpness (클수록 가장 높은 점수 방향으로 결정적)
    """
    g: float = 1.0
    h: float = 0.0
    n: float = 0.0
    softmax_beta: float = 1.0


@dataclass
class RootConfig:
    """뿌리 성장 파라미터.

    radii_cm / noise_deg / max_angle_deg / branch_angle_* 는
    각각 [gen1, gen2, gen3, ...] 순서. 길이는 max_generation과 일치해야 함.

    식물 종별 프로필은 configs/species/ 아래 JSON 템플릿 참조.
    """
    initial_roots: int = 3
    max_generation: int = 3
    pruning_probability: float = 0.4
    branches_per_pruning: List[int] = field(default_factory=lambda: [2, 6])
    step_size_cm: float = 0.4

    # 세대별 파라미터 (index 0 = 1세대, index 1 = 2세대, ...)
    radii_cm: List[float] = field(default_factory=lambda: [0.18, 0.10, 0.04])
    max_segment_steps: List[int] = field(default_factory=lambda: [200, 200, 150])
    """세대별 세그먼트 최대 수명(스텝). 초과 시 자연 소멸."""
    noise_deg: List[float] = field(default_factory=lambda: [8.0, 15.0, 25.0])
    max_angle_deg: List[float] = field(default_factory=lambda: [40.0, 80.0, 85.0])
    branch_angle_min: List[float] = field(default_factory=lambda: [0.0, -75.0, -85.0])
    branch_angle_max: List[float] = field(default_factory=lambda: [0.0, 75.0, 85.0])


@dataclass
class ScoreConfig:
    """G-Health Score 가중치.

    Score = surface × surface_area_weight
          + pruning_count × pruning_weight
          - soil_loss_ratio × soil_loss_weight
          + n_uptake × uptake_weight                    (M7, enabled)

    - surface: mm² 단위, 보통 3000~12000 (주축)
    - pruning: 프루닝 1회당 가중치. 프루닝→분기→표면적 증가를 직접 보상.
               학술적 근거: Platycladus air-pruning 연구 (PLOS ONE 2018)에서
               프루닝 후 측근 6배 증가 확인. Reid et al. (1998) Arabidopsis
               뿌리절단 실험에서 측근 밀도 유의미 증가 (P=0.001).
    - soil_loss: 에어룸 체적 비율 패널티. 높을수록 흙손실 적게 유도.
    - uptake_weight: 양분 흡수량(mg)당 점수 기여. (M7, 기본 2000)
    """
    surface_area_weight: float = 1.0
    pruning_weight: float = 50.0
    soil_loss_weight: float = 1000.0
    uptake_weight: float = 2000.0


@dataclass
@dataclass
class DiffusionConfig:
    """M6: Cellular Automata 자원 확산 파라미터.

    initial_water_content: 급수 후 초기 수분 함량 (0~1)
    water_diffusion_rate: 확산 계수 (클수록 빨리 퍼짐)
    gravity_bias: 중력에 의한 하향 이동 비율
    evaporation_rate: 표면 증발률 (iter당)
    max_iterations: CA 최대 반복 횟수
    convergence_threshold: 수렴 판정 임계값
    nutrient_concentration: 물 대비 양분 농도 비율 (mg/cm³)
    """
    enabled: bool = False
    initial_water_content: float = 0.8
    water_diffusion_rate: float = 0.15
    gravity_bias: float = 0.3
    evaporation_rate: float = 0.02
    max_iterations: int = 80
    convergence_threshold: float = 1e-6
    nutrient_concentration: float = 0.05


@dataclass
class UptakeConfig:
    """M7: Michaelis-Menten 양분 흡수 파라미터.

    model: "linear" (선형) or "mm" (Michaelis-Menten)
    uptake_rate: 선형 모델 단위면적당 흡수율 (mg/mm²/day) ≈ 30 µg/cm²/day
    vmax_nitrogen: MM 최대 흡수 속도 (mg/mm²/day)
    km_nitrogen: MM 반포화 상수 (mg/cm³)
    """
    enabled: bool = False
    model: str = "mm"
    uptake_rate: float = 0.0003
    vmax_nitrogen: float = 0.001
    km_nitrogen: float = 0.05


@dataclass
class SearchConfig:
    """탐색 (랜덤/GA) 파라미터.

    n_eval_seeds: 설계당 평가용 시드 수 (1=단일시드, 3+=확률적 잡음 제거).
                  클수록 robust하지만 N배 느려짐.
    """
    method: str = "random"
    n_candidates: int = 100
    top_k: int = 5
    n_eval_seeds: int = 3


@dataclass
class GAConfig:
    """유전 알고리즘 파라미터.

    population: 한 세대 개체 수
    generations: 총 세대 수
    elite_frac: 상위 몇 %를 다음 세대에 그대로 유지
    mutation_sigma_cm: 에어룸 위치 변이 표준편차 (cm)
    airroom_count: 개체당 에어룸 개수
    """
    population: int = 20
    generations: int = 10
    elite_frac: float = 0.25
    mutation_sigma_cm: float = 1.0
    airroom_count: int = 10


# ── 최상위 Config ────────────────────────────────────────────


@dataclass
class SimConfig:
    """전체 시뮬레이션 설정.

    plan.md의 config.json 예시에 대응.
    확장 기능은 extension 슬롯으로 꺼두고, 나중에 enabled=true로 켠다.
    """
    pot: PotConfig = field(default_factory=PotConfig)
    soil: SoilConfig = field(default_factory=SoilConfig)
    airroom: AirroomConfig = field(default_factory=AirroomConfig)
    root: RootConfig = field(default_factory=RootConfig)
    tropism: TropismConfig = field(default_factory=TropismConfig)
    score: ScoreConfig = field(default_factory=ScoreConfig)
    diffusion: DiffusionConfig = field(default_factory=DiffusionConfig)
    uptake: UptakeConfig = field(default_factory=UptakeConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    ga: GAConfig = field(default_factory=GAConfig)

    ga_enabled: bool = False

    seed: int = 42
    """재현성 확보용 난수 시드."""

    # ── factory methods ──────────────────────────────────────

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SimConfig":
        """중첩 dict를 SimConfig로 변환."""
        cfg = cls()

        if "pot" in d:
            cfg.pot = PotConfig(**d["pot"])
        if "soil" in d:
            cfg.soil = SoilConfig(**d["soil"])
        if "airroom" in d:
            cfg.airroom = AirroomConfig(**d["airroom"])
        if "root" in d:
            cfg.root = RootConfig(**d["root"])
        if "tropism" in d:
            cfg.tropism = TropismConfig(**d["tropism"])
        if "score" in d:
            cfg.score = ScoreConfig(**d["score"])
        if "search" in d:
            cfg.search = SearchConfig(**d["search"])
        if "diffusion" in d:
            cfg.diffusion = DiffusionConfig(**d["diffusion"])
        if "uptake" in d:
            cfg.uptake = UptakeConfig(**d["uptake"])
        if "ga" in d:
            cfg.ga = GAConfig(**d["ga"])
        if "seed" in d:
            cfg.seed = int(d["seed"])

        # 확장 슬롯 (이전 JSON 호환)
        ext = d.get("_extension_slots", {})
        if ext:
            cfg.diffusion.enabled = ext.get("diffusion", {}).get("enabled", False)
            upt = ext.get("uptake", {})
            cfg.uptake.enabled = upt.get("enabled", False)
            cfg.uptake.model = upt.get("model", "linear")
            cfg.ga_enabled = ext.get("ga", {}).get("enabled", False)

        return cfg

    @classmethod
    def from_json(cls, path: str | Path) -> "SimConfig":
        """JSON 파일에서 설정 로드."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"설정 파일 없음: {path}")
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        return cls.from_dict(d)

    # ── 검증 ─────────────────────────────────────────────────

    def validate(self) -> List[str]:
        """설정값 검증. 문제가 있으면 오류 메시지 리스트 반환."""
        errors: List[str] = []

        if self.pot.radius_cm <= 0:
            errors.append("pot.radius_cm > 0 이어야 함")
        if self.pot.height_cm <= 0:
            errors.append("pot.height_cm > 0 이어야 함")
        vs = self.pot.voxel_size_cm
        if vs <= 0 or vs > self.pot.radius_cm:
            errors.append(f"pot.voxel_size_cm({vs}) 가 부적절함")

        if self.airroom.max_count < 0:
            errors.append("airroom.max_count >= 0")
        r0, r1 = self.airroom.radius_range_cm
        if r0 <= 0 or r1 < r0:
            errors.append("airroom.radius_range_cm 부적절함")
        if self.airroom.pruning_zone_factor < 1.0:
            errors.append("pruning_zone_factor >= 1.0 이어야 함")

        rc = self.root
        if rc.max_generation < 1:
            errors.append("root.max_generation >= 1")
        if not (0 <= rc.pruning_probability <= 1):
            errors.append("root.pruning_probability 는 0~1 사이")
        b0, b1 = rc.branches_per_pruning
        if b0 < 0 or b1 < b0:
            errors.append("root.branches_per_pruning 부적절함")
        # 세대별 파라미터 길이 검증
        ngen = rc.max_generation
        if len(rc.radii_cm) != ngen:
            errors.append(f"root.radii_cm 길이({len(rc.radii_cm)}) != max_generation({ngen})")
        if len(rc.max_segment_steps) != ngen:
            errors.append(f"root.max_segment_steps 길이({len(rc.max_segment_steps)}) != max_generation({ngen})")
        if len(rc.noise_deg) != ngen:
            errors.append(f"root.noise_deg 길이({len(rc.noise_deg)}) != max_generation({ngen})")
        if len(rc.max_angle_deg) != ngen:
            errors.append(f"root.max_angle_deg 길이({len(rc.max_angle_deg)}) != max_generation({ngen})")
        if len(rc.branch_angle_min) != ngen or len(rc.branch_angle_max) != ngen:
            errors.append("root.branch_angle_{min,max} 길이 불일치")
        for i in range(ngen):
            if rc.branch_angle_min[i] > rc.branch_angle_max[i]:
                errors.append(f"root.branch_angle [{i}] min > max")

        s = self.search
        if s.method not in ("random", "ga"):
            errors.append(f"search.method = {s.method!r}, 'random' 또는 'ga' 필요")
        if s.n_candidates < 1:
            errors.append("search.n_candidates >= 1")
        if s.top_k < 1 or s.top_k > s.n_candidates:
            errors.append("top_k 는 1~n_candidates 사이")

        return errors

    def to_dict(self) -> dict:
        """설정을 JSON 직렬화 가능 dict로 변환."""
        return {
            "pot": {
                "radius_cm": self.pot.radius_cm,
                "height_cm": self.pot.height_cm,
                "voxel_size_cm": self.pot.voxel_size_cm,
            },
            "soil": {"mix": dict(self.soil.mix)},
            "airroom": {
                "max_count": self.airroom.max_count,
                "radius_range_cm": list(self.airroom.radius_range_cm),
                "pruning_zone_factor": self.airroom.pruning_zone_factor,
                "shape": self.airroom.shape,
            },
            "root": {
                "initial_roots": self.root.initial_roots,
                "max_generation": self.root.max_generation,
                "pruning_probability": self.root.pruning_probability,
                "branches_per_pruning": list(self.root.branches_per_pruning),
                "step_size_cm": self.root.step_size_cm,
                "radii_cm": list(self.root.radii_cm),
                "max_segment_steps": list(self.root.max_segment_steps),
                "noise_deg": list(self.root.noise_deg),
                "max_angle_deg": list(self.root.max_angle_deg),
                "branch_angle_min": list(self.root.branch_angle_min),
                "branch_angle_max": list(self.root.branch_angle_max),
            },
            "tropism": {
                "g": self.tropism.g,
                "h": self.tropism.h,
                "n": self.tropism.n,
                "softmax_beta": self.tropism.softmax_beta,
            },
            "score": {
                "surface_area_weight": self.score.surface_area_weight,
                "pruning_weight": self.score.pruning_weight,
                "soil_loss_weight": self.score.soil_loss_weight,
                "uptake_weight": self.score.uptake_weight,
            },
            "diffusion": {
                "enabled": self.diffusion.enabled,
                "initial_water_content": self.diffusion.initial_water_content,
                "water_diffusion_rate": self.diffusion.water_diffusion_rate,
                "gravity_bias": self.diffusion.gravity_bias,
                "evaporation_rate": self.diffusion.evaporation_rate,
                "max_iterations": self.diffusion.max_iterations,
                "convergence_threshold": self.diffusion.convergence_threshold,
                "nutrient_concentration": self.diffusion.nutrient_concentration,
            },
            "uptake": {
                "enabled": self.uptake.enabled,
                "model": self.uptake.model,
                "uptake_rate": self.uptake.uptake_rate,
                "vmax_nitrogen": self.uptake.vmax_nitrogen,
                "km_nitrogen": self.uptake.km_nitrogen,
            },
            "search": {
                "method": self.search.method,
                "n_candidates": self.search.n_candidates,
                "top_k": self.search.top_k,
                "n_eval_seeds": self.search.n_eval_seeds,
            },
            "ga": {
                "population": self.ga.population,
                "generations": self.ga.generations,
                "elite_frac": self.ga.elite_frac,
                "mutation_sigma_cm": self.ga.mutation_sigma_cm,
                "airroom_count": self.ga.airroom_count,
            },
            "seed": self.seed,
            "_extension_slots": {
                "diffusion": {"enabled": self.diffusion.enabled},
                "uptake": {"enabled": self.uptake.enabled, "model": self.uptake.model},
                "ga": {"enabled": self.ga_enabled},
            },
        }

    def to_json(self, path: str | Path, indent: int = 2) -> None:
        """설정을 JSON 파일로 저장."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=indent)