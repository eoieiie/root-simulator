"""M4+M5 검증: pipeline + search + 에어룸 0개 vs 10개 비교."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import SimConfig
from src.pipeline import SimPipeline
from src.search import RandomSearch
from src.viz import plot_search_results

cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")

# Test 1: Pipeline single run
print("[1] Pipeline single run")
pipe = SimPipeline(cfg)
result = pipe.run(seed=42, max_steps=500)
s = result["score"]
assert "total" in s
assert "metrics" in s
assert s["metrics"]["spread_ratio"] >= 0
print(f"  Score={s['total']:.1f}  Surface={s['metrics']['surface_area_mm2']:.0f}mm2")
print(f"  Pruning={s['metrics']['pruning_count']}  Spread={s['metrics']['spread_ratio']:.0%}")
print(f"  Airrooms={len(result['airrooms'])}  Unused={s['metrics']['unused_airrooms']}")
assert len(result["airrooms"]) == cfg.airroom.max_count
assert result["grid"] is not None
assert result["root_system"] is not None
print("  OK")

# Test 2: Pipeline with override (0 airrooms)
print("\n[2] Pipeline with 0 airrooms")
result0 = pipe.run(seed=42, airrooms_override=[])
s0 = result0["score"]
assert s0["metrics"]["total_airrooms"] == 0
assert s0["metrics"]["pruning_count"] == 0
assert s0["metrics"]["soil_loss_ratio"] == 0.0
print(f"  Score={s0['total']:.1f}  Surface={s0['metrics']['surface_area_mm2']:.0f}mm2")
print(f"  Pruning=0  Loss=0")
print("  OK")

# Test 3: Pipeline with render
print("\n[3] Pipeline with visualization")
fig = pipe.run(seed=42, render=True)["fig"]
assert fig is not None
assert len(fig.axes) == 3
fig.savefig("E:/gwc-root-sim/output/test_pipeline_viz.png", dpi=100, bbox_inches="tight")
plt.close(fig)
print("  Saved output/test_pipeline_viz.png  OK")

# Test 4: RandomSearch basic
print("\n[4] RandomSearch (10 candidates, top 3)")
search = RandomSearch(cfg)
top3 = search.run(n_candidates=10, top_k=3, include_zero_airroom=True)
assert len(top3) == 3
print(RandomSearch.format_top5(top3))
for r in top3:
    assert r["rank"] >= 1
    assert r["score"]["total"] is not None
print("  OK")

# Test 5: 에어룸 0개 vs max_count 비교 (동일 시드)
print("\n[5] Airroom 0 vs max_count comparison (seed=42, averaged over 5 runs)")
scores_with = []
scores_without = []
for seed in range(42, 47):
    # without
    r0 = pipe.run(seed=seed, airrooms_override=[])
    scores_without.append(r0["score"]["total"])
    # with
    r1 = pipe.run(seed=seed)
    scores_with.append(r1["score"]["total"])

avg_without = sum(scores_without) / len(scores_without)
avg_with = sum(scores_with) / len(scores_with)
print(f"  0 airrooms: {[f'{s:.0f}' for s in scores_without]}  avg={avg_without:.0f}")
print(f"  {cfg.airroom.max_count} airrooms: {[f'{s:.0f}' for s in scores_with]}  avg={avg_with:.0f}")
print(f"  Difference: {avg_with - avg_without:+.0f} ({(avg_with/avg_without - 1)*100:+.1f}%)")
print("  OK")

# Test 6: Full search with multi-seed evaluation
print(f"\n[6] RandomSearch (n=50, eval_seeds={cfg.search.n_eval_seeds})")
search2 = RandomSearch(cfg)
top5 = search2.run(n_candidates=50, top_k=5, include_zero_airroom=True)
for r in top5:
    r["n_total"] = 50
print(f"\nTop 5 (sorted by mean score):")
print(RandomSearch.format_top5(top5))

# Show worst seed and best seed for each (range)
print(f"  Seed score ranges in top 5:")
for r in top5:
    if "all_scores" in r:
        print(f"    #{r['rank']}: mean={r['mean_score']:.0f}  range={min(r['all_scores']):.0f}~{max(r['all_scores']):.0f}  σ={r['std_score']:.0f}")

airroom_counts = [r["n_airrooms"] for r in top5]
print(f"  Airroom range in top 5: {min(airroom_counts)}~{max(airroom_counts)}")
zero_in_top5 = any(r["n_airrooms"] == 0 for r in top5)
print(f"  0-airroom in top 5: {'YES' if zero_in_top5 else 'NO (dropped out)'}")

# Generate Top5 search results visualization (use last seed's score for plot)
for r in top5:
    r["score"]["total"] = r["mean_score"]  # plot shows mean
fig_search = plot_search_results(top5, save_path="E:/gwc-root-sim/output/search_top5_viz.png")
plt.close(fig_search)
print("  Saved output/search_top5_viz.png  OK")

print("\n=== M4+M5 ALL TESTS PASSED ===")