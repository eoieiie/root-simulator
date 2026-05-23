"""G-Health Score 계산 + 메트릭 모듈.

plan.md §5 Phase C 참조.
MVP 점수 = 뿌리 표면적 × w1 + 프루닝 횟수 × w2 - 흙 손실률 × w3.
점수 항목은 확장 가능하게 dict로 관리한다.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from .config import SimConfig
from .geometry import Airroom, airroom_volume_ratio
from .grid import VoxelGrid
from .root import RootSystem


def compute_score(
    root_system: RootSystem,
    airrooms: List[Airroom],
    config: SimConfig,
) -> Dict:
    """G-Health Score 계산.

    Returns:
        {
            "total": float,         -- 최종 점수
            "components": {
                "surface_area": float,   -- 표면적 점수 (mm² × w1)
                "pruning": float,        -- 프루닝 점수 (횟수 × w2)
                "soil_loss": float,      -- 흙 손실 패널티 (-ratio × w3)
            },
            "metrics": {
                "surface_area_mm2": float,
                "pruning_count": int,
                "soil_loss_ratio": float,
                "pruning_by_zone": {"lower": int, "middle": int, "upper": int},
                "total_airrooms": int,
                "unused_airrooms": int,
            }
        }
    """
    w = config.score
    vr = airroom_volume_ratio(airrooms, config.pot.radius_cm, config.pot.height_cm)
    surf = root_system.total_surface_area()
    prun = root_system.pruning_count()

    components = {
        "surface_area": round(surf * w.surface_area_weight, 4),
        "pruning": round(prun * w.pruning_weight, 4),
        "soil_loss": round(-vr * w.soil_loss_weight, 4),
    }
    total = round(sum(components.values()), 4)

    unused = _count_unused_airrooms(root_system, airrooms)
    spread = _spatial_spread_ratio(root_system)

    return {
        "total": total,
        "components": components,
        "metrics": {
            "surface_area_mm2": round(surf, 2),
            "pruning_count": prun,
            "soil_loss_ratio": round(vr, 6),
            "pruning_by_zone": root_system.pruning_by_zone(),
            "total_airrooms": len(airrooms),
            "unused_airrooms": unused,
            "spread_ratio": round(spread, 4),
        },
    }


def _count_unused_airrooms(
    root_system: RootSystem,
    airrooms: List[Airroom],
) -> int:
    """뿌리가 한 번도 안 닿은 에어룸 개수.

    각 에어룸의 프루닝 영역 내 복셀 중 root_visits > 0인 게 하나라도 있으면
    '사용됨'으로 판정.
    """
    grid = root_system.grid
    unused = 0
    for ar in airrooms:
        visited = False
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
                if grid.root_visits[i, j] > 0:
                    visited = True
                    break
            if visited:
                break
        if not visited:
            unused += 1
    return unused


def _spatial_spread_ratio(root_system: RootSystem) -> float:
    """뿌리가 화분 내부를 얼마나 골고루 탐색했는지 측정.

    root_visits > 0 인 흙 복셀 비율. 1.0에 가까울수록
    뿌리가 화분 전체에 퍼져 있음 (엉킴 없음).
    """
    grid = root_system.grid
    total_soil = int(np.sum(grid.soil_type >= 0))
    if total_soil == 0:
        return 0.0
    visited = int(np.sum((grid.root_visits > 0) & (grid.soil_type >= 0)))
    return visited / total_soil
