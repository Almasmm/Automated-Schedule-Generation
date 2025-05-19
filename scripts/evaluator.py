# scripts/evaluator.py

from collections import defaultdict
from scripts.config import GROUP_YEAR_DAYS, FIRST_YEAR_TIMESLOTS, UPPER_YEAR_TIMESLOTS

def evaluate_fitness(genes):
    hard_penalty = 0
    soft_penalty = 0

    group_schedule = defaultdict(list)
    room_schedule = defaultdict(list)
    group_day_slots = defaultdict(lambda: defaultdict(list))

    for g in genes:
        if ("Physical Education" in g.course or "PE" in g.course) and g.room.strip().lower() != "gym":
            hard_penalty += 1000  # Must be in Gym
        
        key_time = (g.day, g.time)
        key_room = (g.room, g.day, g.time)
        key_group = (g.group, g.day, g.time)

        # Collect for clash detection
        room_schedule[key_room].append(g)
        group_schedule[key_group].append(g)
        group_day_slots[g.group][g.day].append(g.time)

        # Check time range constraints
        year = int(g.group.split("-")[1][:2])
        admission_year = 2000 + year
        study_year = 2024 - admission_year 
        allowed_days = GROUP_YEAR_DAYS.get(study_year, [])
        allowed_slots = FIRST_YEAR_TIMESLOTS if study_year == 1 else UPPER_YEAR_TIMESLOTS

        if g.day not in allowed_days:
            hard_penalty += 100
        if g.time not in allowed_slots:
            hard_penalty += 100

    # HARD CONSTRAINTS
    for val in room_schedule.values():
        if len(val) > 1:
            hard_penalty += 1000 * (len(val) - 1)  # Room conflict

    for val in group_schedule.values():
        if len(val) > 1:
            hard_penalty += 1000 * (len(val) - 1)  # Group conflict

    # PRACTICE BEFORE LECTURE (by course)
    seen_lectures = set()
    seen_practices = set()
    for g in genes:
        tag = (g.group, g.course)
        if g.type.lower() == "lecture":
            seen_lectures.add(tag)
        elif g.type.lower() == "practice" and tag not in seen_lectures:
            soft_penalty += 10  # allow it but penalize if lecture not seen yet

    # SOFT CONSTRAINTS
    for group, days in group_day_slots.items():
        for day, times in days.items():
            times_sorted = sorted(times)
            gaps = 0
            for i in range(1, len(times_sorted)):
                prev = int(times_sorted[i - 1][:2])
                curr = int(times_sorted[i][:2])
                if curr - prev > 1:
                    gaps += curr - prev - 1
            soft_penalty += gaps * 100  # each idle gap is slightly penalized

    # Total fitness
    return hard_penalty + soft_penalty
