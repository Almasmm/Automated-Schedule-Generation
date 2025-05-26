# scripts/validator.py

from collections import defaultdict
from .config import FIRST_YEAR_TIMESLOTS, UPPER_YEAR_TIMESLOTS, GROUP_YEAR_DAYS

def validate_schedule(chromosome):
    errors = []

    room_conflicts = defaultdict(list)
    group_conflicts = defaultdict(list)

    for gene in chromosome.genes:
        room_key = (gene.room, gene.day, gene.time)
        group_key = (gene.group, gene.day, gene.time)

        room_conflicts[room_key].append(gene)
        group_conflicts[group_key].append(gene)

        # Time validation
        year = int(gene.group.split("-")[1][:2])
        admission_year = 2000 + year
        study_year = 2024 - admission_year + 1
        allowed_days = GROUP_YEAR_DAYS.get(study_year, [])
        allowed_slots = FIRST_YEAR_TIMESLOTS if study_year == 1 else UPPER_YEAR_TIMESLOTS

        if gene.day not in allowed_days:
            errors.append(f"{gene.group} scheduled on invalid day: {gene.day}")
        if gene.time not in allowed_slots:
            errors.append(f"{gene.group} scheduled at invalid time: {gene.time}")

    # Check for room and group time clashes
    for key, sessions in room_conflicts.items():
        if len(sessions) > 1:
            errors.append(f"Room conflict at {key}: {[g.group for g in sessions]}")

    for key, sessions in group_conflicts.items():
        if len(sessions) > 1:
            errors.append(f"Group conflict at {key}: {[g.course for g in sessions]}")

    if not errors:
        print("Validation passed - No hard constraint violations found.")
    else:
        print("Validation errors:")
        for e in errors:
            print(" -", e)
    return errors
