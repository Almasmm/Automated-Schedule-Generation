# scripts/exporter.py

import json
import pandas as pd
from pathlib import Path

def is_physical_education(course_name):
    name = str(course_name).lower().strip()
    return "physical education" in name or name == "pe"

def export_schedule(chromosome, json_path, excel_path):
    # For all genes, set room to Gym if course is PE/Physical Education
    for gene in chromosome.genes:
        if is_physical_education(gene.course):
            gene.room = "Gym"
    export_to_json(chromosome, json_path)
    export_to_excel(chromosome, excel_path)

def export_to_json(chromosome, path):
    # Force Gym for PE in the JSON as well
    data = chromosome.to_json()
    for group_name in data:
        for entry in data[group_name]:
            course_name = entry.get("Course", "")
            if is_physical_education(course_name):
                entry["Room"] = "Gym"
            if "Instructor" in entry:
                del entry["Instructor"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def export_to_excel(chromosome, path):
    rows = []
    for gene in sorted(chromosome.genes, key=lambda g: (g.group, g.day, g.time)):
        room = "Gym" if is_physical_education(gene.course) else gene.room
        rows.append({
            "Group": gene.group,
            "Day": gene.day,
            "Time": gene.time,
            "Course": gene.course,
            "Type": gene.type,
            "Room": room
        })

    df = pd.DataFrame(rows)
    writer = pd.ExcelWriter(path, engine="openpyxl")

    DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    for group, group_df in df.groupby("Group"):
        group_df["Day"] = pd.Categorical(group_df["Day"], categories=DAY_ORDER, ordered=True)
        sheet_df = group_df.sort_values(by=["Day", "Time"])
        sheet_df.drop(columns=["Group"], inplace=True)
        sheet_name = group[:31]  # Excel sheet name limit
        sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    writer.close()
