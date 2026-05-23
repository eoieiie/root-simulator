"""M1 검증 스크립트: config -> grid -> geometry 파이프라인 확인."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
import numpy as np

from src.config import SimConfig
from src.grid import VoxelGrid
from src.geometry import (Airroom, render_airrooms_to_grid,
                          generate_random_airrooms, airroom_volume_ratio,
                          get_contact_mask)

cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")
errs = cfg.validate()
assert not errs, f"Config fail: {errs}"
print(f"[1] Config: {cfg.pot.radius_cm}cm x {cfg.pot.height_cm}cm  voxel={cfg.pot.voxel_size_cm}cm")
print(f"  soil={cfg.soil.mix}  max_airrooms={cfg.airroom.max_count}  OK")

grid = VoxelGrid(cfg)
assert grid.nr == 24
assert grid.nz == 40
assert grid.total_cells == 960
print(f"[2] Grid: {grid.nr}x{grid.nz}={grid.total_cells} cells  OK")

summary = grid.soil_type_summary()
pct = {k: f"{v*100:.1f}%" for k, v in summary.items()}
assert 0.9 < sum(summary.values()) <= 1.0
print(f"[3] Soil: {pct}  OK")

i, j = grid.world_to_grid(0, 0)
rw, zw = grid.grid_to_world(0, 0)
assert (i, j) == (0, 0) and abs(rw - 0.25) < 1e-6
assert grid.is_inside_pot(5, 10) and not grid.is_inside_pot(15, 25)
print(f"[4] Coord: (0,0)->grid({i},{j})->world({rw:.2f},{zw:.2f})  boundary OK  OK")

g = VoxelGrid(cfg)
a1 = Airroom(6.0, 10.0, 1.0, 1.25)
render_airrooms_to_grid(g, [a1])
zm = get_contact_mask(g, [a1])
vr = airroom_volume_ratio([a1], cfg.pot.radius_cm, cfg.pot.height_cm)
assert int(np.sum(g.is_airroom)) > 0
print(f"[5] Single airroom: ar={int(np.sum(g.is_airroom))}cells zone={int(np.sum(zm))}cells loss={vr:.4f}  OK")

rng = random.Random(cfg.seed)
airrooms = generate_random_airrooms(cfg, n=10, rng=rng)
assert 0 < len(airrooms) <= cfg.airroom.max_count
g2 = VoxelGrid(cfg)
render_airrooms_to_grid(g2, airrooms)
vr2 = airroom_volume_ratio(airrooms, cfg.pot.radius_cm, cfg.pot.height_cm)
assert g2.airroom_cells > 0
print(f"[6] Random airrooms: {len(airrooms)} created  ar_cells={g2.airroom_cells}  loss={vr2*100:.2f}%  OK")

d = cfg.to_dict()
cfg2 = SimConfig.from_dict(d)
assert cfg2.pot.radius_cm == cfg.pot.radius_cm
assert cfg2.soil.mix == cfg.soil.mix
print(f"[7] Config serialization round-trip: OK")

print("\n=== M1 ALL TESTS PASSED ===")