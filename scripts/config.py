# scripts/config.py

# GA Hyperparameters
POPULATION_SIZE = 200     
GENERATIONS = 150         
MUTATION_RATE = 0.12      
CROSSOVER_RATE = 0.88    
EARLY_STOP_GENERATIONS = 25

# Trimester-based paths
INPUT_FILE = "inputs/GA_input.xlsx"
OUTPUT_JSON = "outputs/timetable_T{trimester}/2024.json"
OUTPUT_EXCEL = "outputs/timetable_T{trimester}/2024.xlsx"

# Weekly time slots
FIRST_YEAR_TIMESLOTS = [
    f"{hour:02d}:00" for hour in range(8, 14)  # 08:00 - 13:00
]

UPPER_YEAR_TIMESLOTS = [
    f"{hour:02d}:00" for hour in range(8, 20)  # 08:00 - 19:00
]

# Days by group year
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

GROUP_YEAR_DAYS = {
    1: DAYS,                        # 1st year: Mon–Sat
    2: DAYS[:5],                   # 2nd year: Mon–Fri
    3: ["Mon", "Tue", "Wed", "Fri", "Sat"],  # 3rd year: No Thursday
}

# Year computation
CURRENT_YEAR = 2024

# Rooms to exclude (labs)
EXCLUDED_ROOMS = [
    "C1.2.124", "C1.1.260", "C1.3.122", "C1.3.124",
    "C1.3.327", "C1.3.324"
]

# Session types
SESSION_TYPES = ["Lecture", "Practice", "Lab"]

# Course keywords to exclude
EXCLUDED_COURSES = [
    "Industrial Practice",
    "Diploma Work",
    "Educational Practice",
    "Undergraduate Practice"
]
