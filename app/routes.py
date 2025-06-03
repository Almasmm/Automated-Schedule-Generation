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
    checked = False
    if request.method == "POST":
        checked = True
        tf = request.files["timetable"]
        gf = request.files.get("ga_input")
        timetable_name = tf.filename
        timetable = json.load(tf)
        conflict_table, violation_table = check_conflicts_and_violations(timetable, timetable_name, gf)
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
    if 'file' not in request.files or 'trimester' not in request.form:
        return jsonify({'error': 'File or trimester not provided'}), 400
    file = request.files['file']
    trimester = request.form['trimester']
    os.makedirs(INPUTS_FOLDER, exist_ok=True)
    input_path = os.path.join(INPUTS_FOLDER, 'GA_input.xlsx')
    file.save(input_path)
    # Import here to avoid circular imports
    from app.ga.ga_engine import generate_schedule, save_schedule
    import time
    try:
        start = time.time()
        # Generate the best schedule (Chromosome object)
        best_schedule = generate_schedule(input_path, int(trimester))
        elapsed = round(time.time() - start, 2)
        # Save the outputs (Excel, JSON)
        excel_out = os.path.join(OUTPUTS_FOLDER, f'timetable_T{trimester}.xlsx')
        json_out = os.path.join(OUTPUTS_FOLDER, f'timetable_T{trimester}.json')
        save_schedule(best_schedule, excel_out, json_out)
        # Get fitness/conflicts/hard/soft
        fitness_score = best_schedule.fitness
        # For hard/soft constraint breakdown, you may need to enhance your evaluate_fitness to return both
        # For now, let's just send the total fitness
        # Count conflicts (very basic: hard penalty occurrences)
        conflicts = int(fitness_score // 1000) # You may improve this logic!
        best_schedule, fitness_progress = generate_schedule(input_path, int(trimester))
        metrics = {
            "fitnessScore": round(10000 / (1 + fitness_score), 2),
            "conflicts": conflicts,
            "hard": "-",    
            "soft": "-",    
            "time": elapsed,
            "fitness_progress": fitness_progress
        }
        return jsonify(metrics)
    except Exception as e:
        return jsonify({'error': 'Schedule generation failed!', 'details': str(e)}), 500


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

