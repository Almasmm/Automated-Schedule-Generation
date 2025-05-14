"""Single point for all numerical GA settings"""

POPULATION = 120
GENERATIONS = 200
MUTATION_RATE = 0.15
CROSSOVER_RATE = 0.9

# Penalty weights (minus = want to minimise)

WEIGHTS = {
    "HARD_CLASH": -1_000,
    "CAPACITY_OVER": -400,
    "LECTURE_AFTER_PRACT": -600,
    "IDLE_GAP": -8,
}
