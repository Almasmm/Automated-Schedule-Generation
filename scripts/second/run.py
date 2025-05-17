"""CLI-обёртка: validate | generate"""

from __future__ import annotations
import argparse, json
from pathlib import Path
from loader import GAData
from ga_engine import run_ga
from exporter import export_big_table
import config as cfg

# ------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Проверка структуры Excel")
    v.add_argument("--xlsx", required=True)

    g = sub.add_parser("generate", help="Сгенерировать расписание")
    g.add_argument("--xlsx", required=True)
    g.add_argument("--acad-tri", type=int, choices=[1,2,3], default=1,
                   help="Учебный триместр (1/2/3) для всех курсов")
    g.add_argument("--pop", type=int, default=cfg.POPULATION)
    g.add_argument("--gen", type=int, default=cfg.GENERATIONS)
    g.add_argument("--seed", type=int, default=1)

    return p.parse_args()

# ------------------------------------------------------------------
def validate(data: GAData):
    print(f"Courses: {len(data.courses)}")
    print(f"Groups : {len(data.groups)}")
    print(f"Rooms  : {len(data.rooms)}")
    print(f"Times  : {len(data.times)}")
    print("✔ Validation finished. If numbers look right – proceed.")

# ------------------------------------------------------------------
def main():
    args = parse_args()
    data = GAData(args.xlsx)

    if args.cmd == "validate":
        validate(data)
        return

    # -------- generate --------------------------------------------
    df = run_ga(data, args.acad_tri, args.pop, args.gen, args.seed)
    json_out = Path(f"timetable_T{args.acad_tri}.json")
    df.to_json(json_out, orient="records", force_ascii=False, indent=2)
    print("✓", json_out)

    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    big_xlsx = out_dir / f"timetable_T{args.acad_tri}.xlsx"
    export_big_table(df, big_xlsx)

    json_out = out_dir / f"timetable_T{args.acad_tri}.json"
    df.to_json(json_out, orient="records", force_ascii=False, indent=2)

    print("✓", big_xlsx)
    print("✓", json_out)

# ------------------------------------------------------------------
if __name__ == "__main__":
    main()
