"""G-Health Score 계산 — 표면적 + 프루닝 + 흙손실 패널티.

점수 공식:
    Score = surface_area × surface_area_weight
          + pruning_count × pruning_weight
          - soil_loss_ratio × soil_loss_weight

프루닝 점수 근거:
    - Platycladus orientalis air-pruning (PLOS ONE 2018): 프루닝 72h 후
      측근 6배 증가 관측.
    - Reid et al. (1998) Arabidopsis 뿌리절단: 측근 밀도 유의미 증가 (P=0.001).
    - YUC9-mediated auxin pathway (2018): 절단 부위 옥신 축적 → 측근 형성.

양분흡수 메트릭 근거:
    - 단위면적당 흡수율: Craig et al. (2025) 77수종 분석,
      NH4 Imax ≈ 30 µg/cm²/day (사탕수수, McDonald et al.)
    - 세대별 흡수 효율: Guo et al. (2008) 23수종 분석,
      1차근=수송위주, 3차근=주흡수.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from .config import SimConfig
from .geometry import Airroom, airroom_volume_ratio
from .grid import VoxelGrid
from .root import RootSystem
from .uptake import compute_uptake


def compute_score(
    root_system: RootSystem,
    airrooms: List[Airroom],
    config: SimConfig,
    grid: VoxelGrid,
) -> Dict:
    """G-Health Score 계산.

    점수 = 표면적(mm²) × w_surface
         + 프루닝횟수 × w_pruning
         - 흙손실률 × w_soil_loss

    Returns:
        {
            "total": float,
            "components": {
                "surface_area": float,
                "pruning": float,
                "soil_loss": float,
            },
            "metrics": {
                "surface_area_mm2": float,
                "pruning_count": int,
                "soil_loss_ratio": float,
                "pruning_by_zone": ...,
                "total_airrooms": int,
                "unused_airrooms": int,
                "spread_ratio": float,
                "estimated_n_uptake_mg": float,
            }
        }
    """
    w = config.score
    vr = airroom_volume_ratio(airrooms, config.pot.radius_cm, config.pot.height_cm)
    surf = root_system.total_surface_area()
    pcount = root_system.pruning_count()

    n_uptake = compute_uptake(root_system, grid, config) if config.uptake.enabled else 0.0

    components = {
        "surface_area": round(surf * w.surface_area_weight, 4),
        "pruning": round(pcount * w.pruning_weight, 4),
        "soil_loss": round(-vr * w.soil_loss_weight, 4),
        "n_uptake": round(n_uptake * w.uptake_weight, 4),
    }
    total = round(sum(components.values()), 4)

    unused = _count_unused_airrooms(root_system, airrooms)
    spread = _spatial_spread_ratio(root_system)

    return {
        "total": total,
        "components": components,
        "metrics": {
            "surface_area_mm2": round(surf, 2),
            "pruning_count": pcount,
            "soil_loss_ratio": round(vr, 6),
            "pruning_by_zone": root_system.pruning_by_zone(),
            "total_airrooms": len(airrooms),
            "unused_airrooms": unused,
            "spread_ratio": round(spread, 4),
            "n_uptake_mg": round(n_uptake, 6),
        },
    }


def _count_unused_airrooms(
    root_system: RootSystem,
    airrooms: List[Airroom],
) -> int:
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
    total_soil = int(np.sum(root_system.grid.soil_type >= 0))
    if total_soil == 0:
        return 0.0
    visited = int(np.sum((root_system.grid.root_visits > 0)
                          & (root_system.grid.soil_type >= 0)))
    return visited / total_soil
