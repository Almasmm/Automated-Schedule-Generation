from flask import Flask, request, send_file, send_from_directory, jsonify
import os
import shutil
import tempfile
import subprocess

# Change these as needed:
INPUTS_FOLDER = 'inputs'
OUTPUTS_FOLDER = 'outputs'
STATIC_FOLDER = 'static'
app = Flask(__name__, static_folder='static')


app = Flask(__name__, static_folder=STATIC_FOLDER)

@app.route('/')
def index():
    # Serve your HTML page
    return send_from_directory(STATIC_FOLDER, 'test_page.html')

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
    return send_file(excel_out, as_attachment=True, download_name=f'Schedule_Trimester_{trimester}.xlsx')
@app.route('/download_excel')
def download_excel():
    trimester = request.args.get('trimester', '1')
    path = f'outputs/timetable_T{trimester}.xlsx'
    return send_file(path, as_attachment=True, download_name=f'Schedule_Trimester_{trimester}.xlsx')

@app.route('/download_json')
def download_json():
    trimester = request.args.get('trimester', '1')
    path = f'outputs/timetable_T{trimester}.json'
    return send_file(path, as_attachment=True, download_name=f'Schedule_Trimester_{trimester}.json')

if __name__ == "__main__":
    app.run(port=5050, debug=True)
