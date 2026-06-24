"""GA 검증: config 로드 → GA 실행 → 랜덤 서치 200개와 비교."""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import SimConfig
from src.pipeline import SimPipeline
from src.ga import GeneticOptimizer
from src.search import RandomSearch, run_search

cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")

# Test 1: Config loads correctly
print("[1] Config validation (GA + Tropism)")
errors = cfg.validate()
if errors:
    for e in errors:
        print(f"  ERROR: {e}")
    raise SystemExit(1)
tc = cfg.tropism
print(f"  tropism: g={tc.g}, h={tc.h}, n={tc.n}")
ga = cfg.ga
print(f"  ga: pop={ga.population}, gen={ga.generations}, elite={ga.elite_frac}")
assert tc.g == 1.5 and tc.h == 0.0 and tc.n == 0.0
assert ga.population == 30 and ga.generations == 15
print("  OK")

# Test 2: GA basic run (fast: 3 pop, 2 gen)
print("\n[2] GA mini run (pop=3, gen=2, airrooms=4)")
mini_cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")
mini_cfg.ga.population = 3
mini_cfg.ga.generations = 2
mini_cfg.ga.airroom_count = 4
mini_cfg.ga.mutation_sigma_cm = 0.5

pipeline = SimPipeline(mini_cfg)
def _fitness(airrooms):
    r = pipeline.run(seed=42, airrooms_override=airrooms, max_steps=300)
    return r["score"]["total"]

opt = GeneticOptimizer(mini_cfg, fitness_fn=_fitness)
ga_result = opt.run()
best = ga_result.best
print(f"  Best: Score={best.fitness:.1f}, Airrooms={len(best.airrooms)}")
print(f"  History best: {[f'{v:.0f}' for v in ga_result.history_best]}")
print(f"  History mean: {[f'{v:.0f}' for v in ga_result.history_mean]}")
print(f"  Total evals: {ga_result.n_evaluated}")
assert ga_result.n_evaluated > 0
assert len(ga_result.history_best) == 2
print("  OK")

# Test 3: GA vs Random Search (multi-seed fitness + 충분한 평가)
print("\n[3] GA (pop=20, gen=10, n_air=10) vs Random (n=200)")
cmp_cfg = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")
cmp_cfg.ga.population = 30
cmp_cfg.ga.generations = 15
cmp_cfg.ga.airroom_count = 10
cmp_cfg.ga.mutation_sigma_cm = 1.5

# Multi-seed fitness: 3개 시드 평균 (잡음 제거)
eval_seeds = [42, 99, 177]
pipeline2 = SimPipeline(cmp_cfg)
def _fitness_multi(airrooms):
    scores = []
    for s in eval_seeds:
        r = pipeline2.run(seed=s, airrooms_override=airrooms, max_steps=500)
        scores.append(r["score"]["total"])
    return sum(scores) / len(scores)

opt2 = GeneticOptimizer(cmp_cfg, fitness_fn=_fitness_multi)
ga_res = opt2.run()
ga_best_score = max(ga_res.history_best)

# GA best의 실제 점수 (seed=42만)
p3 = SimPipeline(cmp_cfg)
ga_actual = _fitness_multi(ga_res.best.airrooms)

# Random run (200 candidates, 10 airrooms)
import random
rand_best_indiv = 0
rand_all = []
for i in range(200):
    from src.geometry import generate_random_airrooms
    ar = generate_random_airrooms(cmp_cfg, n=10, rng=random.Random(3000 + i))
    r = p3.run(seed=42, airrooms_override=ar, max_steps=500)
    rand_all.append(r["score"]["total"])
rand_best = max(rand_all)
rand_mean = sum(rand_all) / len(rand_all)

print(f"  GA history best: {[f'{v:.0f}' for v in ga_res.history_best]}")
print(f"  GA best (multi-seed avg): {ga_actual:.0f}")
print(f"  GA total evaluations: {ga_res.n_evaluated}")
print(f"  Random best (200): {rand_best:.0f}")
print(f"  Random mean (200):  {rand_mean:.0f}")
if ga_actual > rand_best:
    print(f"  GA > Random: +{(ga_actual/rand_best - 1)*100:+.1f}% ✅")
else:
    print(f"  GA < Random: {(ga_actual/rand_best - 1)*100:+.1f}% (에어룸 커버리지 증가 필요)")

# Test 4: run_search dispatcher
print("\n[4] run_search(method='ga') dispatcher")
cmp_cfg2 = SimConfig.from_json("E:/gwc-root-sim/configs/mvp.json")
cmp_cfg2.ga.population = 5
cmp_cfg2.ga.generations = 3
cmp_cfg2.ga.airroom_count = 6
cmp_cfg2.search.method = "ga"
results = run_search(cmp_cfg2, top_k=3)
print(f"  Top 1: Score={results[0]['score']['total']:.1f}  Airrooms={results[0]['n_airrooms']}")
print(f"  GA history present: {'ga_history_best' in results[0]}")
print(f"  GA evaluations: {results[0].get('ga_n_evaluated', '?')}")
assert "ga_history_best" in results[0]
assert "ga_n_evaluated" in results[0]
print("  OK")

# Test 5: Visualization of GA convergence
print("\n[5] GA convergence plot")
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
ax1, ax2 = axes
gens = list(range(1, len(ga_res.history_best) + 1))
ax1.plot(gens, ga_res.history_best, "b-o", label="Best")
ax1.plot(gens, ga_res.history_mean, "r--s", label="Mean")
ax1.set_xlabel("Generation")
ax1.set_ylabel("Fitness (Score)")
ax1.set_title("GA Convergence (multi-seed avg)")
ax1.legend()
ax1.grid(True)

# GA best airroom positions
best_ars = ga_res.best.airrooms
rs = [ar.r for ar in best_ars]
zs = [ar.z for ar in best_ars]
ax2.scatter(rs, zs, c="green", s=80, alpha=0.7)
circle = plt.Circle((0, 10), 12, fill=False, linestyle="--", color="gray")
ax2.add_patch(circle)
ax2.set_xlim(0, 13)
ax2.set_ylim(0, 21)
ax2.set_xlabel("r (cm)")
ax2.set_ylabel("z (cm)")
ax2.set_title(f"GA Best Airroom Positions")
ax2.set_aspect("equal")
ax2.invert_yaxis()

plt.tight_layout()
plt.savefig("E:/gwc-root-sim/output/test_ga_viz.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  Saved output/test_ga_viz.png  OK")

print("\n=== GA ALL TESTS PASSED ===")
