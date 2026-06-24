"""
FINAL RUN: GA optimization for 13cm pot (r=6.5, h=15cm).
V3 params (g=1.0, noise=8°), NO seed genome (fresh start).
Larger search: pop=30, gen=20, eval=5 seeds internal.
Top5 re-evaluated with 15 seeds.
Then output 3D airroom coordinates for Fusion 360.
"""
import json, time, math, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import SimConfig
from src.search import run_ga_search, save_results, RandomSearch
from src.pipeline import SimPipeline

print("=" * 65)
print("FINAL RUN: V3 config, no seed genome, pop=30 gen=20")
print("=" * 65)

cfg = SimConfig.from_json("configs/pot_13.json")
cfg.ga.population = 30
cfg.ga.generations = 20

print(f"GA: pop={cfg.ga.population}, gen={cfg.ga.generations}, elite={cfg.ga.elite_frac}, mut_sigma={cfg.ga.mutation_sigma_cm}")
print(f"Tropism: g={cfg.tropism.g}, noise={cfg.root.noise_deg}")
print(f"Eval seeds: {cfg.search.n_eval_seeds} (GA internal)")
est_runs = cfg.ga.population * cfg.ga.generations * cfg.search.n_eval_seeds
print(f"Estimated: {est_runs} pipeline runs")

t0 = time.time()
top5 = run_ga_search(cfg, seed_genome=None)
t_ga = time.time() - t0
print(f"\nGA complete: {t_ga:.0f}s ({t_ga/60:.1f}min)")

print("\n--- Top5 (GA internal eval) ---")
print(RandomSearch.format_top5(top5))

# Re-evaluate Top5 with 15 seeds
RE_EVAL = 15
print(f"\n--- Re-evaluating with {RE_EVAL} seeds ---")
t0 = time.time()
eval_seeds = [cfg.seed + i for i in range(RE_EVAL)]
pipeline = SimPipeline(cfg)

for entry in top5:
    all_scores = []
    for s in eval_seeds:
        r = pipeline.run(seed=s, airrooms_override=entry["airrooms"], max_steps=500)
        all_scores.append(r["score"]["total"])
    mean_s = sum(all_scores) / len(all_scores)
    std_s = (sum((x - mean_s)**2 for x in all_scores) / len(all_scores))**0.5
    entry["mean_score"] = mean_s
    entry["std_score"] = round(std_s, 2)
    entry["all_scores"] = [round(s, 1) for s in all_scores]
    entry["n_eval_seeds"] = RE_EVAL
    if entry is top5[0]:
        entry["score"] = r["score"]  # last seed's score

t_re = time.time() - t0

top5.sort(key=lambda x: -x["mean_score"])
for i, entry in enumerate(top5):
    entry["rank"] = i + 1

print(f"\nRe-evaluation: {t_re:.0f}s ({t_re/60:.1f}min)")

print("\n" + "=" * 65)
print("FINAL RESULTS")
print("=" * 65)

for entry in top5:
    s = entry["score"]
    z = s["metrics"].get("pruning_by_zone", {})
    print(f"\n#{entry['rank']}: Mean={entry['mean_score']:.0f} Std={entry['std_score']:.0f}")
    print(f"  Airrooms={entry['n_airrooms']}  Seeds={entry['n_eval_seeds']}")
    print(f"  S={s['metrics']['surface_area_mm2']:.0f}mm²  P={s['metrics']['pruning_count']}회")
    print(f"  L={s['metrics']['soil_loss_ratio']*100:.1f}%  N={s['metrics']['n_uptake_mg']:.4f}mg")
    print(f"  Spread={s['metrics']['spread_ratio']*100:.1f}%  Zones=L{z.get('lower',0)}/M{z.get('middle',0)}/U{z.get('upper',0)}")

best = top5[0]
print("\n\n=== BEST DESIGN ===")
print(f"Score: {best['mean_score']:.0f} ± {best['std_score']:.0f} ({RE_EVAL} seeds)")
print(f"All scores: {best['all_scores']}")
s = best["score"]
print(f"\nComponents:")
print(f"  Surface area: {s['metrics']['surface_area_mm2']:.0f} mm²")
print(f"  Pruning: {s['metrics']['pruning_count']}회 (L{z.get('lower',0)}/M{z.get('middle',0)}/U{z.get('upper',0)})")
print(f"  Soil loss: {s['metrics']['soil_loss_ratio']*100:.1f}%")
print(f"  N uptake: {s['metrics']['n_uptake_mg']:.4f} mg")
print(f"  Spread: {s['metrics']['spread_ratio']*100:.1f}%")

print(f"\nAirrooms (2D r-z):")
for i, a in enumerate(best["airrooms"], 1):
    print(f"  {i}: r={a.r:.2f}cm  z={a.z:.2f}cm  radius={a.radius:.2f}cm")

# 3D conversion: distribute each airroom evenly around circumference
n_theta = 4  # 4 copies per ring for symmetry
print(f"\n\n3D AIRROOM COORDINATES (for Fusion 360)")
print(f"  Each 2D airroom → {n_theta} copies at 360°/{n_theta} intervals")
print(f"  Total: {len(best['airrooms']) * n_theta} airrooms")
for i, a in enumerate(best["airrooms"], 1):
    theta_deg = 360.0 / n_theta
    for k in range(n_theta):
        theta = k * theta_deg
        x = a.r * math.cos(math.radians(theta))
        y = a.r * math.sin(math.radians(theta))
        z = a.z
        print(f"  [{i}.{k+1}] x={x:.2f}  y={y:.2f}  z={z:.2f}  radius={a.radius:.2f}cm")

# Save
save_results(top5, cfg, "output/results_final.json")
print(f"\nSaved: output/results_final.json")
total = t_ga + t_re
print(f"Total: {total:.0f}s ({total/60:.1f}min)")
