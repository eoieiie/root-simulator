"""
V5: Validation run.
- Same V3 config (g=1.0, noise=8°, pop=30, gen=25)
- Different random seed (123) to check reproducibility
- No seed genome (fresh start)
- 15-seed re-evaluation
"""
import json, time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import SimConfig
from src.search import run_ga_search, save_results, RandomSearch
from src.pipeline import SimPipeline

cfg = SimConfig.from_json("configs/pot_13.json")
cfg.ga.population = 30
cfg.ga.generations = 25
cfg.seed = 123  # different random seed for reproducibility check

print("=" * 65)
print("V5: Reproducibility check (seed=123, pop=30, gen=25)")
print("=" * 65)
print(f"GA: pop={cfg.ga.population}, gen={cfg.ga.generations}")
print(f"Tropism: g={cfg.tropism.g}, noise={cfg.root.noise_deg}")
print(f"Seed genome: None (fresh start)")
print(f"Estimated runs: {cfg.ga.population * cfg.ga.generations * cfg.search.n_eval_seeds}")

t0 = time.time()
top5 = run_ga_search(cfg, seed_genome=None)
t_ga = time.time() - t0
print(f"\nGA: {t_ga:.0f}s ({t_ga/60:.1f}min)")

print(RandomSearch.format_top5(top5))

# Re-evaluate Top5 with 15 seeds
RE = 15
print(f"\n--- Re-evaluating Top{len(top5)} with {RE} seeds ---")
t0 = time.time()
eval_seeds = [cfg.seed + i for i in range(RE)]
pipeline = SimPipeline(cfg)
for entry in top5:
    scores = []
    for s in eval_seeds:
        r = pipeline.run(seed=s, airrooms_override=entry["airrooms"], max_steps=500)
        scores.append(r["score"]["total"])
    m = sum(scores) / len(scores)
    sd = (sum((x-m)**2 for x in scores) / len(scores))**0.5
    entry["mean_score"] = m
    entry["std_score"] = round(sd, 2)
    entry["all_scores"] = [round(s,1) for s in scores]
    entry["n_eval_seeds"] = RE
    if entry is top5[0]:
        entry["score"] = r["score"]

t_re = time.time() - t0
top5.sort(key=lambda x: -x["mean_score"])
for i, e in enumerate(top5):
    e["rank"] = i+1

print(f"Re-eval: {t_re:.0f}s")
print(f"\n{'='*65}")
print("V5 RESULTS vs PREVIOUS BEST")
print(f"{'='*65}")

best = top5[0]
s = best["score"]
z = s["metrics"].get("pruning_by_zone",{})
print(f"\nV5: Mean={best['mean_score']:.0f}±{best['std_score']:.0f}  P={s['metrics']['pruning_count']}회  Zones=L{z.get('lower',0)}/M{z.get('middle',0)}/U{z.get('upper',0)}")
print(f"Prev (final): 6865±864  P=68  Zones=L33/M29/U0")
print(f"Prev (V3):    6861±823  P=50  Zones=L30/M20/U0")

# Airrooms
print(f"\nAirrooms:")
for i, a in enumerate(best["airrooms"], 1):
    print(f"  {i}: r={a.r:.2f} z={a.z:.2f} rad={a.radius:.2f}")

save_results(top5, cfg, "output/results_v5.json")
print(f"\nSaved: output/results_v5.json")
print(f"Total: {t_ga+t_re:.0f}s ({(t_ga+t_re)/60:.1f}min)")
