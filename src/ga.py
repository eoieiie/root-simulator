"""유전 알고리즘 기반 에어룸 배치 최적화.

2D r-z 단면 최적화용 GA.
Genome: [(r0, z0, radius0), (r1, z1, radius1), ..., (rN, zN, radiusN)]
  N = GAConfig.airroom_count
  radius는 에어룸 반경 (cm). genome에 포함시켜 재현성 확보.
Fitness: G-Health Score (Pipeline.run)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .config import SimConfig
from .geometry import Airroom

Genome = List[Tuple[float, float, float]]


@dataclass
class GAIndividual:
    genome: Genome
    fitness: float = 0.0
    airrooms: List[Airroom] = field(default_factory=list)


@dataclass
class GAResult:
    best: GAIndividual
    history_best: List[float]
    history_mean: List[float]
    n_evaluated: int
    final_population: List[GAIndividual] = field(default_factory=list)  # top N 최종 개체군


class GeneticOptimizer:
    """에어룸 배치 최적화용 GA.

    사용법:
        go = GeneticOptimizer(cfg, fitness_fn)
        result = go.run()
        print(result.best.airrooms)
    """

    def __init__(
        self,
        config: SimConfig,
        fitness_fn: Callable[[List[Airroom]], float],
        rng: Optional[random.Random] = None,
        seed_genome: Optional[Genome] = None,
    ):
        self.cfg = config
        self.ga_cfg = config.ga
        self.fitness_fn = fitness_fn
        self.rng = rng or random.Random(config.seed + 999)
        self.seed_genome = seed_genome

        self.n_airrooms = self.ga_cfg.airroom_count
        self.pot_r = config.pot.radius_cm
        self.pot_h = config.pot.height_cm
        self.airroom_r_min: float = config.airroom.radius_range_cm[0]
        self.airroom_r_max: float = config.airroom.radius_range_cm[1]

    def _genome_to_airrooms(self, genome: Genome) -> List[Airroom]:
        return [
            Airroom(
                r=r,
                z=z,
                radius=radius,
                pruning_zone_factor=self.cfg.airroom.pruning_zone_factor,
            )
            for r, z, radius in genome
        ]

    def _random_genome(self) -> Genome:
        margin = self.airroom_r_max * 2.0
        genome: Genome = []
        for _ in range(self.n_airrooms):
            r = self.rng.uniform(margin, self.pot_r - margin)
            z = self.rng.uniform(margin, self.pot_h - margin)
            radius = self.rng.uniform(self.airroom_r_min, self.airroom_r_max)
            genome.append((r, z, radius))
        return genome

    def _spawn_population(self, n: int) -> List[GAIndividual]:
        pop = [GAIndividual(genome=self._random_genome()) for _ in range(n)]
        # 시드 게놈이 있으면 첫 번째 개체로 삽입
        if self.seed_genome is not None:
            # 게놈 길이 맞추기 (부족하면 패딩, 넘치면 자름)
            sg = list(self.seed_genome)
            while len(sg) < self.n_airrooms:
                sg.append(self._random_genome()[0])
            pop[0] = GAIndividual(genome=sg[:self.n_airrooms])
        return pop

    # ── 평가 ──────────────────────────────────────────────

    def _evaluate(self, ind: GAIndividual) -> float:
        airrooms = self._genome_to_airrooms(ind.genome)
        ind.airrooms = airrooms
        ind.fitness = self.fitness_fn(airrooms)
        return ind.fitness

    def _mutate(self, genome: Genome) -> Genome:
        sigma = self.ga_cfg.mutation_sigma_cm
        idx = self.rng.randint(0, len(genome) - 1)
        r, z, radius = genome[idx]
        margin = self.airroom_r_max * 2.0
        r += self.rng.gauss(0, sigma)
        z += self.rng.gauss(0, sigma)
        radius += self.rng.gauss(0, sigma * 0.3)
        r = max(margin, min(self.pot_r - margin, r))
        z = max(margin, min(self.pot_h - margin, z))
        radius = max(self.airroom_r_min, min(self.airroom_r_max, radius))
        new = list(genome)
        new[idx] = (r, z, radius)
        return new

    # ── 교차 ──────────────────────────────────────────────

    def _crossover(self, a: Genome, b: Genome) -> Genome:
        n = len(a)
        pt = self.rng.randint(1, n - 1)
        return a[:pt] + b[pt:]

    # ── 실행 ──────────────────────────────────────────────

    def run(self) -> GAResult:
        pop_n = max(4, self.ga_cfg.population)
        gen_n = max(1, self.ga_cfg.generations)
        elite_n = max(1, int(math.ceil(self.ga_cfg.elite_frac * pop_n)))

        pop = self._spawn_population(pop_n)
        for ind in pop:
            self._evaluate(ind)

        history_best: List[float] = []
        history_mean: List[float] = []
        n_eval = pop_n

        for gen in range(gen_n):
            pop.sort(key=lambda ind: ind.fitness, reverse=True)
            history_best.append(pop[0].fitness)
            history_mean.append(sum(ind.fitness for ind in pop) / len(pop))

            elites = pop[:elite_n]
            next_pop: List[GAIndividual] = list(elites)

            while len(next_pop) < pop_n:
                pa = self.rng.choice(elites).genome
                pb = self.rng.choice(elites).genome
                child_genome = self._crossover(pa, pb)
                if self.rng.random() < 0.5:
                    child_genome = self._mutate(child_genome)
                child = GAIndividual(genome=child_genome)
                self._evaluate(child)
                n_eval += 1
                next_pop.append(child)

            pop = next_pop

        pop.sort(key=lambda ind: ind.fitness, reverse=True)
        return GAResult(
            best=pop[0],
            history_best=history_best,
            history_mean=history_mean,
            n_evaluated=n_eval,
            final_population=pop[:max(10, pop_n)] if pop_n > 0 else [],
        )
