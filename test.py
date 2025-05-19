import os
from flask import Flask, render_template_string, request, send_file
import pandas as pd
import json
from collections import defaultdict
from io import BytesIO

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Проверка расписания</title>
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
    <h1>Проверка конфликтов в расписании</h1>
    <form class="upload-form" method="post" enctype="multipart/form-data">
        <input type="file" name="timetable" accept=".json" required>
        <button class="btn" type="submit">Проверить расписание</button>
    </form>
    {% if table %}
        <a href="/download" class="btn">Скачать ошибки (Excel)</a>
        {{ table | safe }}
    {% endif %}
</body>
</html>
"""

def analyze_conflicts(timetable):
    conflicts = defaultdict(list)
    room_usage = defaultdict(lambda: defaultdict(list))
    group_usage = defaultdict(lambda: defaultdict(list))

    for group, sessions in timetable.items():
        for session in sessions:
            key = (session["day"], session["time"])
            room = session["room"]
            group_id = session["group"]
            # Room conflict (без Gym)
            room_usage[key][room].append((group_id, session["course"]))
            # Group conflict
            group_usage[key][group_id].append(session["course"])

    for key, rooms in room_usage.items():
        for room, usage in rooms.items():
            if room.strip().lower() == "gym":  # Игнорируем Gym
                continue
            if len(usage) > 1:
                conflicts["Room conflict"].append((key, room, usage))
    for key, groups in group_usage.items():
        for group_id, usage in groups.items():
            if len(usage) > 1:
                # usage — это список курсов
                course_pairs = [(group_id, course) for course in usage]
                conflicts["Group conflict"].append((key, group_id, course_pairs))

    conflict_list = []
    for conflict_type, entries in conflicts.items():
        for entry in entries:
            details_str = []
            for detail in entry[2]:
                if isinstance(detail, (list, tuple)) and len(detail) == 2:
                    details_str.append(f"{detail[0]}: {detail[1]}")
                else:
                    details_str.append(str(detail))
            conflict_list.append((
                conflict_type, 
                entry[0][0],  # day
                entry[0][1],  # time
                entry[1],     # entity
                "; ".join(details_str)
            ))
    df_conflicts = pd.DataFrame(conflict_list, columns=["Тип конфликта", "День", "Время", "Сущность", "Детали"])
    df_conflicts.index = df_conflicts.index + 1  # Для нумерации строк с 1
    df_conflicts.reset_index(inplace=True)
    df_conflicts.rename(columns={'index': '№'}, inplace=True)
    return df_conflicts

# Сохраняем последний DataFrame для скачивания
last_conflicts_df = None

@app.route('/', methods=['GET', 'POST'])
def index():
    global last_conflicts_df
    table_html = None
    if request.method == 'POST':
        file = request.files['timetable']
        if file and file.filename.endswith('.json'):
            timetable = json.load(file)
            df_conflicts = analyze_conflicts(timetable)
            last_conflicts_df = df_conflicts  # Сохраним для скачивания
            if not df_conflicts.empty:
                table_html = df_conflicts.to_html(classes='error-table', index=False, border=0, escape=False)
            else:
                table_html = "<p style='color:green;font-weight:bold;'>Конфликтов не найдено! 🎉</p>"
    return render_template_string(HTML_TEMPLATE, table=table_html)

@app.route('/download')
def download():
    global last_conflicts_df
    if last_conflicts_df is None or last_conflicts_df.empty:
        return "Нет данных для скачивания", 400
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        last_conflicts_df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="conflicts.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == "__main__":
    app.run(debug=True)
