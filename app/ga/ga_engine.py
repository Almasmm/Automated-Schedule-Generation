# app/ga/ga_engine.py

from scripts.data_loader import preprocess_data, extract_raw_genes
from scripts.scheduler import run_scheduler
from scripts.exporter import export_to_excel, export_to_json

def generate_schedule(input_excel_path, trimester):
    import scripts.config as config
    config.INPUT_FILE = input_excel_path

    data = preprocess_data()
    groups_df = data["groups"]
    courses_df = data["courses"]
    rooms_df = data["rooms"]

    raw_genes = extract_raw_genes(groups_df, courses_df, trimester)
    valid_rooms = rooms_df["Room"].tolist()
    best_schedule, fitness_progress = run_scheduler(raw_genes, valid_rooms) 

    return best_schedule, fitness_progress

def save_schedule(chromosome, output_excel_path, output_json_path):
    export_to_excel(chromosome, output_excel_path)
    export_to_json(chromosome, output_json_path)
