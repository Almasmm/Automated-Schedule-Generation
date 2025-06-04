# app/utils/schedule_check.py
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

    conflict_rows = []
    for conflict_type, items in conflicts.items():
        for item in items:
            details = "; ".join(f"{a}: {b}" for a, b in item[2])
            conflict_rows.append((conflict_type, item[0][0], item[0][1], item[1], details))

    conflict_df = pd.DataFrame(conflict_rows, columns=["Conflict Type", "Day", "Time", "Entity", "Details"])
    if not conflict_df.empty:
        conflict_df.index += 1
        conflict_df.reset_index(inplace=True)
        conflict_df.rename(columns={"index": "No"}, inplace=True)
        conflict_table = conflict_df.to_html(index=False, classes="table table-bordered table-striped table-hover")
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
                m = {1: {1:1, 2:2, 3:3}, 2: {1:4, 2:5, 3:6}, 3:{1:7, 2:8}}
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
                if 'trimester' not in df.columns:
                    continue
                df = df[df['trimester'] == actual_trim]
                df['course_name'] = df['course_name'].astype(str).str.strip().str.lower()

                for _, row in df.iterrows():
                    cname = row['course_name']
                    if not cname or cname == 'nan':
                        continue
                    for typ in ['lecture', 'practice', 'lab']:
                        sc = f"{typ}_slots"
                        if not pd.isna(row.get(sc)) and int(row[sc]) > 0:
                            req = int(row[sc])
                            act = group_course_type_count[group][cname][typ]
                            if act < req:
                                violations.append({
                                    "Group": group, "EP": ep, "Trimester": actual_trim,
                                    "Course": cname, "Type": typ,
                                    "Required": req, "Actual": act, "Missing": req - act
                                })

            violation_df = pd.DataFrame(violations)
            if not violation_df.empty:
                violation_df.index += 1
                violation_df.reset_index(inplace=True)
                violation_df.rename(columns={"index": "No"}, inplace=True)
                violation_table = violation_df.to_html(index=False, classes="table table-bordered table-striped table-hover")

    return conflict_table, violation_table

def get_subject(course_str):
    """Extracts the subject part from a course name (handles 'CODE: Subject')."""
    parts = course_str.split(':', 1)
    return parts[1].strip().lower() if len(parts) > 1 else course_str.strip().lower()

def get_group_prefix(group_id):
    """Gets a group prefix for conflict logic."""
    group_id = group_id.strip()
    if group_id.startswith("BDA-") or group_id.startswith("IoT-"):
        return group_id[:6]
    else:
        return group_id[:5]

def advanced_conflict_and_violation_analysis(timetable, timetable_name, ga_input_file):
    """
    Advanced room/group conflict analysis allowing up to 5 groups with same subject/joint lecture in same slot+room.
    Used for the /check route.
    """
    import pandas as pd
    import re
    from collections import defaultdict

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

    MAX_GROUPS_WITHOUT_CONFLICT = 5

    # Room conflict with joint lecture exception logic
    for key, rooms in room_usage.items():
        for room, usage in rooms.items():
            if room.strip().lower() in ("gym", "online"):
                continue
            if len(usage) > 1:
                group_ids = [u[0].strip() for u in usage]
                subjects = [get_subject(u[1]) for u in usage]
                prefix_set = set(get_group_prefix(gid) for gid in group_ids)
                subject_set = set(subjects)
                if (
                    len(prefix_set) == 1 and
                    len(subject_set) == 1 and
                    len(group_ids) <= MAX_GROUPS_WITHOUT_CONFLICT
                ):
                    continue  # Exception: joint lecture for same subject and group prefix
                conflicts["Room conflict"].append((key, room, usage))

    # Group conflict with exception logic
    for key, groups in group_usage.items():
        group_ids = [gid.strip() for gid in groups.keys()]
        if len(groups) > 1:
            subjects_per_group = [set(get_subject(c) for c in usage) for usage in groups.values()]
            common_subjects = set.intersection(*subjects_per_group) if subjects_per_group else set()
            prefixes = set(get_group_prefix(gid) for gid in group_ids)
            if len(common_subjects) == 1 and len(prefixes) == 1 and len(group_ids) <= MAX_GROUPS_WITHOUT_CONFLICT:
                continue  # Exception: joint lecture/group, skip as conflict
        for group_id, usage in groups.items():
            if len(usage) > 1:
                conflicts["Group conflict"].append((key, group_id, [(group_id, c) for c in usage]))

    # Prepare DataFrame
    rows = []
    for ctype, items in conflicts.items():
        for item in items:
            details = "; ".join(f"{a}: {b}" for a, b in item[2])
            rows.append((ctype, item[0][0], item[0][1], item[1], details))
    conflict_df = pd.DataFrame(rows, columns=["Conflict Type", "Day", "Time", "Entity", "Details"])
    if not conflict_df.empty:
        conflict_df.index += 1
        conflict_df.reset_index(inplace=True)
        conflict_df.rename(columns={"index": "No"}, inplace=True)
        conflict_table = conflict_df.to_html(index=False, classes="table table-bordered table-striped table-hover")
    else:
        conflict_table = None

    # --- Use your old GA_Input violation logic as before ---
    violation_table = None
    if ga_input_file:
        trimester_match = re.search(r'T(\d+)', timetable_name)
        if trimester_match:
            trimester_base = int(trimester_match.group(1))
            xls = pd.ExcelFile(ga_input_file)
            all_sheets = xls.sheet_names

            def get_ep(g): return g.split("-")[0].upper()
            def map_trimester(base, year):
                m = {1: {1:1, 2:2, 3:3}, 2: {1:4, 2:5, 3:6}, 3:{1:7, 2:8}}
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
                if 'trimester' not in df.columns:
                    continue
                df = df[df['trimester'] == actual_trim]
                df['course_name'] = df['course_name'].astype(str).str.strip().str.lower()

                for _, row in df.iterrows():
                    cname = row['course_name']
                    if not cname or cname == 'nan':
                        continue
                    for typ in ['lecture', 'practice', 'lab']:
                        sc = f"{typ}_slots"
                        if not pd.isna(row.get(sc)) and int(row[sc]) > 0:
                            req = int(row[sc])
                            act = group_course_type_count[group][cname][typ]
                            if act < req:
                                violations.append({
                                    "Group": group, "EP": ep, "Trimester": actual_trim,
                                    "Course": cname, "Type": typ,
                                    "Required": req, "Actual": act, "Missing": req - act
                                })

            violation_df = pd.DataFrame(violations)
            if not violation_df.empty:
                violation_df.index += 1
                violation_df.reset_index(inplace=True)
                violation_df.rename(columns={"index": "No"}, inplace=True)
                violation_table = violation_df.to_html(index=False, classes="table table-bordered table-striped table-hover")

    return conflict_table, violation_table
