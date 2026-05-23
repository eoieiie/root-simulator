"""에어룸 기하 형상 및 격자 마스킹 모듈.

plan.md §3 (에어룸 표현) 및 §3.2 (데이터 구조) 구현.
2D r-z 단면에서 에어룸은 원형 영역으로 근사한다.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import SimConfig
from .grid import VoxelGrid


class Airroom:
    """정사면체 에어룸의 2D r-z 단면 표현.

    Attributes:
        r: 화분 중심축에서 거리 (cm)
        z: 바닥에서 높이 (cm)
        radius: 단면 원 반경 (cm)
        pruning_zone_radius: 프루닝 판정 영향권 반경 (cm)
    """

    def __init__(self, r: float, z: float, radius: float,
                 pruning_zone_factor: float = 1.25):
        self.r = r
        self.z = z
        self.radius = radius
        self.pruning_zone_radius = radius * pruning_zone_factor

    def is_inside(self, r: float, z: float) -> bool:
        dx = r - self.r
        dz = z - self.z
        return (dx * dx + dz * dz) <= self.radius * self.radius

    def is_in_pruning_zone(self, r: float, z: float) -> bool:
        dx = r - self.r
        dz = z - self.z
        return (dx * dx + dz * dz) <= self.pruning_zone_radius * self.pruning_zone_radius

    def to_dict(self) -> Dict:
        return {
            "r": round(self.r, 4),
            "z": round(self.z, 4),
            "radius": round(self.radius, 4),
            "pruning_zone_radius": round(self.pruning_zone_radius, 4),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Airroom":
        return cls(d["r"], d["z"], d["radius"])


# ── 격자 마스킹 ─────────────────────────────────────────


def render_airrooms_to_grid(
    grid: VoxelGrid,
    airrooms: List[Airroom],
) -> None:
    """에어룸 목록을 복셀 격자에 마스킹한다.

    에어룸 내부 복셀은 is_airroom=True, soil_type=-1로 설정.
    """
    for ar in airrooms:
        r_min = max(0.0, ar.r - ar.radius)
        r_max = min(grid.pot_radius, ar.r + ar.radius)
        z_min = max(0.0, ar.z - ar.radius)
        z_max = min(grid.pot_height, ar.z + ar.radius)

        i0, j0 = grid.world_to_grid(r_min, z_min)
        i1, j1 = grid.world_to_grid(r_max, z_max)

        i0 = max(0, i0)
        i1 = min(grid.nr - 1, i1 + 1)
        j0 = max(0, j0)
        j1 = min(grid.nz - 1, j1 + 1)

        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                rw, zw = grid.grid_to_world(i, j)
                if ar.is_inside(rw, zw):
                    grid.is_airroom[i, j] = True
                    grid.soil_type[i, j] = -1


def get_contact_mask(
    grid: VoxelGrid,
    airrooms: List[Airroom],
) -> np.ndarray:
    """프루닝 영향권에 있는 흙 복셀의 bool 마스크 반환.

    Phase B에서 뿌리 팁 위치가 이 마스크와 겹치는지로 프루닝을 판정.
    에어룸 자체는 제외한다.
    """
    mask = np.zeros((grid.nr, grid.nz), dtype=bool)
    for ar in airrooms:
        r_min = max(0.0, ar.r - ar.pruning_zone_radius)
        r_max = min(grid.pot_radius, ar.r + ar.pruning_zone_radius)
        z_min = max(0.0, ar.z - ar.pruning_zone_radius)
        z_max = min(grid.pot_height, ar.z + ar.pruning_zone_radius)

        i0, j0 = grid.world_to_grid(r_min, z_min)
        i1, j1 = grid.world_to_grid(r_max, z_max)

        i0 = max(0, i0)
        i1 = min(grid.nr - 1, i1 + 1)
        j0 = max(0, j0)
        j1 = min(grid.nz - 1, j1 + 1)

        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                if grid.is_airroom[i, j]:
                    continue
                rw, zw = grid.grid_to_world(i, j)
                if ar.is_in_pruning_zone(rw, zw):
                    mask[i, j] = True
    return mask


# ── 랜덤 생성 ──────────────────────────────────────────


def generate_random_airrooms(
    config: SimConfig,
    n: Optional[int] = None,
    rng: Optional[random.Random] = None,
) -> List[Airroom]:
    """화분 내부에 n개의 에어룸을 랜덤 배치.

    중복/과다 겹침을 방지하고, plan.md §3.3의 개수 제한을 따른다.
    """
    if rng is None:
        rng = random.Random(config.seed)
    if n is None:
        n = config.airroom.max_count

    max_count = min(n, config.airroom.max_count)
    r_min_s, r_max_s = config.airroom.radius_range_cm
    pzf = config.airroom.pruning_zone_factor
    pr = config.pot.radius_cm
    ph = config.pot.height_cm

    airrooms: List[Airroom] = []
    safety_margin = 1.0  # 화분 벽/바닥 여유
    max_attempts = max_count * 50

    for _ in range(max_attempts):
        if len(airrooms) >= max_count:
            break

        r = rng.uniform(safety_margin, pr - safety_margin)
        z = rng.uniform(safety_margin + 0.5, ph - safety_margin)
        radius = rng.uniform(r_min_s, r_max_s)

        overlap = False
        merge_dist = (radius + (r_max_s if r_max_s > 0 else 1.0)) * 0.4
        for existing in airrooms:
            dr = r - existing.r
            dz = z - existing.z
            if (dr * dr + dz * dz) < merge_dist * merge_dist:
                overlap = True
                break

        if not overlap:
            airrooms.append(Airroom(r, z, radius, pzf))

    return airrooms


def airroom_volume_ratio(
    airrooms: List[Airroom],
    pot_radius: float,
    pot_height: float,
) -> float:
    """에어룸이 차지하는 체적 비율 (흙 손실률 추정).

    2D 단면 면적 비율을 회전체 부피 비율로 근사:
    plan.md §9.1 파푸스 정리 참조.
    """
    total_section_area = 0.0
    for ar in airrooms:
        total_section_area += math.pi * ar.radius * ar.radius
    pot_section_area = 2.0 * pot_radius * pot_height
    return total_section_area / pot_section_area if pot_section_area > 0 else 0.0