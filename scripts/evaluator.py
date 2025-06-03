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
        key_time = (g.day, g.time)
        key_room = (g.room, g.day, g.time)
        key_group = (g.group, g.day, g.time)

        group_schedule[key_group].append(g)
        group_day_slots[g.group][g.day].append(g.time)

        # Determine year and allowed days/slots
        year = int(g.group.split("-")[1][:2])
        admission_year = 2000 + year
        study_year = 2024 - admission_year
        allowed_days = GROUP_YEAR_DAYS.get(study_year, [])
        allowed_slots = FIRST_YEAR_TIMESLOTS if study_year == 1 else UPPER_YEAR_TIMESLOTS

        # Online lectures: only 18:00 or 19:00 are valid times
        if getattr(g, "delivery_mode", "offline") == "online" and g.type.lower() == "lecture":
            if g.time not in ["18:00", "19:00"]:
                hard_penalty += 1000
        else:
            if g.day not in allowed_days:
                hard_penalty += 100
            if g.time not in allowed_slots:
                hard_penalty += 100

        # Only add offline classes to room schedule for room conflict checks
        if getattr(g, "delivery_mode", "offline") != "online":
            room_schedule[key_room].append(g)

    # HARD CONSTRAINTS: Room conflicts (offline only, with special handling for PE/Gym and joint lectures)
    for key, val in room_schedule.items():
        room, day, time = key

        # Skip PE in gym conflicts
        if all(("physical education" in g.course.lower() or g.course.strip().upper() == "PE") and g.room.strip().lower() == "gym" for g in val):
            continue

        all_lectures = all(g.type.lower() == "lecture" for g in val)

        joint_keys = set()
        for g in val:
            ep = g.group.split("-")[0].upper()
            year_num = int(g.group.split("-")[1][:2])
            admission_year = 2000 + year_num
            study_year = 2024 - admission_year
            joint_keys.add((g.course, g.type, ep, study_year))

        # Allow joint lectures for same course if <= 5
        if all_lectures and len(joint_keys) == 1:
            if len(val) > 5:
                hard_penalty += 1000 * (len(val) - 5)
        else:
            if len(val) > 1:
                hard_penalty += 1000 * (len(val) - 1)

    # HARD: Group conflicts (online and offline)
    for val in group_schedule.values():
        if len(val) > 1:
            hard_penalty += 1000 * (len(val) - 1)

    # SOFT: Practice before lecture (by course)
    seen_lectures = set()
    seen_practices = set()
    for g in genes:
        tag = (g.group, g.course)
        if g.type.lower() == "lecture":
            seen_lectures.add(tag)
        elif g.type.lower() == "practice" and tag not in seen_lectures:
            soft_penalty += 10

    # SOFT: Gaps in group schedule per day
    for group, days in group_day_slots.items():
        for day, times in days.items():
            times_sorted = sorted(times)
            gaps = 0
            for i in range(1, len(times_sorted)):
                prev = int(times_sorted[i - 1][:2])
                curr = int(times_sorted[i][:2])
                if curr - prev > 1:
                    gaps += curr - prev - 1
            soft_penalty += gaps * 100

    return hard_penalty + soft_penalty
