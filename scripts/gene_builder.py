"""gene_builder.py – Translate curriculum & group tables into *genes*
====================================================================
Each **gene** represents *one* 50‑minute session (lecture / practice /
lab) that must be placed somewhere in the timetable.

Why a 1‑hour granularity?
-------------------------
* It simplifies crossover/mutation: every list index == exactly one
  slot‑room assignment.
* We can still favour consecutive placement via a soft penalty,
  but the GA is free to separate hours if no feasible adjacent slots
  remain.

Public API
----------
* :func:`build_genes` → ``List[dict]`` ready for GA consumption.

Assumptions
~~~~~~~~~~~
* **Groups sheet** must have at least ``group_code`` & ``programme_code``.
* **Curriculum sheets** must contain:
  - ``programme_code`` (added by loader)
  - ``course_code`` / ``course_name``
  - ``trimester`` *(absolute 1–9)*
  - columns ``lecture_hours``, ``practice_hours``, ``lab_hours`` (ints)
* Hours represent *weekly* contact hours → exactly how many genes we
  create per course.

If a curriculum row is entirely zeros for all three hour columns, it is
ignored.
"""
from __future__ import annotations

import re
from typing import List, Dict, Any

import pandas as pd

import config as cfg

from config import CONFIG

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

COLUMN_ALIASES = {
    #  ⟵ ORIGINAL → STANDARD NAME EXPECTED BY CODE
    "lecture":        "lecture_hours",
    "lec_hours":      "lecture_hours",
    "practice":       "practice_hours",
    "prac_hours":     "practice_hours",
    "lab":            "lab_hours",
    "laboratory":     "lab_hours",
    "laboratory_hours":"lab_hours",
}

def extract_year_from_group(group_code: str) -> int:
    """Return **1, 2, 3** based on two‑digit admission year inside group code.

    Example
    -------
    >>> extract_year_from_group("IT-2205")
    2  # if ACADEMIC_YEAR == 2024 (22 → 2022 intake)
    """
    match = re.search(r"-(\d{2})", group_code)
    if not match:
        raise ValueError(f"Group code '{group_code}' does not contain YY part")

    admission_year = 2000 + int(match.group(1))  # crude but fine until 2099
    current_year = CONFIG.academic_year
    year = (current_year % 100) - admission_year + 1    
    return max(1, min(year, 3))


def academic_trimester(abs_trimester: int) -> int:
    """Convert *absolute* 1‑9 → *academic* 1/2/3."""
    return 3 if abs_trimester % 3 == 0 else abs_trimester % 3


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_genes(
    groups_df: pd.DataFrame,
    courses_df: pd.DataFrame,
    trimester: int,
) -> List[Dict[str, Any]]:
    """Yield one gene‑dict per 50‑minute session.

    Parameters
    ----------
    groups_df : DataFrame
        Must contain *group_code* and *programme_code* columns.
    courses_df : DataFrame
        All curriculum rows across EPs.
    trimester : int {1,2,3}
        Academic trimester of *current* year.
    """

    if trimester not in (1, 2, 3):
        raise ValueError("trimester must be 1, 2, or 3 (academic, not absolute)")

    genes: list[dict[str, Any]] = []

    # Pre‑compute academic trimester for every curriculum row once
    courses_df = courses_df.copy()
    
    courses_df.rename(columns=COLUMN_ALIASES, inplace=True)

    courses_df["acad_tri"] = courses_df["trimester"].apply(academic_trimester)

    # ------------------------------------------------------------------
    # Iterate all groups – include 1st, 2nd, 3rd year indiscriminately
    # ------------------------------------------------------------------
    for _idx, g_row in groups_df.iterrows():
        group_code: str = g_row["group_code"]
        if "programme_code" in g_row:
            programme_code = g_row["programme_code"]
        else:
            programme_code = g_row["group_code"].split("-")[0].upper()
            
        year: int = extract_year_from_group(group_code)

        # Pull courses for this EP *and* academic trimester
        filt = (
            (courses_df["programme_code"] == programme_code) &
            (courses_df["acad_tri"] == trimester)
        )
        cur_courses = courses_df.loc[filt]

        for _cidx, c_row in cur_courses.iterrows():
            for kind in ("lecture", "practice", "lab"):
                hours_col = f"{kind}_hours"
                if hours_col not in c_row or pd.isna(c_row[hours_col]):
                    continue
                slots_needed = int(c_row[hours_col])
                if slots_needed <= 0:
                    continue

                for _ in range(slots_needed):
                    genes.append(
                        {
                            "group": group_code,
                            "year": year,
                            "programme": programme_code,
                            "course_code": c_row.get("course_code") or c_row["course_name"],
                            "course_name": c_row["course_name"],
                            "type": kind,   # 'lecture' | 'practice' | 'lab'
                            # room / slot indices are assigned later by the GA
                        }
                    )
    if not genes:
        print("DEBUG — curriculum rows per EP / acad_tri:")
        print(courses_df.groupby(['programme_code','acad_tri']).size())

    return genes


# ---------------------------------------------------------------------------
# Quick sanity CLI (run as module)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, pathlib
    from loader import load_input_excel  # type: ignore  # local util

    ap = argparse.ArgumentParser("gene‑builder quick check")
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--tri", type=int, choices=[1, 2, 3], required=True)
    ns = ap.parse_args()

    groups_df, rooms_df, slots_df, courses_df = load_input_excel(ns.xlsx)
    gs = build_genes(groups_df, courses_df, ns.tri)
    print(f"Built {len(gs)} genes for trimester {ns.tri}.")