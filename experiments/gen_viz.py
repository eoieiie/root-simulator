"""개선된 알고리즘으로 시각화 재생성."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import SimConfig
from src.grid import VoxelGrid
from src.geometry import Airroom, render_airrooms_to_grid, generate_random_airrooms
from src.root import RootSystem
from src.score import compute_score
from src.viz import plot_single_run

cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")
rng = random.Random(cfg.seed)

grid = VoxelGrid(cfg)
airrooms = generate_random_airrooms(cfg, n=cfg.airroom.max_count, rng=rng)
render_airrooms_to_grid(grid, airrooms)
rs = RootSystem(cfg, grid, airrooms, rng=random.Random(cfg.seed))
rs.run(max_steps=500)
result = compute_score(rs, airrooms, cfg)

print(f"Score: {result['total']:.2f}")
print(f"Surface: {result['metrics']['surface_area_mm2']:.1f} mm2")
print(f"Pruning: {result['metrics']['pruning_count']} times")
print(f"Zones: L{result['metrics']['pruning_by_zone']['lower']} M{result['metrics']['pruning_by_zone']['middle']} U{result['metrics']['pruning_by_zone']['upper']}")
print(f"Unused airrooms: {result['metrics']['unused_airrooms']}/{result['metrics']['total_airrooms']}")

fig = plot_single_run(grid, rs, airrooms, result)
fig.savefig("E:/gwc-root-sim/output/viz_improved.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("saved: output/viz_improved.png")