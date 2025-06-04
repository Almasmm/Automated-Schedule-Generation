# scripts/run_generate.py
import sys
from scripts.data_loader import preprocess_data, extract_raw_genes
from scripts.scheduler import run_scheduler
from scripts.exporter import export_schedule
from scripts.config import get_output_paths

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.run_generate <trimester>")
        sys.exit(1)
    trimester = int(sys.argv[1])

    print(f"Loading data and extracting raw genes for trimester {trimester} ...")
    data = preprocess_data()
    groups_df = data["groups"]
    courses_df = data["courses"]
    rooms_df = data["rooms"]

    raw_genes = extract_raw_genes(groups_df, courses_df, trimester)
    print(f"Number of raw genes generated: {len(raw_genes)}")
    if not raw_genes:
        print("❗ No genes were generated. Check your input data for this trimester and year!")
        sys.exit(1)

    valid_rooms = rooms_df["Room"].tolist()
    print("Running scheduler...")
    best_schedule, fitness_progress = run_scheduler(raw_genes, valid_rooms)
    print(f"Best fitness found: {best_schedule.fitness}")

    json_out, excel_out = get_output_paths(trimester)
    export_schedule(best_schedule, json_out, excel_out)
    print(f"Schedule generated. Files saved to:\n  Excel: {excel_out}\n  JSON: {json_out}")

if __name__ == "__main__":
    main()

