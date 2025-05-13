"""
schedule_ga.py – full working GA (v2.1)
=======================================
* derives `programme_code` and `year` in Groups if missing
* works when Curriculum lacks `course_code` and/or `year`
* prints meaningful warnings when genes = 0
"""
from __future__ import annotations

import argparse, json, random, re, sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from deap import base, creator, tools
from tqdm import trange

DEFAULT_PARAMS = {"pop": 60, "gen": 120, "cx": 0.9, "mut": 0.15}
WEIGHTS = {"HARD_CLASH": -1000, "CAPACITY": -500, "PRECEDENCE": -400, "GAP": -5}
slug = lambda s: re.sub(r"[^A-Za-z0-9]+", "_", str(s)).upper()

# -----------------------------------------------------
# Excel loader


def read_excel(xlsx: Path) -> Dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(xlsx)
    frames: Dict[str, pd.DataFrame] = {}
    static = {"Groups", "Rooms", "Timeslots", "Departments"}
    for st in static:
        frames[st] = pd.read_excel(xl, sheet_name=st)

    course_frames = []
    for name in xl.sheet_names:
        if name in static:
            continue
        df = pd.read_excel(xl, sheet_name=name)
        if "course_name" not in df.columns:
            continue
        df = df.copy()
        if "course_code" not in df.columns:
            df["course_code"] = df["course_name"].apply(slug)
        df["programme_code"] = name
        course_frames.append(df)
    frames["Courses"] = pd.concat(course_frames, ignore_index=True)
    return frames


# -----------------------------------------------------
# Build genes


def build_genes(frames: Dict[str, pd.DataFrame], trimester: int, programme: str | None = None):
    cur = frames["Courses"][frames["Courses"].trimester == trimester].copy()
    if "year" not in cur.columns:
        cur["year"] = ((cur.trimester - 1) // 3 + 1).astype(int)

    groups = frames["Groups"].copy()
    if "programme_code" not in groups.columns:
        groups["programme_code"] = groups["group_code"].astype(str).str.split("-").str[0]
    if "year" not in groups.columns:
        groups["year"] = groups["group_code"].str.extract(r"-(\d)").astype(int)

    if programme:
        cur = cur[cur.programme_code == programme]
        groups = groups[groups.programme_code == programme]

    genes: List[Dict[str, Any]] = []

    lec = cur[cur.lecture_slots > 0]
    for (prog, year, cc), block in lec.groupby(["programme_code", "year", "course_code"], dropna=False):
        gfilter = groups[(groups.programme_code == prog) & (groups.year == year)]
        if gfilter.empty:
            continue
        genes.append({
            "kind": "lecture",
            "course_code": cc,
            "course_name": block.course_name.iloc[0],
            "groups": gfilter.group_code.tolist(),
            "size": int(gfilter.headcount.sum() if "headcount" in gfilter.columns else 25 * len(gfilter)),
            "slots_needed": int(block.lecture_slots.iloc[0]),
        })

    def _sess(col: str, kind: str):
        part = cur[cur[col] > 0]
        merged = part.merge(groups, on=["programme_code", "year"], suffixes=("", "_g"))
        for _, row in merged.iterrows():
            genes.append({
                "kind": kind,
                "course_code": row.course_code,
                "course_name": row.course_name,
                "groups": [row.group_code],
                "size": int(row.headcount) if "headcount" in row else 25,
                "slots_needed": int(row[col]),
            })

    _sess("practice_slots", "practice")
    _sess("lab_slots", "lab")
    return genes


# -----------------------------------------------------
creator.create("Fitness", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.Fitness)


def make_toolbox(genes, rooms, slots):
    r_idx = rooms.index.to_list(); s_idx = list(range(len(slots)))
    sid_map = {i: slots[i] for i in s_idx}; rid_map = {i: rooms.iloc[i].room_code for i in r_idx}

    def random_ind():
        return creator.Individual([(random.choice(r_idx), random.choice(s_idx)) for _ in genes])

    tb = base.Toolbox()
    tb.register("individual", random_ind)
    tb.register("population", tools.initRepeat, list, tb.individual)

    def eval_ind(ind):
        hard = soft = 0; used_room = {}; used_group = {}
        for gi, (ri, si) in enumerate(ind):
            g = genes[gi]; slot = sid_map[si]; room = rid_map[ri]
            if (slot, room) in used_room: hard += WEIGHTS["HARD_CLASH"]
            used_room[(slot, room)] = True
            for gr in g["groups"]:
                if (slot, gr) in used_group: hard += WEIGHTS["HARD_CLASH"]
                used_group[(slot, gr)] = True
            cap = rooms.iloc[ri].capacity
            if g["size"] > cap:
                hard += WEIGHTS["CAPACITY"] * ((g["size"] - cap) // 5 + 1)
        return (hard + soft,)

    tb.register("evaluate", eval_ind)
    tb.register("mate", tools.cxTwoPoint)

    def mutate(ind):
        gi = random.randrange(len(ind)); ri, si = ind[gi]
        if random.random() < 0.5: ri = random.choice(r_idx)
        else: si = random.choice(s_idx)
        ind[gi] = (ri, si); return ind,

    tb.register("mutate", mutate)
    tb.register("select", tools.selTournament, tournsize=3)
    return tb, sid_map, rid_map


# -----------------------------------------------------
# CLI & main


def parse_args():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate"); v.add_argument("--xlsx", required=True, type=Path)

    r = sub.add_parser("run"); r.add_argument("--xlsx", required=True, type=Path)
    r.add_argument("--trimester", required=True, type=int)
    r.add_argument("--programme"); r.add_argument("--pop", type=int, default=DEFAULT_PARAMS["pop"])
    r.add_argument("--gen", type=int, default=DEFAULT_PARAMS["gen"])
    r.add_argument("--seed", type=int)
    r.add_argument("--weights-file", type=Path)
    return p.parse_args()


def validate(frames):
    print("Courses:", len(frames["Courses"]))
    print("Groups :", len(frames["Groups"]))
    print("Rooms  :", len(frames["Rooms"]))
    print("Times  :", len(frames["Timeslots"]))
    print("✔ Validation finished. If numbers look right – proceed.")


def run(frames, tri, prog, args):
    genes = build_genes(frames, tri, prog)
    if not genes:
        print(f"⚠ No sessions found for trimester {tri} (programme={prog or 'ALL'}).")
        return
    print(f"Generating timetable: trimester {tri}, genes={len(genes)} …")

    # slot pool: все слоты из Timeslots без фильтра, простота
    slots = frames["Timeslots"].slot_id.tolist()
    rooms = frames["Rooms"][frames["Rooms"].available == True].reset_index(drop=True)

    tb, sid_map, rid_map = make_toolbox(genes, rooms, slots)

    pop = tb.population(n=args.pop)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values[0])
    stats.register("best", np.min)

    for _ in trange(args.gen, desc="GA"):
        offspring = tools.selTournament(pop, len(pop), 3)
        offspring = list(map(tb.clone, offspring))
        for c1, c2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < DEFAULT_PARAMS["cx"]:
                tb.mate(c1, c2)
        for mut in offspring:
            if random.random() < DEFAULT_PARAMS["mut"]:
                tb.mutate(mut)
            del mut.fitness.values
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid:
            ind.fitness.values = tb.evaluate(ind)
        pop[:] = offspring
        hof.update(pop)

    best = hof[0]
    sched = []
    for gi, (ri, si) in enumerate(best):
        g = genes[gi]
        sched.append({
            "group": ",".join(g["groups"]),
            "course": g["course_name"],
            "type": g["kind"],
            "room": rid_map[ri],
            "slot": sid_map[si],
        })
    out_json = Path(f"timetable_T{tri}.json")
    json.dump(sched, out_json.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Saved", out_json)

    # also Excel
    pd.DataFrame(sched).to_excel(f"timetable_T{tri}.xlsx", index=False)


# -----------------------------------------------------
if __name__ == "__main__":
    # --- parse CLI ---
    args = parse_args()

    # --- RNG seed ---
    seed_val = getattr(args, "seed", None)
    if seed_val is not None:
        random.seed(seed_val)
        np.random.seed(seed_val)


    # --- load Excel once ---
    frames = read_excel(args.xlsx)

    # --- branch ---
    if args.cmd == "validate":
        validate(frames)
    else:                       # cmd == run
        run(frames, args.trimester, args.programme, args)

