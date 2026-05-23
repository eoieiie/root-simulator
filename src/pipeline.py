"""1회 실행 파이프라인 오케스트레이션.

사용법:
    pipe = SimPipeline(config)
    result = pipe.run(seed=42)
    print(result["score"]["total"])
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from .config import SimConfig
from .geometry import (
    Airroom,
    generate_random_airrooms,
    render_airrooms_to_grid,
)
from .grid import VoxelGrid
from .root import RootSystem
from .score import compute_score
from .viz import plot_single_run


class SimPipeline:
    """Config 1개로 전체 Phase A→B→C를 1회 실행."""

    def __init__(self, config: SimConfig):
        self.config = config

    def run(
        self,
        seed: Optional[int] = None,
        max_steps: int = 500,
        airrooms_override: Optional[List[Airroom]] = None,
        render: bool = False,
    ) -> Dict:
        """파이프라인 1회 실행.

        Args:
            seed: 난수 시드 (None=config.seed 사용)
            max_steps: 최대 성장 스텝 수
            airrooms_override: 외부에서 에어룸 지정 (None=랜덤 생성)
            render: True면 시각화 fig도 반환

        Returns:
            {"grid": VoxelGrid, "root_system": RootSystem,
             "airrooms": List[Airroom], "score": Dict, "fig": Figure | None}
        """
        seed = seed if seed is not None else self.config.seed
        rng = random.Random(seed)

        # Phase A — 격자 + 에어룸
        grid = VoxelGrid(self.config)
        if airrooms_override is not None:
            airrooms = airrooms_override
        else:
            n = self.config.airroom.max_count
            airrooms = generate_random_airrooms(self.config, n=n, rng=rng)
        render_airrooms_to_grid(grid, airrooms)

        # Phase B — 뿌리 성장
        root_system = RootSystem(self.config, grid, airrooms, rng=random.Random(seed))
        root_system.run(max_steps=max_steps)

        # Phase C — 점수
        score_result = compute_score(root_system, airrooms, self.config)

        # Phase E — 시각화 (옵션)
        fig = None
        if render:
            fig = plot_single_run(grid, root_system, airrooms, score_result)

        return {
            "grid": grid,
            "root_system": root_system,
            "airrooms": airrooms,
            "score": score_result,
            "fig": fig,
        }
