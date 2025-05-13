# loader.py -----------------------------------------------------------

"""Read GA_Input.xlsx and build internal data frames.
Handles:
  • deriving `programme_code`, `year` from group_code (IT-2205 → programme=IT, year=2)
  • slug‑generating `course_code` if absent
  • merging all programme sheets into one Courses DataFrame
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd
import re

def slug(s: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", s.upper()).strip("_")

class GAData:  # simple container
    def __init__(self, xlsx: Path):
        xl = pd.ExcelFile(xlsx)
        # identify curriculum sheets
        curriculum_sheets = [s for s in xl.sheet_names if s not in {"Groups", "Rooms", "Timeslots", "Departments", "Instructors"}]
        courses = []
        for sh in curriculum_sheets:
            df = pd.read_excel(xl, sheet_name=sh)
            df["programme_code"] = sh
            if "course_code" not in df.columns:
                df["course_code"] = df["course_name"].map(slug)
            courses.append(df)
        self.courses = pd.concat(courses, ignore_index=True)
        self.groups = pd.read_excel(xl, sheet_name="Groups")
        if "programme_code" not in self.groups.columns:
            self.groups["programme_code"] = self.groups["group_code"].str.extract(r"^(.*?)-")[0]
        if "year" not in self.groups.columns:
            self.groups["year"] = self.groups["group_code"].str.extract(r"-(\d)(\d)\d{2}")[0].astype(int)
        self.rooms = pd.read_excel(xl, sheet_name="Rooms")
        self.times = pd.read_excel(xl, sheet_name="Timeslots")
        self.departments = pd.read_excel(xl, sheet_name="Departments")

    def curriculum_for_trimester(self, tri: int):
        cur = self.courses[self.courses.trimester == tri].copy()
        if "year" not in cur.columns:
            cur["year"] = ((cur.trimester - 1) // 3) + 1
        return cur