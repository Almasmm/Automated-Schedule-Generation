# ga_engine.py --------------------------------------------------------

"""DEAP based GA that schedules all groups for a trimester."""
from __future__ import annotations
from typing import List, Dict
import random, numpy as np
from deap import base, creator, tools
from model import Gene
import pandas as pd

creator.create("Fitness", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.Fitness)

MON_TO_SAT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

def build_genes(data, cur_df):
    genes: List[Gene] = []
    groups = data.groups
    # lecture streams
    lec = cur_df[cur_df.lecture_slots > 0]
    for (_, yr, cc), block in lec.groupby(["programme_code", "year", "course_code"]):
        relevant_groups = groups[(groups.programme_code == block.programme_code.iloc[0]) & (groups.year == yr)]
        size = relevant_groups.headcount.sum()
        genes.append(Gene(relevant_groups.group_code.tolist(), cc, block.course_name.iloc[0], "lecture", size, int(block.lecture_slots.iloc[0])))
    # practice / lab per group
    for _, row in cur_df.iterrows():
        gfilter = groups[(groups.programme_code == row.programme_code) & (groups.year == row.year)]
        for _, g in gfilter.iterrows():
            if row.practice_slots:
                genes.append(Gene([g.group_code], row.course_code, row.course_name, "practice", g.headcount, int(row.practice_slots)))
            if row.lab_slots:
                genes.append(Gene([g.group_code], row.course_code, row.course_name, "lab", g.headcount, int(row.lab_slots)))
    return genes

def run_ga(data, trimester, pop=60, gen=120, seed=1):
    random.seed(seed); np.random.seed(seed)
    cur = data.curriculum_for_trimester(trimester)
    genes = build_genes(data, cur)
    if not genes:
        print("No sessions to schedule for this trimester")
        return []

    rooms = data.rooms[data.rooms.available == True].reset_index(drop=True)
    slot_ids = data.times.slot_id.tolist()

    R = list(range(len(rooms)))
    S = list(range(len(slot_ids)))

    def make_ind():
        return creator.Individual([(random.choice(R), random.choice(S)) for _ in genes])

    tb = base.Toolbox()
    tb.register("individual", make_ind)
    tb.register("population", tools.initRepeat, list, tb.individual)

    def fitness(ind):
        hard = 0
        used_room = {s: set() for s in S}
        used_group = {s: set() for s in S}
        for i, (r_idx, s_idx) in enumerate(ind):
            g = genes[i]
            # clashes
            if r_idx in used_room[s_idx]:
                hard += 1000
            else:
                used_room[s_idx].add(r_idx)
            for gc in g.group_codes:
                if gc in used_group[s_idx]:
                    hard += 1000
                else:
                    used_group[s_idx].add(gc)
            # capacity
            if g.size > rooms.capacity.iloc[r_idx]:
                hard += 200 * ((g.size - rooms.capacity.iloc[r_idx]) // 5 + 1)
        return (-hard,),

    tb.register("evaluate", fitness)
    tb.register("mate", tools.cxTwoPoint)
    tb.register("mutate", lambda ind: (swap_mut(ind, R, S),))
    tb.register("select", tools.selTournament, tournsize=3)

    def swap_mut(ind, R, S):
        idx = random.randrange(len(ind))
        r, s = ind[idx]
        if random.random() < 0.5:
            r = random.choice(R)
        else:
            s = random.choice(S)
        ind[idx] = (r, s)
        return ind

    popu = tb.population(n=pop)
    popu, _ = tools.eaSimple(popu, tb, 0.9, 0.15, gen, verbose=False)
    best = tools.selBest(popu, 1)[0]

    # materialise schedule rows
    schedule = []
    for i, (r_idx, s_idx) in enumerate(best):
        g = genes[i]
        schedule.append({
            "group": ",".join(g.group_codes),
            "course": g.course_name,
            "type": g.session_type,
            "slot": slot_ids[s_idx],
            "room": rooms.room_code.iloc[r_idx]
        })
    return schedule