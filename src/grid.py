"""2D r-z 복셀 격자 생성 모듈.

화분 내부를 회전 대칭 가정 하에 (r, z) 2D 격자로 표현한다.
plan.md §2 Phase A 참조.
"""
from __future__ import annotations

import numpy as np
from typing import Dict, List

from .config import SimConfig, SOIL_TYPES


class VoxelGrid:
    """2D r-z 원통 좌표계 복셀 격자.

    Attributes:
        nr: r축(반지름 방향) 복셀 개수
        nz: z축(높이 방향) 복셀 개수
        voxel_size: 복셀 한 변 길이 (cm)
        pot_radius: 화분 반지름 (cm)
        pot_height: 화분 높이 (cm)
        soil_type: [nr, nz] int 배열, 각 복셀의 흙 종류 ID
        is_airroom: [nr, nz] bool 배열, 에어룸 복셀 마스크
        root_visits: [nr, nz] int 배열, 뿌리 방문 횟수 (Phase B에서 채움)
    """

    def __init__(self, config: SimConfig):
        self.voxel_size: float = config.pot.voxel_size_cm
        self.pot_radius: float = config.pot.radius_cm
        self.pot_height: float = config.pot.height_cm

        self.nr: int = int(np.ceil(self.pot_radius / self.voxel_size))
        self.nz: int = int(np.ceil(self.pot_height / self.voxel_size))

        shape = (self.nr, self.nz)
        self.soil_type: np.ndarray = np.zeros(shape, dtype=np.int32)
        self.is_airroom: np.ndarray = np.zeros(shape, dtype=bool)
        self.root_visits: np.ndarray = np.zeros(shape, dtype=np.int32)

        self._apply_soil_mix(config.soil.mix)

    # ── 좌표 변환 ────────────────────────────────────────

    def world_to_grid(self, r: float, z: float) -> tuple[int, int]:
        i = int(np.floor(r / self.voxel_size))
        j = int(np.floor(z / self.voxel_size))
        return i, j

    def grid_to_world(self, i: int, j: int) -> tuple[float, float]:
        r = (float(i) + 0.5) * self.voxel_size
        z = (float(j) + 0.5) * self.voxel_size
        return r, z

    # ── 경계 검사 ────────────────────────────────────────

    def is_inside_pot(self, r: float, z: float) -> bool:
        return (0.0 <= r <= self.pot_radius and 0.0 <= z <= self.pot_height)

    def is_inside_pot_grid(self, i: int, j: int) -> bool:
        return (0 <= i < self.nr and 0 <= j < self.nz)

    # ── 흙 배합 ──────────────────────────────────────────

    def _apply_soil_mix(self, mix: Dict[str, float]) -> None:
        if not mix:
            return
        names = list(mix.keys())
        probs = list(mix.values())
        if len(names) == 1:
            self.soil_type[:, :] = SOIL_TYPES.get(names[0], 0)
            return
        ids = [SOIL_TYPES.get(n, 0) for n in names]
        flat = np.random.choice(ids, size=self.nr * self.nz, p=probs)
        self.soil_type = flat.reshape(self.nr, self.nz)

    # ── 통계 및 요약 ─────────────────────────────────────

    @property
    def total_cells(self) -> int:
        return self.nr * self.nz

    @property
    def airroom_cells(self) -> int:
        return int(np.sum(self.is_airroom))

    def soil_type_summary(self) -> Dict[str, float]:
        total = self.total_cells
        summary: Dict[str, float] = {}
        for name, tid in SOIL_TYPES.items():
            count = int(np.sum(self.soil_type == tid))
            summary[name] = count / total if total > 0 else 0.0
        return summary