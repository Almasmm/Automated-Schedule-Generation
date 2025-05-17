"""logger.py – Simple run/fitness tracking helpers
==================================================
Two conveniences for experiments & web‑UI:

* :func:`log_fitness_curve`  ➜ CSV with best penalty per generation.
* :func:`log_run_metadata`   ➜ JSON side‑car with GA hyper‑parameters,
                              gene count, final score, timestamp …

Both files go to an *outputs/* folder alongside other artefacts (Excel &
JSON timetables).
"""
from __future__ import annotations

import json
import datetime as _dt
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd

# ---------------------------------------------------------------------------
#  Public helpers
# ---------------------------------------------------------------------------

def log_fitness_curve(
    fitness_history: Sequence[float],
    trimester: int,
    outdir: str | Path = "outputs",
) -> Path:
    """Save best‑of‑generation penalties to *CSV* and return its path."""
    out_path = Path(outdir) / f"fitness_T{trimester}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame({
        "generation": range(len(fitness_history)),
        "fitness": list(fitness_history),
    })
    df.to_csv(out_path, index=False)
    print(f"📈  Fitness curve ➜ {out_path.relative_to(Path.cwd())}")
    return out_path


def log_run_metadata(
    *,
    trimester: int,
    pop: int,
    gen: int,
    mutation: float,
    crossover: float,
    seed: int | None,
    genes_count: int,
    final_fitness: float,
    extra: Mapping[str, int | float | str] | None = None,
    outdir: str | Path = "outputs",
) -> Path:
    """Persist a JSON side‑car summarising the GA run."""
    meta: dict[str, int | float | str] = {
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        "academic_trimester": trimester,
        "population": pop,
        "generations": gen,
        "mutation_rate": mutation,
        "crossover_rate": crossover,
        "seed": seed or "default",
        "genes_scheduled": genes_count,
        "best_fitness": final_fitness,
    }
    if extra:
        meta.update(extra)

    out_path = Path(outdir) / f"run_log_T{trimester}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"📝  Run metadata   ➜ {out_path.relative_to(Path.cwd())}")
    return out_path


__all__ = [
    "log_fitness_curve",
    "log_run_metadata",
]
