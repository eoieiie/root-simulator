"""13cm pot (r=6.5, h=15) GA optimization with seed from old best design."""
import json, math, time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import SimConfig
from src.search import run_ga_search, save_results, RandomSearch

# ============================================================
# PART 1: Interpret old results
# ============================================================
with open('output/results_precision_final.json') as f:
    old = json.load(f)
b = old['results'][0]

print("=" * 65)
print("PART 1: OLD RESULT INTERPRETATION (12x20cm pot, 0.3cm voxel)")
print("=" * 65)
print()

print("Rank:", b['rank'])
print("Config:", old['config_method'], "| GA pop gen:", b['n_airrooms'])
print()
print("--- Core Score ---")
print(f"mean_score = {b['mean_score']:.0f} — 5개 시드 평균 (GA 피트니스)")
print("  BUT: std_score=0.0, n_eval_seeds=1 — 최종보고 싱글시드 버그 (지금 수정)")
print()
print("--- Components ---")
print("Score = S(표면적) + P(프루닝) - L(흙손실) + N(양분흡수)")
print()
print(f"S = surface_area_mm2 x weight(1.0)")
print(f"  surface_area_mm2 = {b['surface_area_mm2']:.0f} — 전체 뿌리 표면적")
print(f"  모든 세그먼트 2*pi*r*L 합산. 클수록 흡수 유리.")
print()
print(f"P = pruning_count x weight(50.0)")
print(f"  pruning_count = {b['pruning_count']} — 에어룸 닿아 프루닝된 횟수")
print(f"  PLOS ONE 2018: 프루닝 72h 후 측근 6배 증가")
print(f"  현재 16회 — 랜덤설계(75회)보다 적지만 흙손실 적음")
print()
print(f"L = soil_loss_ratio x weight(1000.0)")
print(f"  soil_loss_ratio = {b['soil_loss_ratio']:.4f} ({b['soil_loss_ratio']*100:.2f}%)")
print(f"  에어룸 체적/화분 체적. 높으면 패널티.")
print()
print("--- Spatial ---")
print(f"spread_ratio = {b['spread_ratio']:.4f} ({b['spread_ratio']*100:.2f}%)")
print(f"  뿌리가 방문한 복셀 비율. 높을수록 공간활용 우수")
print()
print("pruning_by_zone:", b['pruning_by_zone'])
print("  하단(lower)에만 프루닝 집중 — 중력 편향. 개선 필요")
print()
print(f"Airrooms: {b['n_airrooms']}개, 두 클러스터:")
for a in b['airroom_positions']:
    print(f"  r={a['r_cm']:.1f} z={a['z_cm']:.1f} rad={a['radius_cm']:.2f}")
print("  Cluster A (하단 z=3~9.6): 6개, r=3~5 — 초기 프루닝")
print("  Cluster B (상단 z=12~16): 4개, r=5~8 — 확장 영역")
print()

# ============================================================
# PART 2: Scale to new pot (r=6.5, h=15)
# ============================================================
print("=" * 65)
print("PART 2: SCALE TO NEW POT (r=6.5, h=15, voxel=0.2)")
print("=" * 65)

r_scale = 6.5 / 12.0
z_scale = 15.0 / 20.0
print(f"Scale: r={r_scale:.3f}, z={z_scale:.3f}")

old_ars = b['airroom_positions']
scaled = []
for a in old_ars:
    sr = max(2.0, min(4.5, a['r_cm'] * r_scale))
    sz = max(2.0, min(13.0, a['z_cm'] * z_scale))
    srad = max(0.5, min(0.9, a['radius_cm'] * min(r_scale, z_scale)))
    scaled.append((round(sr, 2), round(sz, 2), round(srad, 2)))

print("Scaled 10 airrooms:")
for i, (r, z, rad) in enumerate(scaled):
    print(f"  {i+1}: r={r} z={z} rad={rad}")

# Cluster 10 -> 6 by merging closest pairs
def dist2(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

clusters = list(scaled)
while len(clusters) > 6:
    min_d, mi, mj = float('inf'), 0, 1
    for i in range(len(clusters)):
        for j in range(i+1, len(clusters)):
            d = dist2(clusters[i], clusters[j])
            if d < min_d:
                min_d, mi, mj = d, i, j
    # merge: centroid
    c = ((clusters[mi][0]+clusters[mj][0])/2,
         (clusters[mi][1]+clusters[mj][1])/2,
         (clusters[mi][2]+clusters[mj][2])/2)
    clusters[mi] = c
    del clusters[mj]

seed_genome = [(r, z, rad) for r, z, rad in clusters]
print()
print("Clustered to 6 (seed genome):")
for i, (r, z, rad) in enumerate(seed_genome):
    print(f"  {i+1}: r={r:.2f} z={z:.2f} rad={rad:.2f}")

# ============================================================
# PART 3: GA on new pot
# ============================================================
print()
print("=" * 65)
print("PART 3: GA ON 13cm POT (pop=20, gen=12, eval=5 seeds)")
print("=" * 65)
print("Est: 20x12x5=1200 runs, ~40min")
print()

cfg = SimConfig.from_json("configs/pot_13.json")
t0 = time.time()
top5 = run_ga_search(cfg, seed_genome=seed_genome)
elapsed = time.time() - t0

print()
print(f"COMPLETE in {elapsed:.0f}s ({elapsed/60:.1f}min)")
print()
print("Top 5:")
print(RandomSearch.format_top5(top5))
save_results(top5, cfg, "output/results_pot13_final.json")

# Show best
best = top5[0]
print()
print("=== BEST DESIGN ===")
print(f"Score: mean={best['mean_score']:.0f} std={best['std_score']:.0f}")
print(f"n_eval_seeds={best['n_eval_seeds']} all_scores={best['all_scores']}")
s = best['score']
print(f"S={s['metrics']['surface_area_mm2']:.0f}mm2  P={s['metrics']['pruning_count']}회  L={s['metrics']['soil_loss_ratio']*100:.1f}%  N={s['metrics']['n_uptake_mg']:.4f}mg")
print()
print("Airrooms (new pot best):")
for i, a in enumerate(best['airrooms'], 1):
    print(f"  {i}: r={a.r:.2f} z={a.z:.2f} rad={a.radius:.2f}")
