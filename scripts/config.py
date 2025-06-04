# scripts/config.py
# GA Hyperparameters
import datetime
import os

POPULATION_SIZE = 100     
GENERATIONS = 100         
MUTATION_RATE = 0.15      
CROSSOVER_RATE = 0.85    
EARLY_STOP_GENERATIONS = 10

INPUT_FILE = "inputs/Input_File_Template.xlsx"
def get_output_paths(trimester: int):
    now = datetime.datetime.now()
    year = now.year
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    folder = f"outputs/timetable_T{trimester}_{year}_{timestamp}"
    os.makedirs(folder, exist_ok=True)

    json_path = os.path.join(folder, "schedule.json")
    excel_path = os.path.join(folder, "schedule.xlsx")
    return json_path, excel_path

FIRST_YEAR_TIMESLOTS = [
    f"{hour:02d}:00" for hour in range(8, 14)  
]

UPPER_YEAR_TIMESLOTS = [
    f"{hour:02d}:00" for hour in range(8, 20)  
]

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
