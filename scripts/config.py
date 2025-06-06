# scripts/config.py
# GA Hyperparameters
import datetime
import os

POPULATION_SIZE = 35     
GENERATIONS = 50         
MUTATION_RATE = 0.15      
CROSSOVER_RATE = 0.9    
EARLY_STOP_GENERATIONS = 3

INPUT_FILE = "inputs/Input_File_Template.xlsx"
def get_output_paths(trimester: int):
    """Return JSON and Excel output paths for a given trimester."""
    folder = "outputs"
    os.makedirs(folder, exist_ok=True)

    json_path = os.path.join(folder, f"timetable_T{trimester}.json")
    excel_path = os.path.join(folder, f"timetable_T{trimester}.xlsx")
    return json_path, excel_path

FIRST_YEAR_TIMESLOTS = [
    f"{hour:02d}:00" for hour in range(8, 14)  
]

UPPER_YEAR_TIMESLOTS = [
    f"{hour:02d}:00" for hour in range(8, 20)
]

# Lecture times
ONLINE_LECTURE_TIMES = ["18:00", "19:00", "20:00", "21:00"]

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

GROUP_YEAR_DAYS = {
    1: DAYS,                        # 1st year: Mon–Sat
    2: DAYS[:5],                   # 2nd year: Mon–Fri
    3: ["Mon", "Tue", "Wed", "Fri", "Sat"],  # 3rd year: No Thursday
}

# Year computation
CURRENT_YEAR = 2024

# Rooms to exclude (labs)
EXCLUDED_ROOMS = []

# Session types
SESSION_TYPES = ["Lecture", "Practice", "Lab"]

# Course keywords to exclude
EXCLUDED_COURSES = []
