
import os
import re
import json
from flask import Flask, render_template_string, request, send_file
import pandas as pd
from collections import defaultdict
from io import BytesIO

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Комбинированная проверка расписания</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f8f9fa; margin: 40px;}
        h1 { color: #d7263d;}
        .upload-form {margin-bottom: 30px;}
        table { border-collapse: collapse; width: 100%; margin-top: 30px;}
        th, td { padding: 8px 14px; border: 1px solid #ddd; }
        th { background: #fa8b8b; }
        tr.error-row { background: #ffe5e5; }
        .btn { padding: 10px 25px; border: none; background: #d7263d; color: #fff; font-weight: bold; border-radius: 8px; cursor: pointer;}
        .btn:hover { background: #bc2335; }
    </style>
</head>
<body>
    <h1>Проверка расписания на конфликты и GA_Input</h1>
    <form class="upload-form" method="post" enctype="multipart/form-data">
        <input type="file" name="timetable" accept=".json" required>
        <input type="file" name="ga_input" accept=".xlsx">
        <button class="btn" type="submit">Проверить</button>
    </form>
    {% if conflict_table %}
        <h2>Конфликты</h2>
        {{ conflict_table | safe }}
    {% endif %}
    {% if violation_table %}
        <h2>Нарушения по GA_Input</h2>
        
        {{ violation_table | safe }}
    {% endif %}
</body>
</html>
"""

last_conflict_df = None
last_violation_df = None

@app.route("/", methods=["GET", "POST"])
def index():
    global last_conflict_df, last_violation_df
    conflict_table = None
    violation_table = None
    if request.method == "POST":
        tf = request.files["timetable"]
        gf = request.files.get("ga_input")
        timetable_name = tf.filename
        timetable = json.load(tf)

        # ---------- Конфликт-анализ ----------
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
        last_conflict_df = pd.DataFrame(rows, columns=["Тип конфликта", "День", "Время", "Сущность", "Детали"])
        last_conflict_df.index += 1
        last_conflict_df.reset_index(inplace=True)
        last_conflict_df.rename(columns={"index": "№"}, inplace=True)
        if not last_conflict_df.empty:
            conflict_table = last_conflict_df.to_html(index=False)

        # ---------- GA_Input-анализ ----------
        if gf:
            trimester_match = re.search(r'T(\d+)', timetable_name)
            if trimester_match:
                trimester_base = int(trimester_match.group(1))
                xls = pd.ExcelFile(gf)
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
                last_violation_df = pd.DataFrame(violations)
                if not last_violation_df.empty:
                    violation_table = last_violation_df.to_html(index=False)
    return render_template_string(HTML_TEMPLATE, conflict_table=conflict_table, violation_table=violation_table)


if __name__ == "__main__":
    app.run(debug=True)
