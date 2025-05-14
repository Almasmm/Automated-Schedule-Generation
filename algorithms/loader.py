"""Чтение GA_Input.xlsx и подготовка датафреймов для ГА.

  • curriculum-листы (BDH, IT …) сливаются в один Courses
  • если нет course_code → генерируется slug(course_name)
  • programme_code + year выводятся из group_code, если их нет
"""

from __future__ import annotations
from pathlib import Path
import re
import pandas as pd
from datetime import datetime

CURRENT_ACAD_YEAR = 2024  # при необходимости поменяйте на datetime.now().year

def _slug(s: str) -> str:
    """'Deep Learning' → 'DEEP_LEARNING'"""
    return re.sub(r"[^A-Z0-9]+", "_", s.upper()).strip("_")

class GAData:
    """Контейнер с курсами, группами, аудиториями, тайм-слотами."""

    def __init__(self, xlsx_path: str | Path):
        xlsx = Path(xlsx_path).expanduser().resolve()
        if not xlsx.exists():
            raise FileNotFoundError(xlsx)

        xl = pd.ExcelFile(xlsx, engine="openpyxl")

        # ---------- Courses (все листы программ) --------------------
        cur_sheets = [
            s for s in xl.sheet_names
            if s not in {"Groups", "Rooms", "Timeslots", "Departments", "Instructors"}
        ]
        frames = []
        for sh in cur_sheets:
            df = pd.read_excel(xl, sheet_name=sh)
            df["programme_code"] = sh
            if "course_code" not in df.columns:
                df["course_code"] = df["course_name"].map(_slug)
            frames.append(df)
        self.courses = pd.concat(frames, ignore_index=True)

        # ---------- Groups ------------------------------------------
        self.groups = pd.read_excel(xl, sheet_name="Groups")
        if "programme_code" not in self.groups.columns:
            self.groups["programme_code"] = self.groups["group_code"].str.extract(r"^(.*?)-")[0]
        if "year" not in self.groups.columns:
            yy = self.groups["group_code"].str.extract(r"-(\d{2})")[0].astype(int)
            self.groups["year"] = (CURRENT_ACAD_YEAR % 100) - yy + 1  # 22 → 2-й курс в 2024
            self.groups["year"] = self.groups["year"].clip(1, 3)

        # ---------- Остальные листы ---------------------------------
        self.rooms = pd.read_excel(xl, sheet_name="Rooms")
        self.times = pd.read_excel(xl, sheet_name="Timeslots")
        self.departments = pd.read_excel(xl, sheet_name="Departments")

    # ----------------------------------------------------------------
    def curriculum_for_acad_tri(self, acad_tri: int) -> pd.DataFrame:
        """Вернуть строки curriculum для академ. триместра 1|2|3 всех курсов."""
        df = self.courses.copy()
        # вычисляем абсолютный триместр для каждой строки
        if "year" not in df.columns:
            df["year"] = ((df.trimester - 1) // 3) + 1
        df["abs_tri"] = df["trimester"]
        return df[df["trimester"].mod(3).replace({0: 3}) == acad_tri]
