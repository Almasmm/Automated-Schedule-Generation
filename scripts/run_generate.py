# scripts/run_generate.py

import argparse
import datetime
import time
import sys

from scripts.data_loader import preprocess_data, extract_raw_genes
from scripts.scheduler import run_scheduler
from scripts.exporter import export_schedule
from scripts.config import get_output_paths
from scripts import config


def main():
    parser = argparse.ArgumentParser(description="Generate schedule using Genetic Algorithm")
    parser.add_argument("trimester", type=int, help="Trimester number (e.g. 1, 2, or 3)")
    parser.add_argument("--input", help="Path to override default config.INPUT_FILE", default=None)
    args = parser.parse_args()

    if args.input:
        config.INPUT_FILE = args.input

    trimester = args.trimester

    start_ts = datetime.datetime.now()
    start_time = time.time()
    print(f"▶️  Starting generation at: {start_ts.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📦 Trimester: {trimester}")
    print(f"📄 Input file: {config.INPUT_FILE}")

    print("🔍 Preprocessing input data...")
    data = preprocess_data()
    groups_df = data["groups"]
    courses_df = data["courses"]
    rooms_df = data["rooms"]

    raw_genes = extract_raw_genes(groups_df, courses_df, trimester)
    print(f"🧬 Raw genes generated: {len(raw_genes)}")
    if not raw_genes:
        print("❗ No genes were generated. Check your input data for this trimester and year.")
        sys.exit(1)

    valid_rooms = rooms_df["Room"].tolist()
    print("⚙️ Running genetic algorithm scheduler...")
    best_schedule, fitness_progress = run_scheduler(raw_genes, valid_rooms)

    print(f"✅ Best fitness found: {best_schedule.fitness}")
    print(f"📈 Total generations run: {len(fitness_progress)}")

    json_out, excel_out = get_output_paths(trimester)
    export_schedule(best_schedule, json_out, excel_out)

    end_ts = datetime.datetime.now()
    elapsed = time.time() - start_time
    print(f"⏹️  Finished at: {end_ts.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Total generation time: {elapsed:.2f} seconds")
    print(f"📁 Output files saved to:\n   Excel: {excel_out}\n   JSON:  {json_out}")
    print(f"📊 Final gene count in schedule: {len(best_schedule.genes)}")


if __name__ == "__main__":
    main()
