# exporter.py ---------------------------------------------------------

"""Pretty XLSX export grouped by group, sorted by day+time."""
import pandas as pd
from pathlib import Path
from loader import GAData

DAY_ORDER = {d: i for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])}

def export(schedule: list[dict], data: GAData, trimester: int):
    df = pd.DataFrame(schedule)
    slot_map = data.times.set_index("slot_id")[["day", "start", "end"]]
    df = df.join(slot_map, on="slot")
    df["Time"] = df["start"] + "-" + df["end"]
    df.sort_values(["group", df.day.map(DAY_ORDER), "start"], inplace=True)

    out = Path(f"timetable_T{trimester}.xlsx")
    with pd.ExcelWriter(out) as xl:
        for grp, block in df.groupby("group"):
            block = block.rename(columns={
                "day": "Day",
                "course": "Discipline",
                "room": "Classroom",
                "type": "Type"
            })[["Day", "Time", "Discipline", "Classroom", "Type"]]
            block.to_excel(xl, index=False, sheet_name=grp[:30])
    print("✓ Pretty Excel saved to", out)
