import re
import json
import pandas as pd
from collections import defaultdict

def check_conflicts_and_violations(timetable, timetable_name, ga_input_file):
    # Conflict analysis
    conflicts = defaultdict(list)
    room_usage = defaultdict(lambda: defaultdict(list))
    group_usage = defaultdict(lambda: defaultdict(list))
    for group, sessions in timetable.items():
        for s in sessions:
            key = (s["day"], s["time"])
            room = s["room"]
            group_id = s["group"]
            room_usage[key][room].append((group_id, s["course"]))
            group_usage[key][group_id].append(s["course"])
    for key, rooms in room_usage.items():
        for room, usage in rooms.items():
            if room.strip().lower() == "gym":
                continue
            if len(usage) > 1:
                conflicts["Room conflict"].append((key, room, usage))
    for key, groups in group_usage.items():
        for group_id, usage in groups.items():
            if len(usage) > 1:
                conflicts["Group conflict"].append((key, group_id, [(group_id, c) for c in usage]))
    rows = []
    for ctype, items in conflicts.items():
        for item in items:
            details = "; ".join(f"{a}: {b}" for a, b in item[2])
            rows.append((ctype, item[0][0], item[0][1], item[1], details))
    conflict_df = pd.DataFrame(rows, columns=["Тип конфликта", "День", "Время", "Сущность", "Детали"])
    if not conflict_df.empty:
        conflict_df.index += 1
        conflict_df.reset_index(inplace=True)
        conflict_df.rename(columns={"index": "№"}, inplace=True)
        conflict_table = conflict_df.to_html(index=False)
    else:
        conflict_table = None

    # Violation analysis
    violation_table = None
    if ga_input_file:
        trimester_match = re.search(r'T(\d+)', timetable_name)
        if trimester_match:
            trimester_base = int(trimester_match.group(1))
            xls = pd.ExcelFile(ga_input_file)
            all_sheets = xls.sheet_names

            def get_ep(g): return g.split("-")[0].upper()
            def map_trimester(base, year):
                m = {1: {1:1, 2:2, 3:3}, 2: {1:4,2:5,3:6}, 3:{1:7,2:8}}
                return m.get(year, {}).get(base)
            group_course_type_count = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
            for group, sessions in timetable.items():
                for s in sessions:
                    group_course_type_count[group][s["course"].strip().lower()][s["type"].strip().lower()] += 10
            violations = []
            for group in timetable:
                ep = get_ep(group)
                year_code = int(group.split("-")[1][:2])
                year = 1 if year_code == 23 else 2 if year_code == 22 else 3
                actual_trim = map_trimester(trimester_base, year)
                if not actual_trim or actual_trim == 9 or ep not in all_sheets:
                    continue
                df = xls.parse(ep)
                df.columns = [c.lower().strip() for c in df.columns]
                if 'trimester' not in df.columns: continue
                df = df[df['trimester'] == actual_trim]
                df['course_name'] = df['course_name'].astype(str).str.strip().str.lower()
                for _, row in df.iterrows():
                    cname = row['course_name']
                    if not cname or cname == 'nan': continue
                    for typ in ['lecture', 'practice', 'lab']:
                        sc = f"{typ}_slots"
                        if not pd.isna(row.get(sc)) and int(row[sc]) > 0:
                            req = int(row[sc])
                            act = group_course_type_count[group][cname][typ]
                            if act < req:
                                violations.append({
                                    "group": group, "ep": ep, "trimester": actual_trim,
                                    "course": cname, "type": typ,
                                    "required": req, "actual": act, "missing": req - act
                                })
            violation_df = pd.DataFrame(violations)
            if not violation_df.empty:
                violation_table = violation_df.to_html(index=False)
    return conflict_table, violation_table
