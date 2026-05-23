"""M2 검증: RootSystem 성장 + 프루닝 + 통계."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
from src.config import SimConfig
from src.grid import VoxelGrid
from src.geometry import Airroom, render_airrooms_to_grid
from src.root import RootSystem

cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")

print("[1] Growth without airrooms")
grid1 = VoxelGrid(cfg)
sys1 = RootSystem(cfg, grid1, [], rng=random.Random(42))
steps = sys1.run(max_steps=500)
s1 = sys1.statistics()
print(f"  steps={steps}, segments={s1['total_segments']} active={s1['active_segments']}")
assert steps > 10
assert s1['total_surface_area_mm2'] > 0
assert s1['pruning_count'] == 0
assert (grid1.root_visits > 0).sum() > 5
print(f"  surface={s1['total_surface_area_mm2']:.2f} mm2  pruning={s1['pruning_count']}  OK")

print("\n[2] Growth with airrooms")
grid2 = VoxelGrid(cfg)
airrooms = [
    Airroom(0.0, 14.0, 1.0, 1.25),
    Airroom(3.0, 10.0, 1.2, 1.25),
    Airroom(6.0, 6.0, 1.2, 1.25),
]
render_airrooms_to_grid(grid2, airrooms)
sys2 = RootSystem(cfg, grid2, airrooms, rng=random.Random(42))
sys2.run(max_steps=500)
s2 = sys2.statistics()
print(f"  steps={s2['steps_run']}, segments={s2['total_segments']} active={s2['active_segments']}")
print(f"  surface={s2['total_surface_area_mm2']:.2f} mm2  pruning={s2['pruning_count']}")
print(f"  pruning zones: {s2['pruning_by_zone']}")
assert s2['pruning_count'] > 0
zones = s2['pruning_by_zone']
assert zones['lower'] + zones['middle'] + zones['upper'] == s2['pruning_count']
print("  OK")

print("\n[3] Surface area distribution")
gen_surf = sys2.surface_area_by_generation()
total = sum(gen_surf.values())
for g in [1, 2, 3]:
    pct = gen_surf[g] / total * 100 if total > 0 else 0
    print(f"  gen{g}: {gen_surf[g]:.2f} mm2 ({pct:.1f}%)")
assert total > 0
print("  OK")

print("\n[4] Reset")
sys2.reset()
assert sys2.num_active == cfg.root.initial_roots
assert len(sys2.segments) == cfg.root.initial_roots
assert sys2.step_count == 0
assert (grid2.root_visits == 0).all()
print("  OK")

print("\n[5] Segment tree structure")
seg1 = sys1.segments[0]
assert seg1.generation == 1
assert seg1.radius == cfg.root.radii_cm[0]
assert seg1.parent_id is None
assert seg1.start_z == cfg.pot.height_cm
assert seg1.length > 0
assert seg1.end_z < seg1.start_z
print("  OK")

print("\n[6] Pruning determinism across seeds")
counts = []
for seed in range(5):
    g = VoxelGrid(cfg)
    ar = [Airroom(0.0, 12.0, 1.5, 1.25)]
    render_airrooms_to_grid(g, ar)
    s = RootSystem(cfg, g, ar, rng=random.Random(seed))
    s.run(max_steps=500)
    counts.append(s.pruning_count())
print(f"  pruning counts: {counts}")
assert all(c > 0 for c in counts)
print("  OK")

print("\n[7] Heavy branching with 10 airrooms")
grid7 = VoxelGrid(cfg)
ar7 = [Airroom(r, z, 0.8, 1.25) for r, z in [(0, 17), (3, 14), (5, 11), (2, 8), (6, 8), (4, 5), (7, 3), (1, 2), (5, 15), (3, 17)]]
render_airrooms_to_grid(grid7, ar7)
sys7 = RootSystem(cfg, grid7, ar7, rng=random.Random(42))
sys7.run(max_steps=500)
s7 = sys7.statistics()
print(f"  pruning={s7['pruning_count']} segments={s7['total_segments']}")
print(f"  surface={s7['total_surface_area_mm2']:.2f} mm2")
assert s7['total_segments'] > s1['total_segments']
print("  OK")

print("\n=== M2 ALL TESTS PASSED ===")