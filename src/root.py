"""뿌리 성장 + 에어프루닝 + 표면적 계산 모듈.

세대별 파라미터(반경/노이즈/각도)는 config.root.* 에서 읽음.
plan.md §4 Phase B, 부록 A3 참조.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from .config import SimConfig
from .grid import VoxelGrid
from .geometry import Airroom


class RootSegment:
    """하나의 뿌리 세그먼트 (분기점~팁 또는 시작점~팁).

    하나의 세그먼트 = 하나의 뿌리 조각. 팁이 자라면서 end_r/end_z가 갱신된다.
    프루닝되면 active=False, pruned=True가 되고, 부모 노드에서 자식 세그먼트들이 분기된다.
    """
    __slots__ = (
        "id", "generation", "radius", "start_r", "start_z",
        "end_r", "end_z", "angle", "length",
        "parent_id", "active", "pruned",
        "max_lifetime", "steps_lived",
    )

    def __init__(
        self,
        seg_id: int,
        generation: int,
        radius: float,
        start_r: float,
        start_z: float,
        parent_id: Optional[int] = None,
        initial_angle: float = 0.0,
        max_lifetime: int = 200,
    ):
        self.id = seg_id
        self.generation = generation
        self.radius = radius
        self.start_r = start_r
        self.start_z = start_z
        self.end_r = start_r  # 팁 위치, 성장하며 갱신
        self.end_z = start_z
        self.angle = initial_angle  # 현재 성장 방향 (rad, 0=직하)
        self.length = 0.0  # 누적 길이 (cm)
        self.parent_id = parent_id
        self.active = True  # 팁이 살아서 자라는 중
        self.pruned = False  # 프루닝되어 종료됨
        self.max_lifetime = max_lifetime  # 이 세그먼트가 살 수 있는 최대 스텝
        self.steps_lived = 0  # 지금까지 살아온 스텝 수


class RootSystem:
    """뿌리 성장 + 에어프루닝 시뮬레이션 관리자.

    사용법:
        system = RootSystem(config, grid, airrooms, rng=rng)
        system.run(max_steps=500)
        print(system.total_surface_area())
        print(system.pruning_count())
    """

    def __init__(
        self,
        config: SimConfig,
        grid: VoxelGrid,
        airrooms: List[Airroom],
        rng: Optional[random.Random] = None,
    ):
        self.config = config
        self.grid = grid
        self.airrooms = airrooms
        self.rng = rng or random.Random(config.seed)

        self.segments: List[RootSegment] = []
        self.pruning_locations: List[Tuple[float, float, int]] = []
        self._next_id: int = 0
        self.step_count: int = 0
        self._init_roots()

    # ── 초기화 ─────────────────────────────────────────

    def _new_id(self) -> int:
        rid = self._next_id
        self._next_id += 1
        return rid

    def _init_roots(self) -> None:
        """초기 뿌리(1세대)를 화분 상단에 생성.

        initial_roots > 1이면 r축으로 살짝 퍼뜨려서
        각기 다른 경로로 성장하게 함.
        """
        n = self.config.root.initial_roots
        rc = self.config.root
        rad = rc.radii_cm[0]
        lifetime = rc.max_segment_steps[0]
        top_z = self.config.pot.height_cm
        vs = self.config.pot.voxel_size_cm
        for i in range(n):
            if n == 1:
                start_r = 0.0
            else:
                start_r = vs * 0.5 * i
            self.segments.append(RootSegment(
                seg_id=self._new_id(),
                generation=1,
                radius=rad,
                start_r=start_r,
                start_z=top_z,
                initial_angle=0.0,
                max_lifetime=lifetime,
            ))

    # ── 속성 ────────────────────────────────────────────

    @property
    def active_segments(self) -> List[RootSegment]:
        return [s for s in self.segments if s.active]

    @property
    def num_active(self) -> int:
        return sum(1 for s in self.segments if s.active)

    # ── 성장 루프 ──────────────────────────────────────

    def step(self) -> int:
        """한 성장 스텝. 모든 활성 팁을 전진시키고 프루닝 검사.

        Returns:
            이 스텝 후 활성 팁 개수 (0 = 전부 죽음)
        """
        step_sz = self.config.root.step_size_cm

        for seg in list(self.active_segments):
            gen_idx = seg.generation - 1
            rc = self.config.root
            tc = self.config.tropism
            # 1. 방향 갱신 = 중력 트로피즘 + 노이즈 (σ·√dx 스케일링) + h/n placeholder
            # GitHub phase1.py의 g+h+n softmax 모델 참조, 각도 기반으로 이식
            #
            # 중력: angle을 0(직하) 쪽으로 당김
            # h/n: 수분/영양분 구배 방향 (M6/M7에서 활성화, 지금은 0)
            if tc.g > 0:
                seg.angle *= (1.0 - tc.g * 0.02)
            noise_deg = rc.noise_deg[gen_idx] if gen_idx < len(rc.noise_deg) else 10.0
            noise_deg *= math.sqrt(step_sz / 0.4)
            max_deg = rc.max_angle_deg[gen_idx] if gen_idx < len(rc.max_angle_deg) else 90.0
            noise = math.radians(self.rng.uniform(-noise_deg, noise_deg))
            seg.angle += noise
            max_rad = math.radians(max_deg)
            seg.angle = max(-max_rad, min(max_rad, seg.angle))

            # 2. 전진: dr = step * sin(θ), dz = -step * cos(θ) (z는 아래로 감소)
            dr = step_sz * math.sin(seg.angle)
            dz = -step_sz * math.cos(seg.angle)
            new_r = seg.end_r + dr
            new_z = seg.end_z + dz

            # 3. 경계 처리
            # 중심축(r<0)는 반사 (회전 대칭, 반대편과 동일)
            if new_r < 0.0:
                new_r = -new_r
                seg.angle = -seg.angle
            # 화분 윗면 위로는 반사 (z축 상단)
            if new_z > self.config.pot.height_cm:
                new_z = self.config.pot.height_cm
                seg.angle = math.pi - seg.angle
            # 화분 벽/바닥 도달 → 팁 종료
            if new_r > self.config.pot.radius_cm or new_z < 0.0:
                seg.active = False
                continue

            # 4. 이동
            seg.end_r = new_r
            seg.end_z = new_z
            seg.length += step_sz
            seg.steps_lived += 1

            # 5. 세대별 최대 수명 초과 시 자연 소멸
            if seg.steps_lived >= seg.max_lifetime:
                seg.active = False
                continue

            # 6. 복셀 방문 기록
            i, j = self.grid.world_to_grid(new_r, new_z)
            if self.grid.is_inside_pot_grid(i, j):
                self.grid.root_visits[i, j] += 1

            # 6. 에어룸 프루닝 검사
            if self._check_pruning(new_r, new_z):
                if self.rng.random() < self.config.root.pruning_probability:
                    self._do_prune(seg)

        self.step_count += 1
        return self.num_active

    def run(self, max_steps: int = 500) -> int:
        """모든 팁이 죽거나 max_steps에 도달할 때까지 성장.

        Returns:
            실제 실행된 스텝 수
        """
        while self.num_active > 0 and self.step_count < max_steps:
            self.step()
        return self.step_count

    def reset(self) -> None:
        """뿌리 시스템을 초기 상태로 리셋 (grid 방문 기록도 초기화)."""
        self.segments.clear()
        self.pruning_locations.clear()
        self._next_id = 0
        self.step_count = 0
        self.grid.root_visits[:, :] = 0
        self._init_roots()

    # ── 프루닝 ─────────────────────────────────────────

    def _check_pruning(self, r: float, z: float) -> bool:
        """뿌리 팁이 어느 에어룸의 프루닝 영역 안에 있는지 확인."""
        for ar in self.airrooms:
            if ar.is_in_pruning_zone(r, z):
                return True
        return False

    def _do_prune(self, seg: RootSegment) -> None:
        """프루닝: 현재 팁 종료 → 부모 노드에서 다음 세대 분기."""
        seg.active = False
        seg.pruned = True
        gen = seg.generation
        self.pruning_locations.append((seg.end_r, seg.end_z, gen))

        # 최대 세대면 더 이상 분기 안 함
        if gen >= self.config.root.max_generation:
            return

        child_gen = gen + 1
        cg_idx = child_gen - 1
        rc = self.config.root
        child_rad = rc.radii_cm[cg_idx] if cg_idx < len(rc.radii_cm) else 0.04
        ang_min = rc.branch_angle_min[cg_idx] if cg_idx < len(rc.branch_angle_min) else -80.0
        ang_max = rc.branch_angle_max[cg_idx] if cg_idx < len(rc.branch_angle_max) else 80.0

        child_lifetime = rc.max_segment_steps[cg_idx] if cg_idx < len(rc.max_segment_steps) else 150
        n_branches = self.rng.randint(*rc.branches_per_pruning)
        for _ in range(n_branches):
            init_angle = math.radians(self.rng.uniform(ang_min, ang_max))
            child = RootSegment(
                seg_id=self._new_id(),
                generation=child_gen,
                radius=child_rad,
                start_r=seg.end_r,
                start_z=seg.end_z,
                parent_id=seg.id,
                initial_angle=init_angle,
                max_lifetime=child_lifetime,
            )
            self.segments.append(child)

    # ── 표면적 계산 ────────────────────────────────────

    def total_surface_area(self) -> float:
        """모든 세그먼트의 총 표면적 (mm²).

        세그먼트 표면적 = 2π × 반경(cm) × 길이(cm) → 각 세그먼트를 원통으로 근사.
        cm² → mm² 환산 (×100).
        """
        area_cm2 = 0.0
        for seg in self.segments:
            area_cm2 += 2.0 * math.pi * seg.radius * seg.length
        return area_cm2 * 100.0

    def surface_area_by_generation(self) -> Dict[int, float]:
        """세대별 표면적 (mm²)."""
        result: Dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0}
        for seg in self.segments:
            area = 2.0 * math.pi * seg.radius * seg.length * 100.0
            result[seg.generation] = result.get(seg.generation, 0.0) + area
        return result

    # ── 프루닝 통계 ─────────────────────────────────────

    def pruning_count(self) -> int:
        """전체 프루닝 발생 횟수."""
        return len(self.pruning_locations)

    def pruning_by_zone(self) -> Dict[str, int]:
        """상/중/하 프루닝 분포 (z축 3등분).

        plan.md §5.2: 점수 미반영, 결과 지표로만 출력.
        """
        ph = self.config.pot.height_cm
        zones: Dict[str, int] = {"lower": 0, "middle": 0, "upper": 0}
        for _, z, _ in self.pruning_locations:
            ratio = z / ph
            if ratio > 2.0 / 3.0:
                zones["upper"] += 1
            elif ratio > 1.0 / 3.0:
                zones["middle"] += 1
            else:
                zones["lower"] += 1
        return zones

    # ── 전체 통계 ───────────────────────────────────────

    def statistics(self) -> Dict:
        """시뮬레이션 전체 통계 요약."""
        return {
            "total_segments": len(self.segments),
            "active_segments": self.num_active,
            "pruned_segments": self.pruning_count(),
            "total_surface_area_mm2": round(self.total_surface_area(), 2),
            "surface_area_by_gen": {
                str(k): round(v, 2) for k, v in self.surface_area_by_generation().items()
            },
            "pruning_count": self.pruning_count(),
            "pruning_by_zone": self.pruning_by_zone(),
            "steps_run": self.step_count,
        }
