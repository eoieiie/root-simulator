"""M6: Cellular Automata 기반 자원 확산.

물과 양분이 화분 내에서 중력 + 확산으로 퍼지는 과정을 격자 기반 CA로 계산.
에어룸 복셀은 물을 저장하지 않는 장벽으로 작동.

Phase A(격자 생성) 후, Phase B(뿌리 성장) 전에 실행.
"""
from __future__ import annotations

import numpy as np
from typing import Optional

from .config import SimConfig
from .grid import VoxelGrid


def run_diffusion(
    grid: VoxelGrid,
    config: SimConfig,
) -> None:
    """Cellular Automata로 수분/양분 확산을 계산해 grid에 기록.

    Args:
        grid: 복셀 격자 (is_airroom 필드 필요)
        config: 설정 (diffusion 파라미터 사용)

    Effects:
        grid.water_map: (nr, nz) float, 0~1, 각 복셀의 수분 함량
        grid.nutrient_map: (nr, nz) float, mg/cm³, 각 복셀의 질소 농도
    """
    dc = config.diffusion
    nr, nz = grid.nr, grid.nz

    # water_map 초기화
    water = np.full((nr, nz), dc.initial_water_content, dtype=np.float64)

    # 에어룸 복셀은 water = 0
    airroom_mask = grid.is_airroom.copy()
    water[airroom_mask] = 0.0

    # 표면 마스크 (z축 최상단, 급수 지점)
    surface_mask = np.zeros((nr, nz), dtype=bool)
    surface_mask[:, nz - 1] = True

    # 바닥 마스크 (z=0, 배수)
    bottom_mask = np.zeros((nr, nz), dtype=bool)
    bottom_mask[:, 0] = True

    for iteration in range(dc.max_iterations):
        prev = water.copy()

        # 1. 중력: water가 아래(z-1)로 이동
        #    gravity_bias 비율만큼 아래로 내려보냄
        grav_move = prev * dc.gravity_bias
        for i in range(nr):
            for j in range(1, nz):  # 아래에서 위로 스캔 (j=0=바닥, j=nz-1=표면)
                if airroom_mask[i, j]:
                    continue
                if airroom_mask[i, j - 1]:
                    continue  # 아래가 에어룸이면 이동 안 함 (장벽)
                amount = grav_move[i, j]
                water[i, j] -= amount
                water[i, j - 1] += amount

        # 2. 확산: 주변 4방향으로 확산 (diffusion_rate)
        diff_rate = dc.water_diffusion_rate
        for i in range(nr):
            for j in range(nz):
                if airroom_mask[i, j]:
                    continue
                # 왼쪽 (i-1)
                if i > 0 and not airroom_mask[i - 1, j]:
                    amount = (water[i, j] - water[i - 1, j]) * diff_rate * 0.25
                    if amount > 0:
                        water[i, j] -= amount
                        water[i - 1, j] += amount
                # 오른쪽 (i+1)
                if i < nr - 1 and not airroom_mask[i + 1, j]:
                    amount = (water[i, j] - water[i + 1, j]) * diff_rate * 0.25
                    if amount > 0:
                        water[i, j] -= amount
                        water[i + 1, j] += amount
                # 위 (j+1)
                if j < nz - 1 and not airroom_mask[i, j + 1]:
                    amount = (water[i, j] - water[i, j + 1]) * diff_rate * 0.25
                    if amount > 0:
                        water[i, j] -= amount
                        water[i + 1 if i < nr - 1 else i - 1, j + 1] += amount
                # 아래 (j-1)
                if j > 0 and not airroom_mask[i, j - 1]:
                    amount = (water[i, j] - water[i, j - 1]) * diff_rate * 0.25
                    if amount > 0:
                        water[i, j] -= amount
                        water[i, j - 1] += amount

        # 3. 표면 증발
        water[surface_mask & ~airroom_mask] *= (1.0 - dc.evaporation_rate)

        # 4. 바닥 배수
        water[bottom_mask] *= 0.95

        # 5. 에어룸 복셀은 항상 0 유지
        water[airroom_mask] = 0.0

        # 6. 0~1 클램프
        water = np.clip(water, 0.0, 1.0)

        # 7. 수렴 검사
        diff = np.abs(water - prev).max()
        if diff < dc.convergence_threshold:
            break

    # 결과 저장
    grid.water_map = water

    # nutrient_map: water에 비례한 질소 농도 (mg/cm³)
    # 표면 근처는 급수로 양분 많음, 아래로 갈수록 감소
    base_nutrient = water * dc.nutrient_concentration
    # 추가: 표면 근처에 양분 집중 (급수 + 비료 효과)
    depth_bonus = np.linspace(0.0, 0.3, nz)  # 표면: +0.3, 바닥: 0.0
    nutrient = base_nutrient + depth_bonus[np.newaxis, :] * 0.05
    nutrient[airroom_mask] = 0.0
    nutrient = np.clip(nutrient, 0.0, dc.nutrient_concentration * 1.5)
    grid.nutrient_map = nutrient
