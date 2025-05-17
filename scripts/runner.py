"""
runner.py – CLI orchestrator for the AITU timetable GA
=====================================================

Example
-------
    python -m algorithms.runner \
        --xlsx input/GA_Input.xlsx \
        --trimester 3 \
        --pop 100 --gen 250 --seed 42
"""

from __future__ import annotations

from pathlib import Path
import argparse
import sys
import pandas as pd

# Local imports
from config import CONFIG
from gene_builder import build_genes
from ga_solver import run_ga
from logger import log_fitness_curve, log_run_metadata

# --------------------------------------------------------------------------- #
# CLI helpers
# --------------------------------------------------------------------------- #
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate a trimester schedule via Genetic Algorithm.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--xlsx", required=True,
                   help="Path to GA_Input.xlsx (must contain Groups, Rooms, "
                        "Timeslots sheets and curriculum sheets per EP).")
    p.add_argument("--trimester", required=True, type=int, choices=[1, 2, 3],
                   help="Academic trimester of the current year (1, 2 or 3).")
    p.add_argument("--pop", type=int, default=CONFIG.pop_size,
                   help="GA population size.")
    p.add_argument("--gen", type=int, default=CONFIG.generations,
                   help="Number of GA generations.")
    p.add_argument("--seed", type=int, default=CONFIG.seed,
                   help="Random seed for reproducibility.")
    return p


# --------------------------------------------------------------------------- #
# Excel loader (simple, keeps runner.py standalone)
# --------------------------------------------------------------------------- #
def load_input_excel(xlsx_path: str | Path):
    """
    Reads core sheets and curriculum dataframes from the Excel input file.

    Returns
    -------
    groups_df, rooms_df, slots_df, courses_df : pandas.DataFrame
    """
    xl = pd.ExcelFile(xlsx_path)

    # Mandatory sheets
    try:
        groups_df = pd.read_excel(xl, "Groups")
        rooms_df = pd.read_excel(xl, "Rooms")
        slots_df = pd.read_excel(xl, "Timeslots")
    except ValueError as exc:  # sheet missing
        sys.exit(f"❌ Missing required sheet in {xlsx_path}: {exc}")

    # Any sheet that is **not** a core/ignored one is a curriculum sheet
    curriculum_dfs = []
    ignored = {"Groups", "Rooms", "Timeslots", "Departments", "Instructors"}
    for sheet in xl.sheet_names:
        if sheet in ignored:
            continue
        df = pd.read_excel(xl, sheet)
        df["programme_code"] = sheet
        curriculum_dfs.append(df)

    if not curriculum_dfs:
        sys.exit("❌ No curriculum sheets found in the Excel file.")

    courses_df = pd.concat(curriculum_dfs, ignore_index=True)
    return groups_df, rooms_df, slots_df, courses_df


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_input(courses_df: pd.DataFrame, trimester: int) -> None:
    """
    Abort execution if no courses exist for the requested academic trimester.
    """
    # Convert absolute (1-9) → academic (1-3)
    acad_trimester = courses_df["trimester"].mod(3).replace({0: 3})
    if courses_df[acad_trimester == trimester].empty:
        sys.exit(f"❌ No courses found for academic trimester {trimester}.")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None):
    args = _build_arg_parser().parse_args(argv)

    print("📦 Loading input Excel ...")
    groups_df, rooms_df, slots_df, courses_df = load_input_excel(args.xlsx)

    print("🧪 Validating curriculum ...")
    validate_input(courses_df, args.trimester)

    print("🧬 Building genes ...")
    genes = build_genes(groups_df, courses_df, args.trimester)
    if not genes:
        sys.exit("❌ No genes generated (empty curriculum / groups mismatch).")

    print(f"🔁 Running GA  | Genes: {len(genes)} | "
          f"Pop: {args.pop} | Gen: {args.gen} | Seed: {args.seed}")
    best_df, fitness_hist = run_ga(
        genes=genes,
        rooms_df=rooms_df,
        slots_df=slots_df,
        pop_size=args.pop,
        generations=args.gen,
        seed=args.seed,
    )

    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)

    json_path = out_dir / f"timetable_T{args.trimester}.json"
    xlsx_path = out_dir / f"timetable_T{args.trimester}.xlsx"

    print("💾 Saving schedule ...")
    best_df.to_json(json_path, orient="records", force_ascii=False, indent=2)
    best_df.to_excel(xlsx_path, index=False)

    print(f"✅ Schedule saved:\n    → {json_path}\n    → {xlsx_path}")

    # ------------------------------------------------------------------ #
    # Logging extras
    # ------------------------------------------------------------------ #
    if CONFIG.log_fitness:
        log_fitness_curve(fitness_hist, args.trimester)

    if CONFIG.track_run:
        log_run_metadata(
            trimester=args.trimester,
            pop=args.pop,
            gen=args.gen,
            mutation=CONFIG.mutation_rate,
            crossover=CONFIG.crossover_rate,
            seed=args.seed,
            genes_count=len(genes),
            final_fitness=fitness_hist[-1],
        )


# Allow `python -m algorithms.runner ...`
if __name__ == "__main__":
    main()
