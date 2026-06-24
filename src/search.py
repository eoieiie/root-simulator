"""탐색 (랜덤/GA) — 설계 공간 탐색 및 최적화.

plan.md §6 Phase D 참조.
search.method="random" → RandomSearch
search.method="ga" → GeneticOptimizer
search.n_eval_seeds: 설계당 평가 시드 수. 클수록 robust.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional

from .config import SimConfig
from .pipeline import SimPipeline


def _mean_score(scores: List[float]) -> float:
    return sum(scores) / len(scores)


def _std_score(scores: List[float]) -> float:
    m = _mean_score(scores)
    var = sum((s - m) ** 2 for s in scores) / len(scores)
    return math.sqrt(var)


class RandomSearch:
    """랜덤 탐색: n_candidates개 생성 → 다중시드 평균 점수순 정렬 → top_k."""

    def __init__(self, config: SimConfig):
        self.config = config
        self.pipeline = SimPipeline(config)

    def run(
        self,
        n_candidates: Optional[int] = None,
        top_k: Optional[int] = None,
        include_zero_airroom: bool = True,
    ) -> List[Dict]:
        """랜덤 탐색 실행. 각 설계를 n_eval_seeds개 시드로 평가, 평균 점수로 순위.

        Args:
            n_candidates: 생성할 후보 수 (None=config.search.n_candidates)
            top_k: 출력할 상위 개수 (None=config.search.top_k)
            include_zero_airroom: True면 에어룸 0개 케이스도 후보에 포함

        Returns:
            상위 top_k개 결과 리스트. 각 결과에 평균/표준편차 포함.
        """
        n_candidates = n_candidates or self.config.search.n_candidates
        top_k = top_k or self.config.search.top_k
        n_seeds = self.config.search.n_eval_seeds

        seeds = list(range(1000, 1000 + n_candidates))
        eval_seeds = [self.config.seed + i * 100 for i in range(n_seeds)]
        results: List[Dict] = []

        for i in range(n_candidates):
            if include_zero_airroom and i == 0:
                n_air = 0
            else:
                max_c = self.config.airroom.max_count
                n_air = random.Random(seeds[i]).randint(1, max_c)

            from .geometry import generate_random_airrooms
            ar = generate_random_airrooms(
                self.config, n=n_air, rng=random.Random(seeds[i] + 1000)
            )

            # 다중 시드 평가
            all_scores = []
            last_result = None
            for s in eval_seeds:
                result = self.pipeline.run(
                    seed=s,
                    airrooms_override=ar,
                    max_steps=500,
                )
                all_scores.append(result["score"]["total"])
                last_result = result

            entry = {
                "airrooms": ar,
                "n_airrooms": len(ar),
                "seed": seeds[i],
                "score": last_result["score"],
                "grid": last_result["grid"],
                "root_system": last_result["root_system"],
                "rank": 0,
                # 다중 시드 통계
                "mean_score": _mean_score(all_scores),
                "std_score": _std_score(all_scores),
                "all_scores": all_scores,
                "n_eval_seeds": n_seeds,
            }
            results.append(entry)

        # 평균 점수 내림차순 정렬
        results.sort(key=lambda r: r["mean_score"], reverse=True)
        for idx, r in enumerate(results):
            r["rank"] = idx + 1
        return results[:top_k]

    @staticmethod
    def format_top5(top5: List[Dict]) -> str:
        """Top5 결과를 읽기 쉬운 문자열로 포맷팅.

        다중 시드 평가 시 mean_score 기준, 단일 시드는 total 기준.
        """
        lines = []
        for r in top5:
            s = r["score"]
            score_str = f"Mean={r['mean_score']:.0f}±{r['std_score']:.0f}" if "mean_score" in r else f"Score={s['total']:.1f}"
            lines.append(
                f"  #{r['rank']}: {score_str}  "
                f"Airrooms={r['n_airrooms']}  "
                f"Surface={s['metrics']['surface_area_mm2']:.0f}mm2  "
                f"Pruning={s['metrics']['pruning_count']}  "
                f"Spread={s['metrics']['spread_ratio']:.0%}  "
                f"Zones=L{s['metrics']['pruning_by_zone']['lower']}"
                f"/M{s['metrics']['pruning_by_zone']['middle']}"
                f"/U{s['metrics']['pruning_by_zone']['upper']}"
            )
        return "\n".join(lines)


def run_ga_search(
    config: SimConfig,
    top_k: int = 5,
    eval_seeds: Optional[List[int]] = None,
    seed_genome: Optional[Genome] = None,
) -> List[Dict]:
    """GA 탐색 실행. RandomSearch와 동일한 반환 포맷.

    GeneticOptimizer로 airroom 배치 최적화.
    다중 시드 평가로 잡음 제거.

    Args:
        config: 설정
        top_k: 반환할 상위 개수
        eval_seeds: 평가용 시드 리스트 (None=seed만 사용)
        seed_genome: 초기 개체군에 주입할 시드 게놈 (이전 최적 설계 계승)
    """
    from .ga import GeneticOptimizer, Genome

    eval_seeds = eval_seeds or [config.seed, 99, 177, 255, 333]
    pipeline = SimPipeline(config)

    def _fitness(airrooms) -> float:
        scores = []
        for s in eval_seeds:
            r = pipeline.run(seed=s, airrooms_override=airrooms, max_steps=500)
            scores.append(r["score"]["total"])
        return sum(scores) / len(scores)

    opt = GeneticOptimizer(config, fitness_fn=_fitness, seed_genome=seed_genome)
    ga_result = opt.run()

    def _build_entry(airrooms) -> Dict:
        all_scores = []
        last_result = None
        for s in eval_seeds:
            r = pipeline.run(seed=s, airrooms_override=airrooms, max_steps=500)
            all_scores.append(r["score"]["total"])
            last_result = r
        mean_s = _mean_score(all_scores)
        std_s = _std_score(all_scores)
        return {
            "airrooms": airrooms,
            "n_airrooms": len(airrooms),
            "seed": config.seed,
            "score": last_result["score"],
            "grid": last_result["grid"],
            "root_system": last_result["root_system"],
            "rank": 0,
            "mean_score": mean_s,
            "std_score": std_s,
            "all_scores": all_scores,
            "n_eval_seeds": len(eval_seeds),
        }

    # 최종 개체군의 상위 top_k개를 반환
    candidates = [ga_result.best] + ga_result.final_population[:top_k]
    seen = set()
    unique = []
    for ind in candidates:
        key = tuple(sorted((a.r, a.z, a.radius) for a in ind.airrooms))
        if key not in seen:
            seen.add(key)
            unique.append(ind)

    entries = [_build_entry(ind.airrooms) for ind in unique[:top_k]]
    if entries:
        entries[0]["ga_history_best"] = ga_result.history_best
        entries[0]["ga_history_mean"] = ga_result.history_mean
        entries[0]["ga_n_evaluated"] = ga_result.n_evaluated

    entries.sort(key=lambda r: r["score"]["total"], reverse=True)
    for idx, r in enumerate(entries):
        r["rank"] = idx + 1
    return entries[:top_k]


def run_search(
    config: SimConfig,
    n_candidates: Optional[int] = None,
    top_k: Optional[int] = None,
) -> List[Dict]:
    """설정에 따라 랜덤/GA 탐색 실행.

    config.search.method:
        "random" → RandomSearch
        "ga" → GeneticOptimizer
    """
    method = config.search.method
    if method == "ga":
        return run_ga_search(config, top_k or config.search.top_k)
    return RandomSearch(config).run(
        n_candidates=n_candidates,
        top_k=top_k,
        include_zero_airroom=True,
    )


def save_results(
    top5: List[Dict],
    config: SimConfig,
    filepath: str,
) -> None:
    """Top5 결과를 JSON 파일로 저장.

    Args:
        top5: run_search() 결과 리스트
        config: 사용된 설정
        filepath: 저장 경로 (예: "output/results_20240101.json")
    """
    import json
    from datetime import datetime

    entries = []
    for r in top5:
        s = r["score"]
        entry = {
            "rank": r["rank"],
            "n_airrooms": r["n_airrooms"],
            "mean_score": round(r.get("mean_score", s["total"]), 1),
            "std_score": round(r.get("std_score", 0.0), 1),
            "all_scores": [round(v, 1) for v in r.get("all_scores", [s["total"]])],
            "n_eval_seeds": r.get("n_eval_seeds", 1),
            "surface_area_mm2": round(s["metrics"]["surface_area_mm2"], 1),
            "pruning_count": s["metrics"]["pruning_count"],
            "soil_loss_ratio": round(s["metrics"]["soil_loss_ratio"], 4),
            "spread_ratio": round(s["metrics"]["spread_ratio"], 4),
            "pruning_by_zone": s["metrics"]["pruning_by_zone"],
            # 에어룸 위치 정보 (grid/r/z)
            "airroom_positions": [
                {"r_cm": round(a.r, 2), "z_cm": round(a.z, 2), "radius_cm": round(a.radius, 2)}
                for a in r["airrooms"]
            ],
        }
        entries.append(entry)

    output = {
        "timestamp": datetime.now().isoformat(),
        "config_method": config.search.method,
        "config_n_candidates": config.search.n_candidates,
        "config_top_k": config.search.top_k,
        "config_n_eval_seeds": config.search.n_eval_seeds,
        "config_seed": config.seed,
        "species": {
            "initial_roots": config.root.initial_roots,
            "max_generation": config.root.max_generation,
        },
        "results": entries,
    }

    import pathlib
    p = pathlib.Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  saved results: {filepath}")
