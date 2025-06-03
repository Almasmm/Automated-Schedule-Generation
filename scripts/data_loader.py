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
    Extracts initial raw genes (events) for the GA, grouped by group and trimester logic.
    """
    raw_genes = []

    group_name_col = [c for c in groups_df.columns if "group" in c.lower()][0]
    course_name_col = "course_name"
    trimester_col = [c for c in courses_df.columns if "trimester" in c.lower()][0]

    def get_ep_from_group(group_name):
        return str(group_name).split('-')[0]

    def get_admission_year(group_name):
        return int(group_name.split("-")[1][:2]) + 2000

    for _, group_row in groups_df.iterrows():
        group_name = group_row[group_name_col]
        ep = get_ep_from_group(group_name).upper().strip()
        admission_year = get_admission_year(group_name)
        study_year = CURRENT_YEAR - admission_year  # <-- important logic fix

        curriculum_trimester = (study_year) * 3 + trimester - 3
        # (study_year = 1) => 1st year: trimester 1,2,3
        # (study_year = 2) => 2nd year: trimester 4,5,6
        # (study_year = 3) => 3rd year: trimester 7,8,9

        ep_courses = courses_df[
            (courses_df["EP"] == ep) &
            (courses_df[trimester_col] == curriculum_trimester)
        ]

        print(f"Group: {group_name} | EP: {ep} | Study year: {study_year+1} | Curriculum trimester: {curriculum_trimester} | Courses: {len(ep_courses)}")

        type_to_column = {
            "Lecture": "lecture_slots",
            "Practice": "practice_slots",
            "Lab": "lab_slots"
        }
        weeks_per_trimester = 10

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
