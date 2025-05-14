"""Create ONE Excel file with the timetable of all groups, sorting: first the group code, inside the day (Mon...Sat) and time."""

from pathlib import Path
import pandas as pd

DAY_ORDER = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5}

def export_big_table(df_sched: pd.DataFrame, outfile: Path):
    # "explode" the group column ("IT-2205,IT-2206") → separate rows for each group
    rows = []
    for _, row in df_sched.iterrows():
        for g in row.group.split(","):
            rows.append({**row, "group": g})
    df = pd.DataFrame(rows)

    # rename and sort
    df.rename(columns={
        "group": "Group",
        "day": "Day",
        "time": "Time",
        "course": "Discipline",
        "room": "Classroom",
        "type": "Type"
    }, inplace=True)

    df.sort_values(
        ["Group", "Day", "Time"],
        key=lambda col: col.map(DAY_ORDER).fillna(col) if col.name == "Day" else col,
        inplace=True
    )

    with pd.ExcelWriter(outfile) as xl:
        df.to_excel(xl, index=False, sheet_name="Timetable")
