"""config.py – Centralised hyper‑parameters & penalty weights
===========================================================
Import this module from *inside* the ``algorithms`` package.  Modify the
constants (or the `GAConfig` dataclass) to tune the GA without touching
other source files.

Key points
----------
* `GAConfig` bundles every tunable knob so downstream code can just
  depend on **one** object (`CONFIG`).
* Both legacy names (`population`, `generations`, …) *and* the shorter
  aliases used by *runner.py* (`pop_size`, `gen`) are provided.
* Hard‑constraint weights must dominate soft‑constraint ones.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

# ---------------------------------------------------------------------------
#  Core GA defaults
# ---------------------------------------------------------------------------
POPULATION_SIZE: int = 50
GENERATIONS: int = 100
CROSSOVER_RATE: float = 0.90
MUTATION_RATE: float = 0.10
TOURNAMENT_SIZE: int = 3
EARLY_STOPPING: int = 20  # 0 → disabled
DEFAULT_SEED: int = 42
ACADEMIC_YEAR: int = 2024

# ---------------------------------------------------------------------------
#  Fitness penalty weights (<< 0 == BAD)
# ---------------------------------------------------------------------------
HARD_WEIGHTS: dict[str, int] = {
    "ROOM_CLASH": -1000,      # two events in same room / slot
    "ENTITY_CLASH": -1000,    # group or instructor double‑booked
    "PRECEDENCE": -400,       # practice before lecture
    "UNSCHEDULED": -1500,     # gene not placed (shouldn’t happen)
}

SOFT_WEIGHTS: dict[str, int] = {
    "IDLE_GAP": -8,           # 1‑hour hole inside a day
    "NON_CONSEC": -5,         # multi‑hour block split over day
}

FITNESS_WEIGHTS: Mapping[str, int] = HARD_WEIGHTS | SOFT_WEIGHTS  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
#  Timetable grid definition
# ---------------------------------------------------------------------------
DAYS: tuple[str, ...] = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
TIMES: tuple[str, ...] = (
    "08:00", "09:00", "10:00", "11:00", "12:00", "13:00",
    "14:00", "15:00", "16:00", "17:00", "18:00", "19:00",
)

# ---------------------------------------------------------------------------
#  Dataclass wrapper
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class GAConfig:
    """All GA hyper‑parameters in one place."""
    academic_year: int = ACADEMIC_YEAR
    # ── Evolution parameters ───────────────────────────────────────────
    population: int = POPULATION_SIZE
    generations: int = GENERATIONS
    crossover_rate: float = CROSSOVER_RATE
    mutation_rate: float = MUTATION_RATE
    tournament_k: int = TOURNAMENT_SIZE
    early_stop: int = EARLY_STOPPING
    seed: int = DEFAULT_SEED

    # ── Fitness penalties ──────────────────────────────────────────────
    hard_weights: Mapping[str, int] = field(default_factory=lambda: HARD_WEIGHTS.copy())
    soft_weights: Mapping[str, int] = field(default_factory=lambda: SOFT_WEIGHTS.copy())

    # -----------------------------------------------------------------
    #  Aliases for legacy / external code
    # -----------------------------------------------------------------
    @property
    def pop_size(self) -> int:  # used by runner.py CLI defaults
        return self.population

    @pop_size.setter
    def pop_size(self, value: int):
        self.population = value

    @property
    def gen(self) -> int:       # rarely used alias
        return self.generations

    # -----------------------------------------------------------------
    #  Helpers
    # -----------------------------------------------------------------
    def penalty(self, key: str) -> int:
        if key in self.hard_weights:
            return self.hard_weights[key]
        if key in self.soft_weights:
            return self.soft_weights[key]
        raise KeyError(key)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "GAConfig":
        """Load overrides from a YAML mapping (optional)."""
        import yaml
        with Path(path).expanduser().open("r", encoding="utf-8") as fh:
            data: dict = yaml.safe_load(fh) or {}
        return cls(**data)

    def as_dict(self) -> dict[str, int | float]:
        return {
            "population": self.population,
            "generations": self.generations,
            "crossover_rate": self.crossover_rate,
            "mutation_rate": self.mutation_rate,
            "tournament_k": self.tournament_k,
            "early_stop": self.early_stop,
            "seed": self.seed,
        }

# Global singleton
CONFIG = GAConfig()

__all__ = [
    "GAConfig",
    "CONFIG",
    "FITNESS_WEIGHTS",
    "DAYS",
    "TIMES",
]
