"""GA 검증: GA 1회 실행 (30개체, 15세대, 10 에어룸)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import SimConfig
from src.search import run_search, RandomSearch
from src.pipeline import SimPipeline
from src.ga import GeneticOptimizer
import random

cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")

print("=== GA run (pop=30, gen=15, airrooms=10) ===")
cfg.search.method = "ga"

pipeline = SimPipeline(cfg)
eval_seeds = [42, 99, 177]

def _fitness(airrooms):
    scores = []
    for s in eval_seeds:
        r = pipeline.run(seed=s, airrooms_override=airrooms, max_steps=500)
        scores.append(r["score"]["total"])
    return sum(scores) / len(scores)

opt = GeneticOptimizer(cfg, fitness_fn=_fitness)
ga_res = opt.run()

best = ga_res.best
print(f"  Best fitness: {best.fitness:.1f}")
print(f"  History best: {[f'{v:.0f}' for v in ga_res.history_best]}")
print(f"  History mean: {[f'{v:.0f}' for v in ga_res.history_mean]}")
print(f"  Evaluations:  {ga_res.n_evaluated}")
print()

# Single-seed evaluation of best
r_best = pipeline.run(seed=42, airrooms_override=best.airrooms, render=True)
s = r_best["score"]
print(f"  Score (seed=42): {s['total']:.1f}")
print(f"  Components: {s['components']}")
print(f"  Surface: {s['metrics']['surface_area_mm2']:.1f} mm2")
print(f"  Pruning: {s['metrics']['pruning_count']} times")
print(f"  Soil Loss: {s['metrics']['soil_loss_ratio']*100:.3f}%")
print(f"  Spread: {s['metrics']['spread_ratio']:.1%}")
print(f"  N Uptake: {s['metrics']['estimated_n_uptake_mg']} mg")
print(f"  Segments: {len(r_best['root_system'].segments)}")

# Compare with 0-airroom
r0 = pipeline.run(seed=42, airrooms_override=[])
s0 = r0["score"]
print()
print(f"  0-airroom comparison:")
print(f"    Score: {s0['total']:.0f} -> {s['total']:.0f} (+{s['total']-s0['total']:.0f})")
print(f"    Surface: {s0['metrics']['surface_area_mm2']:.0f} -> {s['metrics']['surface_area_mm2']:.0f} mm2")
print(f"    Pruning: {s0['metrics']['pruning_count']} -> {s['metrics']['pruning_count']}")

# Airroom positions
print()
print(f"  GA best airrooms ({len(best.airrooms)}):")
for i, ar in enumerate(best.airrooms):
    print(f"    [{i}] r={ar.r:.1f}, z={ar.z:.1f}, rad={ar.radius:.2f}")

r_best["fig"].savefig("E:/gwc-root-sim/output/verify_ga_best.png", dpi=100, bbox_inches="tight")
print("saved: output/verify_ga_best.png")
print()
print("=== GA VERIFICATION DONE ===")
