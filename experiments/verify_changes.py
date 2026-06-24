"""변경 사항 검증: pipeline 1회 실행 + config 검증."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import SimConfig
from src.pipeline import SimPipeline

# 1. Config validation
print("=== Config validation ===")
cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")
errs = cfg.validate()
if errs:
    for e in errs:
        print(f"  ERROR: {e}")
    sys.exit(1)
else:
    print("  OK")

print(f"  voxel_size_cm={cfg.pot.voxel_size_cm}")
print(f"  pruning_probability={cfg.root.pruning_probability}")
print(f"  noise_deg={cfg.root.noise_deg}")
print(f"  max_angle_deg={cfg.root.max_angle_deg}")
print(f"  tropism.g={cfg.tropism.g}")
print(f"  score.pruning_weight={cfg.score.pruning_weight}")
print(f"  score.soil_loss_weight={cfg.score.soil_loss_weight}")
print(f"  soil.mix={cfg.soil.mix}")
print(f"  search.method={cfg.search.method}")
print(f"  ga.pop={cfg.ga.population}, gen={cfg.ga.generations}")

# 2. Pipeline single run
print()
print("=== Pipeline single run (seed=42) ===")
p = SimPipeline(cfg)
r = p.run(seed=42, render=True)
s = r["score"]

print(f"  Score total: {s['total']:.1f}")
print(f"  Components:  {s['components']}")
print(f"  Surface:     {s['metrics']['surface_area_mm2']:.1f} mm2")
print(f"  Pruning:     {s['metrics']['pruning_count']} times")
print(f"  Soil Loss:   {s['metrics']['soil_loss_ratio']*100:.3f}%")
print(f"  Spread:      {s['metrics']['spread_ratio']:.1%}")
print(f"  N Uptake:    {s['metrics']['estimated_n_uptake_mg']} mg")
print(f"  N/cm2:       {s['metrics']['estimated_n_uptake_per_cm2']} mg")
print(f"  Segments:    {len(r['root_system'].segments)}")
print(f"  Steps run:   {r['root_system'].step_count}")
print()

# 3. 0 airroom baseline
print("=== Baseline: 0 airrooms ===")
r0 = p.run(seed=42, airrooms_override=[])
s0 = r0["score"]
print(f"  Score: {s0['total']:.1f}")
print(f"  Surface: {s0['metrics']['surface_area_mm2']:.1f} mm2")
print(f"  Pruning: {s0['metrics']['pruning_count']} times")
print()

# 4. Save figure
r["fig"].savefig("E:/gwc-root-sim/output/verify_pipeline.png", dpi=100, bbox_inches="tight")
print("saved: output/verify_pipeline.png")

# 5. Summary
print()
print("=== Summary ===")
print(f"  0-airroom Score={s0['total']:.0f}, Surface={s0['metrics']['surface_area_mm2']:.0f}, Pruning={s0['metrics']['pruning_count']}")
print(f"  10-airroom Score={s['total']:.0f}, Surface={s['metrics']['surface_area_mm2']:.0f}, Pruning={s['metrics']['pruning_count']}")
print(f"  Difference: Score {s['total']-s0['total']:+.0f}, Surface {s['metrics']['surface_area_mm2']-s0['metrics']['surface_area_mm2']:+.0f}")
print()
print("=== ALL CHECKS PASSED ===")
