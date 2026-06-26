"""대칭 배치 15시드 평가 → GA 최적 결과와 비교"""
import os, sys, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import SimConfig
from src.pipeline import SimPipeline
from src.geometry import Airroom

POT_R = 6.5; POT_H = 15.0
SEEDS = list(range(42, 57))  # 15 seeds (42..56)

# 대칭 6개 (2r × 3h) — 싱글시드에서 잘 나온 config
SYM_6 = []
for r in [2.0, 4.5]:
    for z in [3.5, 7.5, 11.5]:
        SYM_6.append(Airroom(r=r, z=z, radius=0.65))

def run_seed(cfg_path, airrooms, seed):
    cfg = SimConfig.from_json(cfg_path)
    pipeline = SimPipeline(cfg)
    result = pipeline.run(seed=seed, airrooms_override=airrooms)
    rs = result["root_system"]
    st = rs.statistics()
    sc = result["score"]
    return {
        "seed": seed,
        "score": sc['total'],
        "surface_area_mm2": st['total_surface_area_mm2'],
        "pruning_count": st['pruning_count'],
        "pruning_by_zone": st['pruning_by_zone'],
        "n_uptake_mg": sc['metrics']['n_uptake_mg'],
        "spread_ratio": sc['metrics']['spread_ratio'],
        "segments": st['total_segments'],
        "soil_loss": sc['metrics']['soil_loss_ratio'],
    }

if __name__ == "__main__":
    cfg_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'pot_13.json')

    print("="*55)
    print("대칭 배치(2r×3h) 15시드 전체 평가")
    print("="*55)
    print(f"에어룸: 6개 (2r × 3h)")
    for i, ar in enumerate(SYM_6, 1):
        print(f"  {i}: r={ar.r:.2f}  z={ar.z:.2f}  rad={ar.radius:.2f}")
    print(f"시드: {SEEDS[0]}..{SEEDS[-1]} ({len(SEEDS)}개)")
    print()

    all_results = []
    for seed in SEEDS:
        r = run_seed(cfg_path, SYM_6, seed)
        all_results.append(r)
        print(f"  seed={seed:3d}  score={r['score']:7.1f}  "
              f"surface={r['surface_area_mm2']:5.0f}  "
              f"prune={r['pruning_count']:2d}  "
              f"spread={r['spread_ratio']:.3f}")

    # 통계
    scores = [r['score'] for r in all_results]
    surfaces = [r['surface_area_mm2'] for r in all_results]
    prunings = [r['pruning_count'] for r in all_results]
    uptakes = [r['n_uptake_mg'] for r in all_results]
    spreads = [r['spread_ratio'] for r in all_results]

    mean_s = np.mean(scores)
    std_s  = np.std(scores, ddof=1)
    mean_surf = np.mean(surfaces)
    mean_prn = np.mean(prunings)
    mean_upt = np.mean(uptakes)
    mean_spr = np.mean(spreads)

    # GA 최종 결과 (results_final.json)
    ga_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'results_final.json')
    if os.path.exists(ga_path):
        with open(ga_path) as f: ga_data = json.load(f)
        ga_r1 = ga_data['results'][0]
        ga_mean = ga_r1['mean_score']
        ga_std  = ga_r1['std_score']
        ga_surf = ga_r1['surface_area_mm2']
        ga_prn  = ga_r1['pruning_count']
        ga_spr  = ga_r1['spread_ratio']
    else:
        ga_mean = ga_std = ga_surf = ga_prn = ga_spr = 0

    print("\n" + "="*55)
    print("최종 비교")
    print("="*55)
    print(f"{'':30s} {'GA 최적(6개)':>16s} {'대칭 6개':>16s} {'차이':>10s}")
    print(f"{'─'*72}")
    print(f"{'Score':30s} {ga_mean:>8.0f} ±{ga_std:<5.0f} {mean_s:>8.0f} ±{std_s:<5.0f} "
          f"{'△' if mean_s>ga_mean else '▽'}{abs(mean_s-ga_mean):>5.0f}")
    print(f"{'표면적(mm²)':30s} {ga_surf:>16.0f} {mean_surf:>16.0f} "
          f"{'△' if mean_surf>ga_surf else '▽'}{abs(mean_surf-ga_surf):>5.0f}")
    print(f"{'프루닝(회)':30s} {ga_prn:>16.0f} {mean_prn:>16.0f} "
          f"{'△' if mean_prn>ga_prn else '▽'}{abs(mean_prn-ga_prn):>5.0f}")
    print(f"{'질소흡수(mg)':30s} {'-':>16} {mean_upt:>16.3f}")
    print(f"{'Spread':30s} {ga_spr:>16.3f} {mean_spr:>16.3f}")

    print("\n세부 점수:", sorted(scores))
    print(f"Min={min(scores):.0f}  Max={max(scores):.0f}  "
          f"Range={max(scores)-min(scores):.0f}")

    # 저장
    out_data = {
        "config": "symmetric_2rx3h",
        "n_airrooms": 6,
        "positions": [(ar.r, ar.z, ar.radius) for ar in SYM_6],
        "n_seeds": len(SEEDS),
        "seeds": SEEDS,
        "results": all_results,
        "summary": {
            "mean_score": round(mean_s, 1),
            "std_score": round(std_s, 1),
            "mean_surface_area_mm2": round(mean_surf, 1),
            "mean_pruning_count": round(mean_prn, 1),
            "mean_n_uptake_mg": round(mean_upt, 4),
            "mean_spread_ratio": round(mean_spr, 4),
        },
        "comparison_vs_ga": {
            "ga_mean": ga_mean,
            "ga_std": ga_std,
            "sym_mean": round(mean_s, 1),
            "sym_std": round(std_s, 1),
            "diff": round(mean_s - ga_mean, 1),
        }
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'results_symmetric.json')
    with open(out_path, 'w') as f:
        json.dump(out_data, f, indent=2)
    print(f"\n저장: {out_path}")
    print("="*55)
