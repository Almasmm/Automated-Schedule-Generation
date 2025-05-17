"""fitness.py – Penalty‑based fitness function for the schedule GA
===================================================================
A *lower* fitness score is *better*.  All penalties are **negative**
values configured in :pydata:`config.GAConfig`.

Each individual chromosome is a list of ``(room_idx, slot_idx)`` tuples
aligned one‑for‑one with the *genes* list.  The GA minimises the sum of
hard‑ and soft‑constraint penalties produced here.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Tuple, Any

import pandas as pd

from config import GAConfig as cfg

###############################################################################
# Helper utilities
###############################################################################

def _extract_year_from_group(group_code: str) -> int:
    """Return student year (1, 2, 3) based on admission year embedded in the
    group code (e.g. ``IT-2205`` → admission 2022 → 2nd‑year if current
    academic year is 2024).  Clamped to *[1, 3]*.
    """
    m = re.search(r"-(\d{2})", group_code)
    if not m:
        return 1  # fallback – treat as first‑year
    admission_yy = int(m.group(1))
    current_yy   = cfg.ACADEMIC_YEAR % 100
    return max(1, min(current_yy - admission_yy + 1, 3))


def _slot_key(day: str, time: str) -> int:
    """Map (day, start_time) → a single sortable integer index."""
    return cfg.DAY_ORDER[day] * 100 + cfg.TIME_ORDER[time]

###############################################################################
# Core fitness function
###############################################################################

def evaluate_schedule(
    individual: List[Tuple[int, int]],
    *,
    genes: List[Dict[str, Any]],
    rooms_df: pd.DataFrame,
    slots_df: pd.DataFrame,
) -> Tuple[float]:
    """Compute total penalty for *one* chromosome.

    Parameters
    ----------
    individual
        GA chromosome – list of ``(room_idx, slot_idx)`` pairs.
    genes
        Canonical gene list built by :pymod:`gene_builder`.
    rooms_df
        DataFrame holding **all** allowed rooms (order must match the list
        passed to GA when building the population).
    slots_df
        DataFrame with timeslot meta‑data (order must match list passed to GA).
    """
    hard_penalty: int = 0
    soft_penalty: int = 0

    # Convenience look‑ups ----------------------------------------------------------------
    room_codes = rooms_df["room_code"].tolist()
    slot_ids   = slots_df["slot_id"].tolist()
    slot_day   = slots_df.set_index("slot_id")["day"].to_dict()
    slot_time  = slots_df.set_index("slot_id")["start"].to_dict()

    # Trackers ---------------------------------------------------------------------------
    used_room:  Dict[str, set] = defaultdict(set)  # slot_id → {room_code}
    used_group: Dict[str, set] = defaultdict(set)  # slot_id → {group_code}
    course_slots: Dict[Tuple[str, str], List[int]] = defaultdict(list)  # (group, course) → slot_idx list
    daily_slots: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))  # group → day → indices

    # --------------------------------------------------------------------- Iterate genes
    for gi, (room_idx, slot_idx) in enumerate(individual):
        gene         = genes[gi]
        group        = gene["group"]
        course       = gene["course_code"]
        course_type  = gene["type"]  # lecture / practice / lab
        room_code    = room_codes[room_idx]
        slot_id      = slot_ids[slot_idx]
        day_name     = slot_day[slot_id]
        time_start   = slot_time[slot_id]

        # ----- HARD: Room / group overlaps -----------------------------------------------
        if room_code in used_room[slot_id]:
            hard_penalty += cfg.WEIGHTS["HARD_CLASH"]
        used_room[slot_id].add(room_code)

        if group in used_group[slot_id]:
            hard_penalty += cfg.WEIGHTS["HARD_CLASH"]
        used_group[slot_id].add(group)

        # ----- HARD: invalid day for year ------------------------------------------------
        year = _extract_year_from_group(group)
        if day_name not in cfg.VALID_DAYS[year]:
            hard_penalty += cfg.WEIGHTS["WRONG_DAY_FOR_YEAR"]

        # ----- SOFT: practice before lecture ---------------------------------------------
        if course_type == "practice":
            course_slots[(group, course)].append(slot_idx)
        elif course_type == "lecture":
            course_slots[(group, course)].append(slot_idx)
        # labs follow same precedence as practice – ignore for now (can extend later)

        # ----- Track for gaps / sequences per group & day --------------------------------
        daily_slots[group][day_name].append(slot_idx)

    # --------------------------------------------------------------------- Post‑processing
    for (group, course), indices in course_slots.items():
        if len(indices) < 2:
            continue  # single session – nothing to compare
        indices.sort()
        # Lecture must be earliest if present
        # Logic: find lecture idx; if any practice slot comes before → penalty
        # (Simplified – assumes at most one lecture gene per course per week)
        lecture_idx = None
        for gi, gene in enumerate(genes):
            if gene["group"] == group and gene["course_code"] == course and gene["type"] == "lecture":
                lecture_idx = individual[gi][1]  # slot idx
                break
        if lecture_idx is not None:
            for idx in indices:
                if idx < lecture_idx:  # happens before lecture
                    soft_penalty += cfg.WEIGHTS["LECTURE_AFTER_PRACTICE"]

        # Non‑consecutive slots penalty ---------------------------------------------------
        for i in range(1, len(indices)):
            if indices[i] - indices[i - 1] != 1:
                soft_penalty += cfg.WEIGHTS["NON_CONSECUTIVE"]

    # Idle gaps per group per day ---------------------------------------------------------
    for group, by_day in daily_slots.items():
        for day_name, idx_list in by_day.items():
            if len(idx_list) < 2:
                continue
            idx_list.sort()
            gaps = (idx_list[-1] - idx_list[0] + 1) - len(idx_list)
            soft_penalty += gaps * cfg.WEIGHTS["IDLE_GAP"]

    total = hard_penalty + soft_penalty
    return (float(total),)