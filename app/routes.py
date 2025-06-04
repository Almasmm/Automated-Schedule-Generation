# app/routes.py

from flask import Blueprint, request, send_file, jsonify, render_template
import os
import json
from app.utils.schedule_check import (
    check_conflicts_and_violations,
    get_subject,
    get_group_prefix,
    advanced_conflict_and_violation_analysis,
)
from scripts.config import get_output_paths

bp = Blueprint('main', __name__)

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INPUTS_FOLDER = os.path.join(PROJECT_ROOT, 'inputs')
OUTPUTS_FOLDER = os.path.join(PROJECT_ROOT, 'outputs')

# Cache of the most recently generated output paths per trimester
LAST_OUTPUTS = {}

@bp.route("/check", methods=["GET", "POST"])
def check_schedule():
    """
    Handles schedule checking and displays conflicts/violations.
    Now supports advanced joint lectures logic from old server.py.
    """
    conflict_table = None
    violation_table = None
    checked = False
    if request.method == "POST":
        checked = True
        tf = request.files["timetable"]
        gf = request.files.get("ga_input")
        timetable_name = tf.filename
        timetable = json.load(tf)
        # --- Use ADVANCED logic with joint lectures exception handling ---
        conflict_table, violation_table = advanced_conflict_and_violation_analysis(
            timetable, timetable_name, gf
        )
    return render_template(
        'check.html',
        conflict_table=conflict_table,
        violation_table=violation_table,
        checked=checked
    )


@bp.route('/')
def index():
    return render_template('main_page.html')


@bp.route('/generate_schedule', methods=['POST'])
def generate_schedule_route():
    """
    Handles schedule generation and returns metrics JSON.
    Generated files are saved to the static output paths defined in ``config.get_output_paths``.
    """
    if 'file' not in request.files or 'trimester' not in request.form:
        return jsonify({'error': 'File or trimester not provided'}), 400
    file = request.files['file']
    trimester = request.form['trimester']
    os.makedirs(INPUTS_FOLDER, exist_ok=True)
    input_path = os.path.join(INPUTS_FOLDER, 'GA_input.xlsx')
    file.save(input_path)
    from app.ga.ga_engine import generate_schedule, save_schedule
    import time
    try:
        start = time.time()
        # First call gets best_schedule & fitness_progress
        best_schedule, fitness_progress = generate_schedule(input_path, int(trimester))
        elapsed = round(time.time() - start, 2)
        json_out, excel_out = get_output_paths(trimester)
        save_schedule(best_schedule, excel_out, json_out)

        # Remember the latest outputs for this trimester
        LAST_OUTPUTS[trimester] = (excel_out, json_out)
        
        from scripts.evaluator import compute_penalties
        hard, soft = compute_penalties(best_schedule.genes)
        metrics = {
            "fitnessScore": best_schedule.fitness,
            "hard": int(hard),
            "soft": int(soft),   
            "time": elapsed,
            "fitness_progress": fitness_progress
        }
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': 'Schedule generation failed!', 'details': str(e)}), 500

@bp.route('/download_excel')
def download_excel():
    """
    Downloads most recent Excel file for given trimester.
    """
    trimester = request.args.get('trimester', '1')
    cached = LAST_OUTPUTS.get(trimester)
    if cached:
        excel_path, _ = cached
        if os.path.exists(excel_path):
            return send_file(excel_path, as_attachment=True, download_name=os.path.basename(excel_path))

    # fallback to old style, for backward compat
    fallback = os.path.join(OUTPUTS_FOLDER, f'timetable_T{trimester}.xlsx')
    if not os.path.exists(fallback):
        return "Excel file not found", 404
    return send_file(fallback, as_attachment=True, download_name=f'timetable_T{trimester}.xlsx')


@bp.route('/download_json')
def download_json():
    """
    Downloads most recent JSON file for given trimester.
    """
    trimester = request.args.get('trimester', '1')
    cached = LAST_OUTPUTS.get(trimester)
    if cached:
        _, json_path = cached
        if os.path.exists(json_path):
            return send_file(json_path, as_attachment=True, download_name=os.path.basename(json_path))

    fallback = os.path.join(OUTPUTS_FOLDER, f'timetable_T{trimester}.json')
    if not os.path.exists(fallback):
        return "JSON file not found", 404
    return send_file(fallback, as_attachment=True, download_name=f'timetable_T{trimester}.json')

