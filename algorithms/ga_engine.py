"""Building genes and running GA (DEAP)"""

from __future__ import annotations
import random, numpy as np
from collections import defaultdict
from math import ceil
from typing import List, Dict, Any, Tuple
import pandas as pd
from deap import base, tools, algorithms
from model import creator
import config as cfg

# ------------------------------------------------------------------
def build_genes(data, acad_tri: int) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Из curriculum + groups формируем список 'генов' (занятий)."""
    cur = data.curriculum_for_acad_tri(acad_tri)
    genes = []

    # общий словарь size группы
    size_map = data.groups.set_index("group_code")["headcount"].to_dict()

    # ---------- ЛЕКЦИИ: объединяем группы одного курса+года ----------
    key_cols = ["programme_code", "year", "course_code"]
    for _, block in cur[cur.lecture_slots > 0].groupby(key_cols):
        groups = data.groups[
            (data.groups.programme_code == block.programme_code.iloc[0])
            & (data.groups.year == block.year.iloc[0])
        ].group_code.tolist()
        genes.append(
            dict(kind="lecture",
                 course=block.course_name.iloc[0],
                 course_code=block.course_code.iloc[0],
                 groups=groups,
                 size=int(sum(size_map[g] for g in groups)),
                 slots=int(block.lecture_slots.iloc[0]))
        )

    # ---------- Практики и лаборатории -------------------------------
    def per_group(col, kind):
        sub = cur[cur[col] > 0]
        for _, row in sub.iterrows():
            gfilter = data.groups[
                (data.groups.programme_code == row.programme_code)
                & (data.groups.year == row.year)
            ]
            for g in gfilter.group_code:
                genes.append(
                    dict(kind=kind,
                         course=row.course_name,
                         course_code=row.course_code,
                         groups=[g],
                         size=int(size_map[g]),
                         slots=int(row[col]))
                )
    per_group("practice_slots", "practice")
    per_group("lab_slots", "lab")

    # пул всех slot_id (без Чт для 3-го курса, без Сб для 2-го)
    slot_pool = []
    for yr in (1, 2, 3):
        disallowed = {"Thu"} if yr == 3 else {"Sat"} if yr == 2 else set()
        slots = data.times[~data.times.day.isin(disallowed)].slot_id.tolist()
        slot_pool.extend(slots)
    return genes, slot_pool

# ------------------------------------------------------------------
def run_ga(data, acad_tri: int, pop: int, gen: int, seed: int):
    """Запуск GA и возврат DataFrame расписания."""
    random.seed(seed)
    np.random.seed(seed)

    genes, slot_pool = build_genes(data, acad_tri)
    rooms = data.rooms[data.rooms.available == True].reset_index(drop=True)

    print(f"Genes to schedule: {len(genes)}")

    # ---------- кодируем индивидуум ----------------------------------
    ROOM_IDX = list(range(len(rooms)))
    SLOT_IDX = list(range(len(slot_pool)))

    def random_assignment():
        return [(random.choice(ROOM_IDX), random.choice(SLOT_IDX)) for _ in genes]

    tb = base.Toolbox()
    tb.register("individual", tools.initIterate, creator.Individual, random_assignment)
    tb.register("population", tools.initRepeat, list, tb.individual)
    tb.register("mate", tools.cxTwoPoint)

    # ---- мутация: поменять комнату или слот -------------------------
    def mutate(ind):
        idx = random.randrange(len(ind))
        room, slot = ind[idx]
        if random.random() < 0.5:
            room = random.choice(ROOM_IDX)
        else:
            slot = random.choice(SLOT_IDX)
        ind[idx] = (room, slot)
        return ind,

    tb.register("mutate", mutate)
    tb.register("select", tools.selTournament, tournsize=3)

    # ---------- fitness ---------------------------------------------
        # ---------- fitness ---------------------------------------------
    def evaluate(ind):
        hard = soft = 0
        used_room = defaultdict(set)   # slot → {room}
        used_group = defaultdict(set)  # slot → {group}

        # --- проходим все гены --------------------------------------
        for gi, (r_idx, s_idx) in enumerate(ind):
            gene = genes[gi]
            slot_id = slot_pool[s_idx]
            room = rooms.iloc[r_idx]

            # room clash
            if room.room_code in used_room[slot_id]:
                hard += cfg.WEIGHTS["HARD_CLASH"]
            used_room[slot_id].add(room.room_code)

            # group clash
            for g in gene["groups"]:
                if g in used_group[slot_id]:
                    hard += cfg.WEIGHTS["HARD_CLASH"]
                used_group[slot_id].add(g)

            # capacity
            if gene["size"] > room.capacity:
                hard += cfg.WEIGHTS["CAPACITY_OVER"]

        # --- idle gap per group  ------------------------------------
        # преобразуем used_group → словарь group → [slot_index, ...]
        group_slots = defaultdict(list)
        slot_index_of = {sid: i for i, sid in enumerate(slot_pool)}
        for sid, gs in used_group.items():
            for g in gs:
                group_slots[g].append(slot_index_of[sid])

        for idxs in group_slots.values():
            if len(idxs) > 1:
                holes = (max(idxs) - min(idxs) + 1) - len(idxs)
                soft += holes * cfg.WEIGHTS["IDLE_GAP"]

        return hard + soft,


    tb.register("evaluate", evaluate)

    # ---------- запускаем GA ----------------------------------------
    popu = tb.population(n=pop)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("best", np.min)

    algorithms.eaSimple(                   
         popu, tb,
         cxpb=cfg.CROSSOVER_RATE,
         mutpb=cfg.MUTATION_RATE,
         ngen=gen,
         halloffame=hof,
         stats=stats,
         verbose=True
     )

    # ---------- упаковываем результат -------------------------------
    best = hof[0]
    rows = []
    for gi, (r_idx, s_idx) in enumerate(best):
        gene = genes[gi]
        slot_row = data.times.set_index("slot_id").loc[slot_pool[s_idx]]
        rows.append(dict(
            group=",".join(gene["groups"]),
            day=slot_row.day,
            time=f"{slot_row.start}-{slot_row.end}",
            course=gene["course"],
            room=rooms.iloc[r_idx].room_code,
            type=gene["kind"].capitalize()
        ))
    return pd.DataFrame(rows)
