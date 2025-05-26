# scripts/run_generate.py

import sys
from app.ga.ga_engine import generate_schedule, save_schedule

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.run_generate <trimester>")
        sys.exit(1)
    trimester = int(sys.argv[1])
    input_path = "inputs/GA_input.xlsx"
    output_xlsx = f"outputs/timetable_T{trimester}.xlsx"
    output_json = f"outputs/timetable_T{trimester}.json"

    best_schedule = generate_schedule(input_path, trimester)
    save_schedule(best_schedule, output_xlsx, output_json)
    print(f"Generated: {output_xlsx}, {output_json}")

if __name__ == "__main__":
    main()
