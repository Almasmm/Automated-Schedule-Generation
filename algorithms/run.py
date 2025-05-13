# run.py --------------------------------------------------------------

"""CLI entry‑point."""
import argparse, json
from pathlib import Path
from loader import GAData
from ga_engine import run_ga
from exporter import export

p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd", required=True)

v = sub.add_parser("validate"); v.add_argument("--xlsx", type=Path, required=True)
r = sub.add_parser("run"); r.add_argument("--xlsx", type=Path, required=True)
r.add_argument("--trimester", type=int, required=True)
r.add_argument("--pop", type=int, default=60); r.add_argument("--gen", type=int, default=120)

args = p.parse_args()

data = GAData(args.xlsx)
if args.cmd == "validate":
    print("Courses:", len(data.courses))
    print("Groups :", len(data.groups))
    print("Rooms  :", len(data.rooms))
    print("Times  :", len(data.times))
else:
    sched = run_ga(data, args.trimester, args.pop, args.gen)
    if sched:
        json_path = Path(f"timetable_T{args.trimester}.json")
        json_path.write_text(json.dumps(sched, ensure_ascii=False, indent=2), encoding="utf-8")
        print("✓ JSON saved to", json_path)
        export(sched, data, args.trimester)
