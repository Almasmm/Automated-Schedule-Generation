# scripts/data_loader.py

import pandas as pd
from scripts.config import (
    INPUT_FILE, EXCLUDED_COURSES, EXCLUDED_ROOMS, CURRENT_YEAR
)

def load_excel_data():
    """Load all relevant sheets from GA_input.xlsx"""
    xl = pd.ExcelFile(INPUT_FILE)
    sheets = {sheet_name: xl.parse(sheet_name) for sheet_name in xl.sheet_names}
    return sheets

def determine_group_year(group_name: str) -> int:
    """Infer year of the group from its name like 'IT-2201'"""
    try:
        admission_year = int(group_name.split("-")[1][:2]) + 2000
        study_year = CURRENT_YEAR - admission_year + 1
        return study_year
    except Exception:
        return -1  # fallback if parsing fails

def preprocess_data():
    """Load, filter, and structure input data"""
    data = load_excel_data()

    groups_df = data.get("Groups")
    curriculum_sheets = []
    for sheet_name, df in data.items():
        if sheet_name not in ["Groups", "Rooms", "Instructors"]:
            df = df.copy()
            df["EP"] = sheet_name
            curriculum_sheets.append(df)

    if curriculum_sheets:
        courses_df = pd.concat(curriculum_sheets, ignore_index=True)
    else:
        raise ValueError("No curriculum sheets found in input Excel file!")

    # Clean up for case/type mismatches
    courses_df["EP"] = courses_df["EP"].astype(str).str.upper().str.strip()
    courses_df = courses_df.dropna(subset=["trimester"])
    courses_df["trimester"] = courses_df["trimester"].astype(int)

    rooms_df = data.get("Rooms")
    instructors_df = data.get("Instructors")

    # Filter out excluded rooms
    rooms_df = rooms_df[~rooms_df["Room"].isin(EXCLUDED_ROOMS)]

    # Filter out excluded courses
    def is_valid_course(course):
        return not any(x in str(course) for x in EXCLUDED_COURSES)
    courses_df = courses_df[courses_df["course_name"].apply(is_valid_course)]

    # Add year info to groups
    groups_df["Year"] = groups_df["Group"].apply(determine_group_year)

    return {
        "groups": groups_df,
        "courses": courses_df,
        "rooms": rooms_df,
        "instructors": instructors_df
    }


def extract_raw_genes(groups_df, courses_df, trimester):
    """
    Advanced gene extraction: joint lectures, delivery_mode, batching
    """
    raw_genes = []

    group_name_col = [c for c in groups_df.columns if "group" in c.lower()][0]
    course_name_col = "course_name"
    trimester_col = [c for c in courses_df.columns if "trimester" in c.lower()][0]
    delivery_col = next((c for c in courses_df.columns if "delivery_mode" in c.lower()), None)

    def get_ep(group: str) -> str:
        return str(group).split("-")[0]

    def admission_year(group: str) -> int:
        return int(group.split("-")[1][:2]) + 2000

    # Group groups by programme and study year
    groups_by_ep_year = {}
    for _, g_row in groups_df.iterrows():
        gname = g_row[group_name_col]
        ep = get_ep(gname).upper().strip()
        study_year = CURRENT_YEAR - admission_year(gname) + 1
        groups_by_ep_year.setdefault((ep, study_year), []).append(gname)

    weeks_per_trimester = 10

    # Aggregate joint lecture info
    joint_lecture_slots = {}
    joint_lecture_groups = {}

    for (ep, study_year), g_list in groups_by_ep_year.items():
        curriculum_trimester = (study_year - 1) * 3 + trimester
        ep_courses = courses_df[
            (courses_df["EP"] == ep) &
            (courses_df[trimester_col] == curriculum_trimester)
        ]
        # Print for debug:
        # print(f"EP: {ep} | Year: {study_year} | Trim: {curriculum_trimester} | Groups: {g_list} | Courses: {len(ep_courses)}")

        type_to_column = {
            "Lecture": "lecture_slots",
            "Practice": "practice_slots",
            "Lab": "lab_slots"
        }

        for _, c_row in ep_courses.iterrows():
            course = c_row[course_name_col]
            delivery = str(c_row.get(delivery_col)).strip().lower() if delivery_col and pd.notnull(c_row.get(delivery_col)) else "offline"
            lec_val = c_row.get("lecture_slots", 0)
            prac_val = c_row.get("practice_slots", 0)
            lab_val = c_row.get("lab_slots", 0)
            lec_total = int(lec_val) if pd.notnull(lec_val) else 0
            prac_total = int(prac_val) if pd.notnull(prac_val) else 0
            lab_total = int(lab_val) if pd.notnull(lab_val) else 0

            lec_pw = lec_total // weeks_per_trimester
            prac_pw = prac_total // weeks_per_trimester
            lab_pw = lab_total // weeks_per_trimester

            # Collect joint lectures
            if lec_pw > 0:
                joint_lecture_slots[(ep, study_year, course)] = lec_pw
                joint_lecture_groups[(ep, study_year, course)] = g_list

            if prac_pw > 0:
                for g in g_list:
                    for _ in range(prac_pw):
                        raw_genes.append({
                            "group": g,
                            "course": course,
                            "type": "Practice",
                            "delivery_mode": "offline",
                        })

            if lab_pw > 0:
                for g in g_list:
                    for _ in range(lab_pw):
                        raw_genes.append({
                            "group": g,
                            "course": course,
                            "type": "Lab",
                            "delivery_mode": "offline",
                        })

    # After all, build lecture genes as joint (batch by 5 if offline, all if online)
    for (ep, study_year, course), slots in joint_lecture_slots.items():
        row = courses_df[
            (courses_df["EP"] == ep)
            & (courses_df[trimester_col] == (study_year - 1) * 3 + trimester)
            & (courses_df[course_name_col] == course)
        ].iloc[0]
        delivery = str(row.get(delivery_col)).strip().lower() if delivery_col and pd.notnull(row.get(delivery_col)) else "offline"

        groups = joint_lecture_groups[(ep, study_year, course)]
        batches = [groups] if delivery == "online" else [groups[i:i+5] for i in range(0, len(groups), 5)]

        for _ in range(slots):
            for batch in batches:
                raw_genes.append({
                    "joint_groups": batch,
                    "course": course,
                    "type": "Lecture",
                    "delivery_mode": delivery,
                })

    return raw_genes
