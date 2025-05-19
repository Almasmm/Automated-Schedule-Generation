import argparse
import pandas as pd
from scripts.data_loader import preprocess_data
from scripts.scheduler import run_scheduler
from scripts.exporter import export_schedule

def extract_raw_genes(groups_df, courses_df, trimester):
    raw_genes = []

    # Identify columns
    group_name_col = [c for c in groups_df.columns if "group" in c.lower()][0]
    course_name_col = "course_name"
    trimester_col = [c for c in courses_df.columns if "trimester" in c.lower()][0]

    # Extract EP from group name (before dash)
    def get_ep_from_group(group_name):
        return str(group_name).split('-')[0]

    # For every group, only get courses for their EP and requested trimester
    for _, group_row in groups_df.iterrows():
        group_name = group_row[group_name_col]
        ep = get_ep_from_group(group_name).upper().strip()

        # Only use courses for this EP and trimester (no year filter)
        ep_courses = courses_df[
            (courses_df["EP"] == ep) & 
            (courses_df[trimester_col] == trimester)
        ]

        # Debug: print matched courses count
        print(f"Group: {group_name} | EP: {ep} | Courses for trimester {trimester}: {len(ep_courses)}")

        type_to_column = {
            "Lecture": "lecture_slots",
            "Practice": "practice_slots",
            "Lab": "lab_slots"
        }
        weeks_per_trimester = 10  # or change as needed

        for _, course_row in ep_courses.iterrows():
            course = course_row[course_name_col]
            for typ in ["Lecture", "Practice", "Lab"]:
                slots_col = type_to_column[typ]
                total_slots = int(course_row[slots_col]) if slots_col in course_row and pd.notnull(course_row[slots_col]) else 0
                if total_slots == 0:
                    continue
                slots_per_week = total_slots // weeks_per_trimester
                for _ in range(slots_per_week):
                    raw_genes.append({
                        "group": group_name,
                        "course": course,
                        "type": typ
                    })

    return raw_genes

def main(trimester):
    print(f"Generating schedule for trimester {trimester}...")
    print("Loading data...")

    data = preprocess_data()
    groups_df = data["groups"]
    courses_df = data["courses"]
    rooms_df = data["rooms"]

    raw_genes = extract_raw_genes(groups_df, courses_df, trimester)
    print(f"Number of raw genes generated: {len(raw_genes)}")
    if len(raw_genes) == 0:
        print("❗ No genes were generated. Check your input data for this trimester and year!")
        exit(1)

    valid_rooms = rooms_df["Room"].tolist()
    best_schedule = run_scheduler(raw_genes, valid_rooms)

    export_schedule(
        best_schedule,
        f"outputs/timetable_T{trimester}.json",
        f"outputs/timetable_T{trimester}.xlsx"
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate schedule for a given trimester.")
    parser.add_argument("trimester", type=int, help="Trimester number (1-8)")
    args = parser.parse_args()
    main(args.trimester)
