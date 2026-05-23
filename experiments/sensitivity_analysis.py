"""
민감도 분석 — 현재 모델이 파라미터 변동에 얼마나 민감한지 측정.

실험 A: pruning_probability
실험 B: score weights
실험 C: 재현성 (seed 변경)

사용법:
    python experiments/sensitivity_analysis.py

결과:
    output/sensitivity/ 디렉토리에 JSON 저장
    요약 문자열 출력
"""
from __future__ import annotations

import json
import math
import time
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import SimConfig
from src.search import run_search, save_results


def _top5_overlap(ref: List[Dict], comp: List[Dict]) -> float:
    def _signature(r: Dict) -> List[Tuple[float, float]]:
        return sorted((a.r, a.z) for a in r["airrooms"])

    def _match(sig_a, sig_b) -> bool:
        if len(sig_a) != len(sig_b):
            return False
        for (r1, z1), (r2, z2) in zip(sig_a, sig_b):
            if abs(r1 - r2) > 1.0 or abs(z1 - z2) > 1.0:
                return False
        return True

    ref_sigs = [_signature(r) for r in ref]
    comp_sigs = [_signature(r) for r in comp]

    matches = 0
    for cs in comp_sigs:
        for rs in ref_sigs:
            if _match(cs, rs):
                matches += 1
                break
    return matches / len(ref)


def _cv(scores: List[float]) -> float:
    if not scores:
        return 0.0
    m = sum(scores) / len(scores)
    if m == 0:
        return 0.0
    var = sum((s - m) ** 2 for s in scores) / len(scores)
    return math.sqrt(var) / m


def _fmt_top5(top5: List[Dict]) -> str:
    lines = []
    for r in top5:
        s = r["score"]
        lines.append(
            f"  #{r['rank']}: Mean={r['mean_score']:.0f}±{r['std_score']:.0f}  "
            f"Air={r['n_airrooms']}  "
            f"S={s['metrics']['surface_area_mm2']:.0f}mm2  "
            f"P={s['metrics']['pruning_count']}  "
            f"Spread={s['metrics']['spread_ratio']:.0%}"
        )
    return "\n".join(lines)


def experiment_a_pruning_prob(
    base_cfg: SimConfig, output_dir: Path
) -> Dict:
    values = [0.3, 0.6, 0.85, 1.0]
    results: Dict[str, List[Dict]] = {}
    runtimes = []

    print("\n" + "=" * 60)
    print("실험 A: Pruning Probability 민감도")
    print("=" * 60)

    for pp in values:
        cfg = deepcopy(base_cfg)
        cfg.root.pruning_probability = pp
        t0 = time.time()
        top5 = run_search(cfg)
        elapsed = time.time() - t0
        runtimes.append(elapsed)
        key = f"pp_{pp}"
        results[key] = top5
        save_results(top5, cfg, str(output_dir / f"{key}.json"))
        print(f"\npruning_probability = {pp} ({elapsed:.0f}s)")
        print(_fmt_top5(top5))

    ref_key = "pp_0.85"
    print(f"\n── 기준({ref_key}) 대비 Overlap ──")
    for key, top5 in results.items():
        ov = _top5_overlap(results[ref_key], top5)
        print(f"  {key}: Overlap={ov:.0%}")

    print(f"\n── 1등 점수 변화 ──")
    for key, top5 in results.items():
        if not top5:
            continue
        r1 = top5[0]
        print(f"  {key}: score={r1['mean_score']:.0f}±{r1['std_score']:.0f}  "
              f"pruning={r1['score']['metrics']['pruning_count']}  "
              f"surface={r1['score']['metrics']['surface_area_mm2']:.0f}")

    return results


def experiment_b_score_weights(
    base_cfg: SimConfig, output_dir: Path
) -> Dict:
    results: Dict[str, List[Dict]] = {}

    print("\n" + "=" * 60)
    print("실험 B: Score Weight 민감도")
    print("=" * 60)

    for pw in [4.0, 5.0, 6.0]:
        cfg = deepcopy(base_cfg)
        cfg.score.pruning_weight = pw
        t0 = time.time()
        top5 = run_search(cfg)
        print(f"\npruning_weight = {pw} ({time.time()-t0:.0f}s)")
        print(_fmt_top5(top5))
        key = f"pw_{pw}"
        results[key] = top5
        save_results(top5, cfg, str(output_dir / f"{key}.json"))

    for sw in [40.0, 50.0, 60.0]:
        cfg = deepcopy(base_cfg)
        cfg.score.soil_loss_weight = sw
        t0 = time.time()
        top5 = run_search(cfg)
        print(f"\nsoil_loss_weight = {sw} ({time.time()-t0:.0f}s)")
        print(_fmt_top5(top5))
        key = f"sw_{sw}"
        results[key] = top5
        save_results(top5, cfg, str(output_dir / f"{key}.json"))

    ref_key = "pw_5.0"
    print(f"\n── 기준({ref_key}) 대비 Overlap ──")
    for key, top5 in results.items():
        if key == ref_key:
            continue
        ov = _top5_overlap(results[ref_key], top5)
        print(f"  {key}: Overlap={ov:.0%}")

    print(f"\n── 1등 점수 변화 ──")
    for key, top5 in results.items():
        if not top5:
            continue
        r1 = top5[0]
        print(f"  {key}: score={r1['mean_score']:.0f}  "
              f"surface={r1['score']['metrics']['surface_area_mm2']:.0f}  "
              f"pruning={r1['score']['metrics']['pruning_count']}  "
              f"soil_loss={r1['score']['metrics']['soil_loss_ratio']:.2%}")

    return results


def experiment_c_reproducibility(
    base_cfg: SimConfig, output_dir: Path
) -> Dict:
    seeds = [42, 99, 177, 255, 333]
    results: Dict[str, List[Dict]] = {}

    print("\n" + "=" * 60)
    print("실험 C: 재현성 (Seed 변경)")
    print("=" * 60)

    for seed in seeds:
        cfg = deepcopy(base_cfg)
        cfg.seed = seed
        t0 = time.time()
        top5 = run_search(cfg)
        elapsed = time.time() - t0
        results[f"seed_{seed}"] = top5
        save_results(top5, cfg, str(output_dir / f"repro_seed_{seed}.json"))
        print(f"\nseed = {seed} ({elapsed:.0f}s)")
        print(_fmt_top5(top5))

    print(f"\n── Seed 간 Top5 Overlap ──")
    keys = list(results.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ov = _top5_overlap(results[keys[i]], results[keys[j]])
            print(f"  {keys[i]} vs {keys[j]}: Overlap={ov:.0%}")

    print(f"\n── 1등 점수 변동 ──")
    top_scores = []
    for key, top5 in results.items():
        if not top5:
            continue
        top_scores.append(top5[0]["mean_score"])
        print(f"  {key}: 1등 score = {top5[0]['mean_score']:.0f}")
    if top_scores:
        avg = sum(top_scores) / len(top_scores)
        var = sum((s - avg) ** 2 for s in top_scores) / len(top_scores)
        print(f"  평균 = {avg:.0f}")
        print(f"  표준편차 = {math.sqrt(var):.0f}")
        print(f"  CV = {_cv(top_scores):.2%}")

    return results


def main():
    base_cfg = SimConfig.from_json("configs/mvp.json")
    base_cfg.search.n_candidates = 200
    base_cfg.search.n_eval_seeds = 3

    output_dir = Path("output/sensitivity")
    output_dir.mkdir(parents=True, exist_ok=True)

    results_a = experiment_a_pruning_prob(base_cfg, output_dir)
    results_b = experiment_b_score_weights(base_cfg, output_dir)
    results_c = experiment_c_reproducibility(base_cfg, output_dir)

    print("\n" + "=" * 60)
    print("민감도 분석 요약")
    print("=" * 60)

    print("""
A. Pruning Probability:
   pp=0.3~1.0에서 Top5 Overlap과 1등 점수 변화 확인.
   Overlap < 50%면 프루닝 확률이 결과를 크게 좌우함 (모델 불안정).
   Overlap > 80%면 결과가 확률에 둔감함 (모델 안정적).

B. Score Weights:
   weight ±20%에서 1등 설계가 바뀌는지 확인.
   1등이 바뀌면 현재 weight 근처에서 순위가 불안정한 영역.

C. 재현성:
   1등 점수 CV < 10%: 재현성 우수.
   1등 점수 CV > 20%: 단일 실행 결과 신뢰 곤란, n_eval_seeds 증가 필요.
   1등 점수 CV > 30%: 모델에 근본적인 문제 (랜덤성 과다).
""")


if __name__ == "__main__":
    main()
