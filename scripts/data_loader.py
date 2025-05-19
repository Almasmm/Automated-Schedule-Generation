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
