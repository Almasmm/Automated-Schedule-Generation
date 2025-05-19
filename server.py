from flask import Flask, request, send_file, send_from_directory, jsonify, render_template_string
import shutil
import tempfile
import os
import subprocess
import re
import json
import pandas as pd
from collections import defaultdict
from io import BytesIO

# Change these as needed:
INPUTS_FOLDER = 'inputs'
OUTPUTS_FOLDER = 'outputs'
app = Flask(__name__, static_folder='static')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Комбинированная проверка расписания</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #181818;
            margin: 40px;
            color: #fff;
        }
        h1, h2 {
            color: #ff9800;
        }
        .upload-form {margin-bottom: 30px;}
        input[type="file"] {
            background: #222;
            color: #fff;
            border: 1px solid #444;
            padding: 8px;
            border-radius: 6px;
            margin-right: 10px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 30px;
            background: #232323;
            color: #fff;
        }
        th, td {
            padding: 8px 14px;
            border: 1px solid #444;
        }
        th {
            background: #ff9800;
            color: #181818;
        }
        tr.error-row {
            background: #2d1b09;
        }
        .btn {
            padding: 10px 25px;
            border: none;
            background: #ff9800;
            color: #181818;
            font-weight: bold;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .btn:hover {
            background: #ffa733;
        }
    </style>
</head>
<body>
    <h1>Проверка расписания на конфликты и GA_Input</h1>
    <form class="upload-form" method="post" enctype="multipart/form-data">
        <label for="timetable">Выберите файл расписания (JSON):</label>
        <input type="file" name="timetable" accept=".json" required>
        <label for="ga_input">Выберите файл GA_Input (XLSX):</label>
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

@app.route("/check", methods=["GET", "POST"])
def check_schedule():
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




@app.route('/')
def index():
    # Serve your HTML page
    return send_from_directory('static', 'test_page.html')


@app.route('/generate_schedule', methods=['POST'])
def generate_schedule():
    # 1. Get uploaded file and trimester value
    if 'file' not in request.files or 'trimester' not in request.form:
        return jsonify({'error': 'File or trimester not provided'}), 400

    file = request.files['file']
    trimester = request.form['trimester']

    # 2. Save Excel to inputs/ as GA_input.xlsx (overwrite for simplicity)
    os.makedirs(INPUTS_FOLDER, exist_ok=True)
    input_path = os.path.join(INPUTS_FOLDER, 'GA_input.xlsx')
    file.save(input_path)

    # 3. Run the scheduler for the selected trimester
    try:
        # Call your script (run_generate.py) with the trimester argument
        subprocess.run(['python', '-m', 'scripts.run_generate', str(trimester)], check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({'error': 'Schedule generation failed!', 'details': str(e)}), 500

    # 4. Locate output Excel
    excel_out = os.path.join(OUTPUTS_FOLDER, f'timetable_T{trimester}.xlsx')
    if not os.path.exists(excel_out):
        return jsonify({'error': 'No output Excel generated!'}), 500

    # 5. Send the file to the user
    return send_file(excel_out, as_attachment=True, download_name=f'timetable_T{trimester}.xlsx')
@app.route('/download_excel')
def download_excel():
    trimester = request.args.get('trimester', '1')
    path = f'outputs/timetable_T{trimester}.xlsx'
    return send_file(path, as_attachment=True, download_name=f'timetable_T{trimester}.xlsx')

@app.route('/download_json')
def download_json():
    trimester = request.args.get('trimester', '1')
    path = f'outputs/timetable_T{trimester}.json'
    return send_file(path, as_attachment=True, download_name=f'timetable_T{trimester}.json')

if __name__ == "__main__":
    app.run(port=5050, debug=True)
