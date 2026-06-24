"""Evaluate the V3 best design with 15 seeds and save final result."""
import json, time, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import SimConfig
from src.geometry import Airroom
from src.pipeline import SimPipeline

# V3 best design airrooms (from noise=8, g=1.0 run)
best_airrooms_data = [
    (2.05, 3.55, 0.71),
    (1.96, 6.26, 0.82),
    (3.91, 5.70, 0.50),
    (3.12, 12.15, 0.70),
    (2.46, 4.56, 0.86),
    (1.80, 2.58, 0.90),
]

cfg = SimConfig.from_json("configs/pot_13.json")
pipe = SimPipeline(cfg)

# Create airroom objects
airrooms = []
for r, z, rad in best_airrooms_data:
    ar = Airroom(r=r, z=z, radius=rad, pruning_zone_factor=cfg.airroom.pruning_zone_factor)
    airrooms.append(ar)

# Evaluate with 15 seeds
N_SEEDS = 15
eval_seeds = [cfg.seed + i for i in range(N_SEEDS)]
all_scores = []
last_result = None
pz = {}  # pruning zones cumulative

for s in eval_seeds:
    result = pipe.run(seed=s, airrooms_override=airrooms, max_steps=500)
    sc = result["score"]
    total = sc["total"]
    all_scores.append(total)
    metrics = sc["metrics"]
    pz = metrics.get("pruning_by_zone", {"lower":0,"middle":0,"upper":0})
    last_result = result

mean = sum(all_scores) / len(all_scores)
std = (sum((x - mean)**2 for x in all_scores) / len(all_scores))**0.5

# Build save structure
entry = {
    "rank": 1,
    "n_airrooms": len(airrooms),
    "mean_score": round(mean, 1),
    "std_score": round(std, 2),
    "all_scores": [round(s, 1) for s in all_scores],
    "n_eval_seeds": N_SEEDS,
    "surface_area_mm2": round(last_result["score"]["metrics"]["surface_area_mm2"], 1),
    "pruning_count": last_result["score"]["metrics"]["pruning_count"],
    "soil_loss_ratio": round(last_result["score"]["metrics"]["soil_loss_ratio"], 4),
    "spread_ratio": round(last_result["score"]["metrics"]["spread_ratio"], 4),
    "n_uptake_mg": round(last_result["score"]["metrics"]["n_uptake_mg"], 4),
    "pruning_by_zone": pz,
    "airroom_positions": [
        {"r_cm": round(a.r, 2), "z_cm": round(a.z, 2), "radius_cm": round(a.radius, 2)}
        for a in airrooms
    ],
    "config_g": cfg.tropism.g,
    "config_noise_deg": cfg.root.noise_deg,
}

result_file = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "config_method": "ga",
    "description": "V3 Best Design — noise=8°, g=1.0, 15-seed evaluation",
    "config_pot": {"radius_cm": cfg.pot.radius_cm, "height_cm": cfg.pot.height_cm},
    "config_ga": {
        "population": cfg.ga.population,
        "generations": cfg.ga.generations,
        "elite_frac": cfg.ga.elite_frac,
        "mutation_sigma_cm": cfg.ga.mutation_sigma_cm,
    },
    "results": [entry],
}

with open("output/results_v3_final.json", "w") as f:
    json.dump(result_file, f, indent=2, ensure_ascii=False)

print("=== V3 FINAL RESULT (15 seeds) ===")
print(f"Mean={mean:.0f}  Std={std:.0f}")
print(f"Scores: {[round(s,0) for s in all_scores]}")
print(f"Surface={entry['surface_area_mm2']:.0f}mm²  Pruning={entry['pruning_count']}회")
print(f"Soil Loss={entry['soil_loss_ratio']*100:.1f}%  N Uptake={entry['n_uptake_mg']:.4f}mg")
print(f"Spread={entry['spread_ratio']*100:.1f}%  Zones=L{pz.get('lower',0)}/M{pz.get('middle',0)}/U{pz.get('upper',0)}")
print(f"\nSaved: output/results_v3_final.json")
