"""M3 검증: score 계산 + viz 시각화 출력."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import SimConfig
from src.grid import VoxelGrid
from src.geometry import Airroom, render_airrooms_to_grid, generate_random_airrooms
from src.root import RootSystem
from src.score import compute_score
from src.viz import plot_single_run

cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")

# Setup: grid + airrooms + roots
grid = VoxelGrid(cfg)
rng = random.Random(cfg.seed)
airrooms = generate_random_airrooms(cfg, n=cfg.airroom.max_count, rng=rng)
render_airrooms_to_grid(grid, airrooms)
root_system = RootSystem(cfg, grid, airrooms, rng=random.Random(cfg.seed))
root_system.run(max_steps=500)

# Test 1: compute_score returns valid structure
print("[1] compute_score structure")
result = compute_score(root_system, airrooms, cfg, grid)
print(f"  total={result['total']:.2f}")
print(f"  components: {result['components']}")
print(f"  metrics: {result['metrics']}")
assert "total" in result
assert "components" in result
assert "metrics" in result
assert result["components"]["surface_area"] >= 0
assert result["components"]["pruning"] >= 0
assert result["components"]["soil_loss"] <= 0  # penalty is negative
assert result["metrics"]["pruning_count"] >= 0
print("  OK")

# Test 2: Total = sum of components
print("\n[2] Total = sum of components")
expected = sum(result["components"].values())
assert abs(result["total"] - expected) < 0.001
print(f"  total={result['total']:.2f} == sum({expected:.2f})  OK")

# Test 3: No airrooms = no pruning penalty
print("\n[3] Score without airrooms")
grid3 = VoxelGrid(cfg)
sys3 = RootSystem(cfg, grid3, [], rng=random.Random(42))
sys3.run(max_steps=500)
r3 = compute_score(sys3, [], cfg, grid3)
assert r3["metrics"]["pruning_count"] == 0
assert r3["metrics"]["soil_loss_ratio"] == 0.0
assert r3["components"]["pruning"] == 0.0
assert r3["components"]["soil_loss"] == 0.0
print(f"  total={r3['total']:.2f} (surface only)  OK")

# Test 4: Unused airrooms
print("\n[4] Unused airrooms count")
all_used = result["metrics"]["total_airrooms"] - result["metrics"]["unused_airrooms"]
print(f"  total={result['metrics']['total_airrooms']} unused={result['metrics']['unused_airrooms']} used={all_used}")
assert result["metrics"]["unused_airrooms"] >= 0
assert all_used >= 0
print("  OK")

# Test 5: Pruning zones sum to total
print("\n[5] Pruning zones sum")
zones = result["metrics"]["pruning_by_zone"]
total_prun = zones["lower"] + zones["middle"] + zones["upper"]
assert total_prun == result["metrics"]["pruning_count"]
print(f"  L={zones['lower']}+M={zones['middle']}+U={zones['upper']}={total_prun} == {result['metrics']['pruning_count']}  OK")

# Test 6: Run with different seeds
print("\n[6] Score varies by seed")
scores = []
for seed in range(5):
    g = VoxelGrid(cfg)
    ar = generate_random_airrooms(cfg, n=5, rng=random.Random(seed))
    render_airrooms_to_grid(g, ar)
    rs = RootSystem(cfg, g, ar, rng=random.Random(seed))
    rs.run(max_steps=500)
    sc = compute_score(rs, ar, cfg, g)
    scores.append(sc["total"])
print(f"  scores: {[f'{s:.1f}' for s in scores]}")
assert len(set(round(s, 1) for s in scores)) > 1  # should vary
print("  OK")

# Test 7: viz creates figure
print("\n[7] Visualization output")
fig = plot_single_run(grid, root_system, airrooms, result)
assert fig is not None
n_axes = len(fig.axes)
assert n_axes == 3, f"expected 3 axes, got {n_axes}"
fig.savefig("E:/gwc-root-sim/output/test_m3_viz.png", dpi=100, bbox_inches="tight")
plt.close(fig)
assert os.path.exists("E:/gwc-root-sim/output/test_m3_viz.png")
print(f"  {n_axes} panels, saved to output/test_m3_viz.png  OK")

# Test 8: Soil loss penalty is reasonable
print("\n[8] Soil loss penalty sanity")
grid8 = VoxelGrid(cfg)
ar8 = generate_random_airrooms(cfg, n=cfg.airroom.max_count, rng=random.Random(99))
render_airrooms_to_grid(grid8, ar8)
rs8 = RootSystem(cfg, grid8, ar8, rng=random.Random(99))
rs8.run(max_steps=500)
r8 = compute_score(rs8, ar8, cfg, grid8)
sl = -r8["components"]["soil_loss"]
sr = r8["metrics"]["soil_loss_ratio"]
print(f"  soil_loss_ratio={sr*100:.2f}% penalty={sl:.2f}")
assert 0 < sr < 0.5  # loss shouldn't exceed 50% for 10 airrooms
print("  OK")

print("\n=== M3 ALL TESTS PASSED ===")