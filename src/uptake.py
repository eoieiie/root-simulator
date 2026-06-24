"""M7: Michaelis-Menten 기반 양분 흡수 계산.

각 뿌리 세그먼트의 위치에서 국소 양분 농도를 읽고,
세대별 흡수 효율을 반영한 실제 흡수량 계산.

Phase B(뿌리 성장) 후, Phase C(점수 계산) 전에 실행.
"""
from __future__ import annotations

import math
from typing import List

from .config import SimConfig
from .grid import VoxelGrid
from .root import RootSystem


def compute_uptake(
    root_system: RootSystem,
    grid: VoxelGrid,
    config: SimConfig,
) -> float:
    """전체 뿌리 시스템의 총 양분 흡수량 계산 (mg).

    Args:
        root_system: 성장 완료된 뿌리 시스템
        grid: 복셀 격자 (water_map, nutrient_map 필요)
        config: 설정 (uptake 파라미터 사용)

    Returns:
        총 질소 흡수량 (mg)
    """
    uc = config.uptake
    if not uc.enabled:
        return 0.0

    # water_map / nutrient_map이 없으면 0 반환
    if not hasattr(grid, "nutrient_map") or grid.nutrient_map is None:
        return 0.0

    total_uptake = 0.0

    for seg in root_system.segments:

        # 세그먼트 표면적 (mm²)
        area_mm2 = 2.0 * math.pi * seg.radius * seg.length * 100.0

        # 세대별 흡수 효율 (Guo et al. 2008)
        gen_weights = {1: 0.1, 2: 0.5, 3: 1.0}
        efficiency = gen_weights.get(seg.generation, 1.0)

        # 국소 양분 농도 조회
        i, j = grid.world_to_grid(seg.end_r, seg.end_z)
        if not (0 <= i < grid.nr and 0 <= j < grid.nz):
            continue
        local_n = grid.nutrient_map[i, j]

        if uc.model == "mm":
            # Michaelis-Menten
            # Uptake = area × efficiency × Vmax × C / (Km + C)
            uptake = (
                area_mm2
                * efficiency
                * uc.vmax_nitrogen
                * local_n
                / (uc.km_nitrogen + local_n + 1e-12)
            )
        else:
            # 선형 모델 (기존 _estimate_n_uptake와 동일 계수)
            uptake = area_mm2 * efficiency * local_n * uc.uptake_rate

        total_uptake += uptake

    return round(total_uptake, 6)
