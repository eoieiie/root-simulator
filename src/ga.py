"""유전 알고리즘 기반 에어룸 배치 최적화.

GitHub Dream-no24/GwC-Simulation-System ga.py 참조.
Adapted from 3D box pot → 2D r-z 단면.

Genome: [(r0, z0), (r1, z1), ..., (rN, zN)] — N = GAConfig.airroom_count
Fitness: G-Health Score (Pipeline.run)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .config import SimConfig
from .geometry import Airroom

Genome = List[Tuple[float, float]]


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
    ):
        self.cfg = config
        self.ga_cfg = config.ga
        self.fitness_fn = fitness_fn
        self.rng = rng or random.Random(config.seed + 999)

        self.n_airrooms = self.ga_cfg.airroom_count
        self.pot_r = config.pot.radius_cm
        self.pot_h = config.pot.height_cm
        self.airroom_r_min: float = config.airroom.radius_range_cm[0]
        self.airroom_r_max: float = config.airroom.radius_range_cm[1]

    # ── genome ↔ airrooms 변환 ───────────────────────────

    def _genome_to_airrooms(self, genome: Genome) -> List[Airroom]:
        return [
            Airroom(
                r=r,
                z=z,
                radius=self.rng.uniform(self.airroom_r_min, self.airroom_r_max),
                pruning_zone_factor=self.cfg.airroom.pruning_zone_factor,
            )
            for r, z in genome
        ]

    # ── 초기화 ────────────────────────────────────────────

    def _random_genome(self) -> Genome:
        margin = self.airroom_r_max * 2.0
        genome: Genome = []
        for _ in range(self.n_airrooms):
            r = self.rng.uniform(margin, self.pot_r - margin)
            z = self.rng.uniform(margin, self.pot_h - margin)
            genome.append((r, z))
        return genome

    def _spawn_population(self, n: int) -> List[GAIndividual]:
        return [GAIndividual(genome=self._random_genome()) for _ in range(n)]

    # ── 평가 ──────────────────────────────────────────────

    def _evaluate(self, ind: GAIndividual) -> float:
        airrooms = self._genome_to_airrooms(ind.genome)
        ind.airrooms = airrooms
        ind.fitness = self.fitness_fn(airrooms)
        return ind.fitness

    # ── 변이 ──────────────────────────────────────────────

    def _mutate(self, genome: Genome) -> Genome:
        sigma = self.ga_cfg.mutation_sigma_cm
        idx = self.rng.randint(0, len(genome) - 1)
        r, z = genome[idx]
        margin = self.airroom_r_max * 2.0
        r += self.rng.gauss(0, sigma)
        z += self.rng.gauss(0, sigma)
        r = max(margin, min(self.pot_r - margin, r))
        z = max(margin, min(self.pot_h - margin, z))
        new = list(genome)
        new[idx] = (r, z)
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
        )
