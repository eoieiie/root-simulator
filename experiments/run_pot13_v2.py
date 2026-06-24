"""
V2: G=1.3, GA 다양성↑, 15-seed 재평가.
- Scale old best design → seed genome for new pot (6.5x15cm)
- GA (pop=25, gen=15, eval_seeds=5)
- Re-evaluate Top5 with 15 seeds for reliability
"""
import json, math, time, sys, os, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import SimConfig
from src.search import run_ga_search, save_results, RandomSearch
from src.pipeline import SimPipeline

print("=" * 65)
print("POT 13 V2: Comprehensive GA + Reliability Evaluation")
print("=" * 65)

# --- Load old best design ---
with open("output/results_precision_final.json") as f:
    old = json.load(f)
b = old["results"][0]
print(f"\nOld best: Score={b['mean_score']:.0f}, {b['n_airrooms']} airrooms")

# --- Scale to new pot (r=6.5, h=15) ---
r_scale = 6.5 / 12.0
z_scale = 15.0 / 20.0

old_ars = b["airroom_positions"]
scaled = []
for a in old_ars:
    sr = max(1.8, min(4.7, a["r_cm"] * r_scale))
    sz = max(1.8, min(13.2, a["z_cm"] * z_scale))
    srad = max(0.5, min(0.9, a["radius_cm"] * min(r_scale, z_scale)))
    scaled.append((sr, sz, srad))

# Cluster 10 -> 6 by merging closest pairs
def dist2(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

clusters = list(scaled)
while len(clusters) > 6:
    min_d, mi, mj = float("inf"), 0, 1
    for i in range(len(clusters)):
        for j in range(i+1, len(clusters)):
            d = dist2(clusters[i], clusters[j])
            if d < min_d:
                min_d, mi, mj = d, i, j
    c = ((clusters[mi][0]+clusters[mj][0])/2,
         (clusters[mi][1]+clusters[mj][1])/2,
         (clusters[mi][2]+clusters[mj][2])/2)
    clusters[mi] = c
    del clusters[mj]

seed_genome = [(round(r,2), round(z,2), round(rad,2)) for r, z, rad in clusters]
print("Seed genome (6 airrooms):")
for i, (r, z, rad) in enumerate(seed_genome):
    print(f"  {i+1}: r={r:.2f} z={z:.2f} rad={rad:.2f}")

# --- GA Run ---
cfg = SimConfig.from_json("configs/pot_13.json")
print(f"\nGA: pop={cfg.ga.population}, gen={cfg.ga.generations}, "
      f"elite={cfg.ga.elite_frac}, mut_sigma={cfg.ga.mutation_sigma_cm}")
print(f"Tropism: g={cfg.tropism.g}")
print(f"Eval seeds: {cfg.search.n_eval_seeds} (GA internal)")
t0 = time.time()
top5 = run_ga_search(cfg, seed_genome=seed_genome)
t_ga = time.time() - t0
print(f"GA complete: {t_ga:.0f}s ({t_ga/60:.1f}min)")

print("\n--- Top5 (GA, internal eval) ---")
print(RandomSearch.format_top5(top5))

# --- Re-evaluate Top5 with 15 seeds ---
RE_EVAL_SEEDS = 15
print(f"\n--- Re-evaluating Top{len(top5)} with {RE_EVAL_SEEDS} seeds ---")
t0 = time.time()
eval_seeds = [cfg.seed + i for i in range(RE_EVAL_SEEDS)]
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
    entry["n_eval_seeds"] = RE_EVAL_SEEDS
    # Also re-evaluate the best's full score dict
    if entry is top5[0]:
        entry["score"] = r["score"]

t_re = time.time() - t0
top5.sort(key=lambda x: -x["mean_score"])
for i, entry in enumerate(top5):
    entry["rank"] = i + 1

print(f"\nRe-evaluation complete: {t_re:.0f}s ({t_re/60:.1f}min)")

# --- Final Results ---
print("\n" + "=" * 65)
print("FINAL RESULTS (15-seed re-evaluation)")
print("=" * 65)
print()
for i, entry in enumerate(top5):
    print(f"#{entry['rank']}: Mean={entry['mean_score']:.0f}±{entry['std_score']:.0f}  "
          f"Airrooms={entry['n_airrooms']}  Seeds={entry['n_eval_seeds']}")
    s = entry["score"]
    print(f"       S={s['metrics']['surface_area_mm2']:.0f}mm²  "
          f"P={s['metrics']['pruning_count']}회  "
          f"L={s['metrics']['soil_loss_ratio']*100:.1f}%  "
          f"N={s['metrics']['n_uptake_mg']:.4f}mg")
    print()

best = top5[0]
print("=== BEST DESIGN DETAILS ===")
print(f"Score: mean={best['mean_score']:.0f} std={best['std_score']:.0f}")
print(f"All scores ({len(best['all_scores'])}): {best['all_scores']}")
s = best["score"]
print(f"\nComponents (from last seed {RE_EVAL_SEEDS-1}):")
print(f"  Surface area: {s['metrics']['surface_area_mm2']:.0f} mm²")
print(f"  Pruning count: {s['metrics']['pruning_count']}")
print(f"  Soil loss: {s['metrics']['soil_loss_ratio']*100:.1f}%")
print(f"  N uptake: {s['metrics']['n_uptake_mg']:.4f} mg")
print(f"  Spread ratio: {s['metrics']['spread_ratio']*100:.1f}%")
zones = s["metrics"].get("pruning_by_zone", {})
print(f"  Pruning by zone: L={zones.get('lower',0)} M={zones.get('middle',0)} U={zones.get('upper',0)}")

print("\nAirroom positions:")
for i, a in enumerate(best["airrooms"], 1):
    print(f"  {i}: r={a.r:.2f} z={a.z:.2f} rad={a.radius:.2f}")

# --- Save ---
save_results(top5, cfg, "output/results_pot13_v2_final.json")
print(f"\nSaved: output/results_pot13_v2_final.json")
print(f"Total time: {(t_ga+t_re):.0f}s ({(t_ga+t_re)/60:.1f}min)")
