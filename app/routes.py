from flask import Blueprint, request, send_file, send_from_directory, jsonify, render_template
import os
import sys
import subprocess
import json
from app.utils.schedule_check import check_conflicts_and_violations

bp = Blueprint('main', __name__)

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INPUTS_FOLDER = os.path.join(PROJECT_ROOT, 'inputs')
OUTPUTS_FOLDER = os.path.join(PROJECT_ROOT, 'outputs')

@bp.route("/check", methods=["GET", "POST"])
def check_schedule():
    conflict_table = None
    violation_table = None
    if request.method == "POST":
        tf = request.files["timetable"]
        gf = request.files.get("ga_input")
        timetable_name = tf.filename
        timetable = json.load(tf)
        conflict_table, violation_table = check_conflicts_and_violations(timetable, timetable_name, gf)
    return render_template("check.html", conflict_table=conflict_table, violation_table=violation_table)

@bp.route('/')
def index():
    return send_from_directory('static', 'test_page.html')


@bp.route('/generate_schedule', methods=['POST'])
def generate_schedule_route():
    if 'file' not in request.files or 'trimester' not in request.form:
        return jsonify({'error': 'File or trimester not provided'}), 400
    file = request.files['file']
    trimester = request.form['trimester']
    os.makedirs(INPUTS_FOLDER, exist_ok=True)
    input_path = os.path.join(INPUTS_FOLDER, 'GA_input.xlsx')
    file.save(input_path)
    try:
        subprocess.run([sys.executable, '-m', 'scripts.run_generate', str(trimester)], check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({'error': 'Schedule generation failed!', 'details': str(e)}), 500
    excel_out = os.path.join(OUTPUTS_FOLDER, f'timetable_T{trimester}.xlsx')
    if not os.path.exists(excel_out):
        return jsonify({'error': 'No output Excel generated!'}), 500
    return send_file(excel_out, as_attachment=True, download_name=f'timetable_T{trimester}.xlsx')

@bp.route('/download_excel')
def download_excel():
    trimester = request.args.get('trimester', '1')
    path = os.path.join(OUTPUTS_FOLDER, f'timetable_T{trimester}.xlsx')
    return send_file(path, as_attachment=True, download_name=f'timetable_T{trimester}.xlsx')

@bp.route('/download_json')
def download_json():
    trimester = request.args.get('trimester', '1')
    path = os.path.join(OUTPUTS_FOLDER, f'timetable_T{trimester}.json')
    return send_file(path, as_attachment=True, download_name=f'timetable_T{trimester}.json')

