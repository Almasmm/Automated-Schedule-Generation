"""ga_solver.py – Core GA engine for AITU timetable generation
=============================================================
This module wires together
    *   the **genes** produced by :pymod:`gene_builder`,
    *   the **penalty function** in :pymod:`fitness`, and
    *   the hyper‑parameters stored in :pydata:`config.CONFIG`.

It uses the `DEAP` (Distributed Evolutionary Algorithms in Python)
framework to perform a classic μ + λ GA with:

    • one‑point crossover on the chromosome list,                   
    • per‑gene random mutation (change room and/or timeslot),       
    • k‑way tournament selection (k configurable in CONFIG),        
    • optional early stopping when the best solution has plateaued.

Public API
----------
::

    best_df, fitness_history = run_ga(
        genes, rooms_df, slots_df,
        population=75, generations=300, seed=42,
    )

where ``best_df`` is a tidy **pandas.DataFrame** ready for Excel/JSON
export and ``fitness_history`` is a list[float] of the best penalty per
generation (lower is better).
"""
from __future__ import annotations

import random
from collections import deque
from pathlib import Path
from typing import List, Tuple, Dict, Any, Sequence

import numpy as np
import pandas as pd
from deap import base, creator, tools

import config as cfg
from fitness import evaluate_schedule

# ---------------------------------------------------------------------------
#  Helpers – random generation, mutation, crossover
# ---------------------------------------------------------------------------

def _random_assignment(n_rooms: int, n_slots: int) -> Tuple[int, int]:
    """Return ``(room_idx, slot_idx)`` chosen uniformly at random."""
    return random.randrange(n_rooms), random.randrange(n_slots)


def _mutate_assignment(value: Tuple[int, int], n_rooms: int, n_slots: int) -> Tuple[int, int]:
    """With 50 % chance change room, otherwise change timeslot."""
    room_idx, slot_idx = value
    if random.random() < 0.5:
        room_idx = random.randrange(n_rooms)
    else:
        slot_idx = random.randrange(n_slots)
    return room_idx, slot_idx


# ---------------------------------------------------------------------------
#  Main GA entry point
# ---------------------------------------------------------------------------

def run_ga(
    genes: List[Dict[str, Any]],
    rooms_df: pd.DataFrame,
    slots_df: pd.DataFrame,
    *,
    population: int | None = None,
    generations: int | None = None,
    seed: int | None = None,
) -> Tuple[pd.DataFrame, List[float]]:
    """Evolve a complete schedule.

    Parameters
    ----------
    genes
        Canonical gene list – *order matters* and must stay fixed.
    rooms_df / slots_df
        Metadata tables.  **Order** of rows == index used by chromosome.
    population / generations / seed
        Optional overrides; fall back to :pydata:`config.CONFIG` values.

    Returns
    -------
    tuple (best_schedule_df, fitness_history)
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    cfg_obj = cfg.CONFIG
    pop_size = population or cfg_obj.population
    n_gen    = generations or cfg_obj.generations

    n_rooms = len(rooms_df)
    n_slots = len(slots_df)

    # ------------------------- DEAP primitives ----------------------------
    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMin)

    toolbox = base.Toolbox()

    toolbox.register("_rand_gene", _random_assignment, n_rooms, n_slots)
    toolbox.register(
        "individual",
        tools.initRepeat,
        creator.Individual,
        toolbox._rand_gene,  # type: ignore[arg-type]
        n=len(genes),
    )
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Evaluation -----------------------------------------------------------
    toolbox.register(
        "evaluate",
        evaluate_schedule,
        genes=genes,
        rooms_df=rooms_df,
        slots_df=slots_df,
    )

    # Genetic operators ----------------------------------------------------
    toolbox.register("mate", tools.cxOnePoint)

    def _mutate(individual: creator.Individual) -> Tuple[creator.Individual]:
        for idx in range(len(individual)):
            if random.random() < cfg_obj.mutation_rate:
                individual[idx] = _mutate_assignment(individual[idx], n_rooms, n_slots)
        return (individual,)

    toolbox.register("mutate", _mutate)
    toolbox.register("select", tools.selTournament, tournsize=cfg_obj.tournament_k)

    # ------------------------------ Run GA -------------------------------
    pop = toolbox.population(n=pop_size)
    fitness_history: List[float] = []
    no_improve_counter: int = 0
    best_so_far: float | None = None

    # Evaluate initial population
    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)

    for gen in range(n_gen):
        # Selection ➔ offspring
        offspring = toolbox.select(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))

        # Apply crossover and mutation
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < cfg_obj.crossover_rate:
                toolbox.mate(child1, child2)
                del child1.fitness.values, child2.fitness.values

        for mutant in offspring:
            toolbox.mutate(mutant)
            del mutant.fitness.values

        # Re‑evaluate only invalidated individuals
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid:
            ind.fitness.values = toolbox.evaluate(ind)

        pop[:] = offspring

        # Track best
        gen_best = min(pop, key=lambda ind: ind.fitness.values[0])
        gen_best_score = gen_best.fitness.values[0]
        fitness_history.append(gen_best_score)

        if best_so_far is None or gen_best_score < best_so_far:
            best_so_far = gen_best_score
            no_improve_counter = 0
            hall_of_fame = gen_best  # shallow copy is fine – we won't mutate it
        else:
            no_improve_counter += 1

        if cfg_obj.early_stop and no_improve_counter >= cfg_obj.early_stop:
            print(f"🛑 Early stop: no progress for {cfg_obj.early_stop} generations.")
            break

    # ----------------------- Build tidy schedule DF -----------------------
    best_ind = hall_of_fame  # type: ignore[has-type]

    rows: List[Dict[str, Any]] = []
    slot_id_list: Sequence[Any] = slots_df["slot_id"].tolist()
    for gi, (room_idx, slot_idx) in enumerate(best_ind):
        gene = genes[gi]
        slot_row = slots_df.iloc[slot_idx]
        room_row = rooms_df.iloc[room_idx]

        rows.append(
            {
                "group": gene["group"],
                "year": gene["year"],
                "programme": gene["programme"],
                "day": slot_row["day"],
                "time": f"{slot_row['start']}-{slot_row['end']}",
                "course": gene["course_name"],
                "type": gene["type"].capitalize(),
                "room": room_row["room_code"],
            }
        )

    best_df = pd.DataFrame(rows).sort_values(["group", "day", "time"]).reset_index(drop=True)
    return best_df, fitness_history


# ---------------------------------------------------------------------------
#  CLI helper (for ad‑hoc experiments) --------------------------------------
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    from loader import load_input_excel  # local util provided elsewhere

    ap = argparse.ArgumentParser("GA solver quick run")
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--tri", type=int, choices=[1, 2, 3], required=True)
    ap.add_argument("--pop", type=int, default=cfg.CONFIG.population)
    ap.add_argument("--gen", type=int, default=cfg.CONFIG.generations)
    ns = ap.parse_args()

    groups_df, rooms_df, slots_df, courses_df = load_input_excel(ns.xlsx)
    from gene_builder import build_genes  # local import to avoid cycles

    genes = build_genes(groups_df, courses_df, ns.tri)
    best, hist = run_ga(
        genes,
        rooms_df,
        slots_df,
        population=ns.pop,
        generations=ns.gen,
    )

    print(best.head())
    print("Best fitness", hist[-1] if hist else "N/A")