# scripts/scheduler.py

import random
from copy import deepcopy
from scripts.chromosome import Chromosome
from scripts.gene import Gene
from scripts.config import (
    POPULATION_SIZE, GENERATIONS, CROSSOVER_RATE, MUTATION_RATE,
    EARLY_STOP_GENERATIONS, FIRST_YEAR_TIMESLOTS,
    UPPER_YEAR_TIMESLOTS, GROUP_YEAR_DAYS
)

def get_valid_slots_for_group(group_name):
    year = int(group_name.split("-")[1][:2])
    admission_year = 2000 + year
    study_year = 2024 - admission_year
    days = GROUP_YEAR_DAYS.get(study_year, [])
    if study_year == 1:
        slots = [f"{hour:02d}:00" for hour in range(8, 14)]  # 08:00–13:00 only for first-year
    else:
        slots = [f"{hour:02d}:00" for hour in range(8, 20)]  # 08:00–19:00 for others
    return days, slots

#def generate_initial_population(raw_genes, rooms):
    population = []
    from scripts.gene import Gene
    import random
    from collections import defaultdict

    for _ in range(POPULATION_SIZE):
        assigned = defaultdict(lambda: defaultdict(set))  # group[day] = set(times)
        assigned_room = defaultdict(lambda: defaultdict(set))  # room[day] = set(times)
        genes = []
        for gene_data in raw_genes:
            group = gene_data["group"]
            course = gene_data["course"]
            typ = gene_data["type"]
            days, slots = get_valid_slots_for_group(group)

            random.shuffle(days)
            random.shuffle(slots)
            random.shuffle(rooms)
            # Find the first available slot+room with no conflicts for group and room
            found = False
            for day in days:
                for time in slots:
                    if time in assigned[group][day]:
                        continue
                    for room in rooms:
                        if time in assigned_room[room][day]:
                            continue
                        # Assign here
                        genes.append(Gene(
                            group=group,
                            course=course,
                            type=typ,
                            day=day,
                            time=time,
                            room=room
                        ))
                        assigned[group][day].add(time)
                        assigned_room[room][day].add(time)
                        found = True
                        break
                    if found:
                        break
                if found:
                    break
            # If not found, assign randomly (last resort, but now rare)
            if not found:
                day = random.choice(days)
                time = random.choice(slots)
                room = random.choice(rooms)
                genes.append(Gene(
                    group=group,
                    course=course,
                    type=typ,
                    day=day,
                    time=time,
                    room=room
                ))
                assigned[group][day].add(time)
                assigned_room[room][day].add(time)

        chromosome = Chromosome(genes)
        chromosome.calculate_fitness()
        population.append(chromosome)
    return population
def generate_initial_population(raw_genes, rooms):
    from scripts.gene import Gene
    from scripts.chromosome import Chromosome
    import random
    from collections import defaultdict

    population = []

    for _ in range(POPULATION_SIZE):
        genes = []
        # Track which slots/rooms are already used to avoid conflicts
        group_used = defaultdict(lambda: defaultdict(set))   # group_used[group][day] = set(times)
        room_used = defaultdict(lambda: defaultdict(set))    # room_used[room][day] = set(times)
        
        for gene_data in raw_genes:
            group = gene_data["group"]
            course = gene_data["course"]
            typ = gene_data["type"]
            days, slots = get_valid_slots_for_group(group)

            random.shuffle(days)
            random.shuffle(slots)
            # Check if this is PE
            is_pe = "physical education" in course.lower() or course.strip().upper() == "PE"
            if is_pe:
                room = "Gym"
                candidate_rooms = ["Gym"]
            else:
                # Only pick from non-Gym rooms for non-PE
                candidate_rooms = [r for r in rooms if r.strip().lower() != "gym"]
                random.shuffle(candidate_rooms)
            
            found = False
            for day in days:
                for time in slots:
                    if time in group_used[group][day]:
                        continue
                    if is_pe:
                        # PE: Any number of groups can be in Gym at same time, so skip room check!
                        genes.append(Gene(
                            group=group,
                            course=course,
                            type=typ,
                            day=day,
                            time=time,
                            room="Gym"
                        ))
                        group_used[group][day].add(time)
                        found = True
                        break
                    else:
                        for room in candidate_rooms:
                            if time not in room_used[room][day]:
                                genes.append(Gene(
                                    group=group,
                                    course=course,
                                    type=typ,
                                    day=day,
                                    time=time,
                                    room=room
                                ))
                                group_used[group][day].add(time)
                                room_used[room][day].add(time)
                                found = True
                                break
                        if found:
                            break
                if found:
                    break

            if not found:
                # Fallback: assign randomly (should be rare)
                day = random.choice(days)
                time = random.choice(slots)
                if is_pe:
                    room = "Gym"
                else:
                    room = random.choice(candidate_rooms)
                genes.append(Gene(
                    group=group,
                    course=course,
                    type=typ,
                    day=day,
                    time=time,
                    room=room
                ))
                group_used[group][day].add(time)
                if not is_pe:
                    room_used[room][day].add(time)

        chromosome = Chromosome(genes)
        chromosome.calculate_fitness()
        population.append(chromosome)
    return population

def select_parents(population):
    sorted_pop = sorted(population, key=lambda x: x.fitness)
    return sorted_pop[:2]

def evolve_population(population, rooms):
    next_gen = []
    best = min(population, key=lambda x: x.fitness)

    while len(next_gen) < POPULATION_SIZE:
        parent1, parent2 = random.sample(population, 2)
        if random.random() < CROSSOVER_RATE:
            child = parent1.crossover(parent2)
        else:
            child = deepcopy(random.choice([parent1, parent2]))

        if random.random() < MUTATION_RATE:
            group = random.choice(child.genes).group
            days, slots = get_valid_slots_for_group(group)
            child.mutate(timeslots=slots, days=days, rooms=rooms)

        child.calculate_fitness()
        next_gen.append(child)

    return next_gen, best

def run_scheduler(raw_genes, rooms, verbose=True):
    population = generate_initial_population(raw_genes, rooms)

    best_fitness = float("inf")
    stagnant = 0

    for generation in range(GENERATIONS):
        population, best = evolve_population(population, rooms)

        if best.fitness < best_fitness:
            best_fitness = best.fitness
            best_schedule = best
            stagnant = 0
        else:
            stagnant += 1

        if verbose:
            print(f"Generation {generation + 1} | Best Fitness: {best_fitness}")

        if stagnant >= EARLY_STOP_GENERATIONS:
            if verbose:
                print("Stopping early due to no improvement.")
            break

    return best_schedule
