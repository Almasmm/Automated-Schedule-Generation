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

        # --- Time range and slot validation ---
        year = int(g.group.split("-")[1][:2])
        admission_year = 2000 + year
        study_year = 2024 - admission_year
        allowed_days = GROUP_YEAR_DAYS.get(study_year, [])
        allowed_slots = FIRST_YEAR_TIMESLOTS if study_year == 1 else UPPER_YEAR_TIMESLOTS

        # Online lecture can only be at 18:00, 19:00, or 20:00
        if getattr(g, "delivery_mode", "offline") == "online" and g.type.lower() == "lecture":
            if g.time not in ["18:00", "19:00", "20:00"]:
                hard_penalty += 1000
        else:
            if g.day not in allowed_days:
                hard_penalty += 100
            if g.time not in allowed_slots:
                hard_penalty += 100

        # Only add offline to room_schedule (room conflicts)
        if getattr(g, "delivery_mode", "offline") != "online":
            room_schedule[key_room].append(g)

    # --- ROOM CONFLICTS: ignore online, check offline as before ---
    for key, val in room_schedule.items():
        room, day, time = key

        # Gym (PE) is exempt from conflicts
        if all(
            ("physical education" in g.course.lower() or g.course.strip().upper() == "PE")
            and g.room.strip().lower() == "gym"
            for g in val
        ):
            continue

        all_lectures = all(g.type.lower() == "lecture" for g in val)
        joint_keys = set()
        for g in val:
            ep = g.group.split("-")[0].upper()
            year_num = int(g.group.split("-")[1][:2])
            admission_year = 2000 + year_num
            study_year = 2024 - admission_year
            joint_keys.add((g.course, g.type, ep, study_year))

        # Allow joint lectures (<=5 groups for same course/EP/year/type)
        if all_lectures and len(joint_keys) == 1:
            if len(val) > 5:
                hard_penalty += 1000 * (len(val) - 5)
        else:
            if len(val) > 1:
                hard_penalty += 1000 * (len(val) - 1)

    # --- GROUP CONFLICTS: online & offline ---
    # Prevent any group from having more than one session at same day+time
    for key, val in group_schedule.items():
        if len(val) > 1:
            hard_penalty += 1000 * (len(val) - 1)

    # Prevent any group from having more than one session at 18:00, 19:00, or 20:00 on the same day
    # (even if both are online lectures)
    group_day_lateslot = defaultdict(lambda: defaultdict(list))  # group -> day -> list of sessions
    for g in genes:
        if g.time in ["18:00", "19:00", "20:00"]:
            group_day_lateslot[g.group][g.day].append(g)
    for group, days in group_day_lateslot.items():
        for day, sessions in days.items():
            if len(sessions) > 1:
                # Only one allowed per group per day in 18:00/19:00/20:00, penalize all extras
                hard_penalty += 1000 * (len(sessions) - 1)

    # --- PRACTICE BEFORE LECTURE (by course) ---
    seen_lectures = set()
    for g in genes:
        tag = (g.group, g.course)
        if g.type.lower() == "lecture":
            seen_lectures.add(tag)
        elif g.type.lower() == "practice" and tag not in seen_lectures:
            soft_penalty += 10

    # --- SOFT: Gaps in group schedule per day (offline sessions only) ---
    for group, days in group_day_slots.items():
        for day, times in days.items():
            offline_times = [
                g.time for g in genes
                if g.group == group and g.day == day and getattr(g, "delivery_mode", "offline") != "online"
            ]
            offline_times_sorted = sorted(offline_times)
            gaps = 0
            for i in range(1, len(offline_times_sorted)):
                prev = int(offline_times_sorted[i - 1][:2])
                curr = int(offline_times_sorted[i][:2])
                if curr - prev > 1:
                    gaps += curr - prev - 1
            soft_penalty += gaps * 100

    return hard_penalty + soft_penalty
