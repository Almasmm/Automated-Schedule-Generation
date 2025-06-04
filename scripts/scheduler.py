import random
from copy import deepcopy
from collections import defaultdict
from scripts.chromosome import Chromosome
from scripts.gene import Gene
from scripts.config import (
    POPULATION_SIZE, GENERATIONS, CROSSOVER_RATE, MUTATION_RATE,
    EARLY_STOP_GENERATIONS, FIRST_YEAR_TIMESLOTS,
    UPPER_YEAR_TIMESLOTS, GROUP_YEAR_DAYS
)
import itertools

def get_valid_slots_for_group(group_name):
    year = int(group_name.split("-")[1][:2])
    admission_year = 2000 + year
    study_year = 2024 - admission_year
    days = GROUP_YEAR_DAYS.get(study_year, [])
    if study_year == 1:
        slots = [f"{hour:02d}:00" for hour in range(8, 14)]
    else:
        slots = [f"{hour:02d}:00" for hour in range(8, 20)]
    return days, slots

def get_group_ep_year(group_name):
    ep = group_name.split("-")[0].upper()
    year_num = int(group_name.split("-")[1][:2])
    admission_year = 2000 + year_num
    study_year = 2024 - admission_year
    return ep, study_year

def get_elective_room_count(course_name):
    return course_name.count("/") + 1

def try_assign_batch(groups, course, typ, days, slots, rooms, group_used, room_used, genes, delivery_mode="offline"):
    # Only support offline practices/labs!
    # For online lecture: assign all to Online, allowed times only
    if delivery_mode == "online" and typ.lower() == "lecture":
        online_slots = ["18:00", "19:00", "20:00", "21:00"]
        for g in groups:
            assigned = False
            for day in days:
                for time in online_slots:
                    if time not in group_used[g][day]:
                        genes.append(Gene(
                            group=g,
                            course=course,
                            type=typ,
                            day=day,
                            time=time,
                            room="Online",
                            delivery_mode="online"
                        ))
                        group_used[g][day].add(time)
                        assigned = True
                        break
                if assigned:
                    break
            if not assigned:
                # If all allowed slots are booked, still assign randomly (will be penalized for conflicts)
                day = random.choice(days)
                time = random.choice(online_slots)
                genes.append(Gene(
                    group=g,
                    course=course,
                    type=typ,
                    day=day,
                    time=time,
                    room="Online",
                    delivery_mode="online"
                ))
                group_used[g][day].add(time)
        return True

    # Else: offline as before
    random.shuffle(days)
    random.shuffle(slots)
    random.shuffle(rooms)
    needed_rooms = get_elective_room_count(course)
    for day in days:
        for time in slots:
            if any(time in group_used[g][day] for g in groups):
                continue
            available_rooms = [room for room in rooms if not room_used[room][day][time]]
            if len(available_rooms) >= needed_rooms:
                room_string = ",".join(available_rooms[:needed_rooms])
                for g in groups:
                    genes.append(Gene(
                        group=g,
                        course=course,
                        type=typ,
                        day=day,
                        time=time,
                        room=room_string,
                        delivery_mode="offline"
                    ))
                    group_used[g][day].add(time)
                    group_ep, group_year = get_group_ep_year(g)
                    for assigned_room in available_rooms[:needed_rooms]:
                        room_used[assigned_room][day][time][g] = (course, typ, group_ep, group_year)
                return True

    # Fallback as before...
    if len(groups) == 1:
        g = groups[0]
        # Try ALL day-time combinations, shuffled (KEY FIX)
        day_time_pairs = [(d, t) for d in days for t in slots]
        random.shuffle(day_time_pairs)
        for day, time in day_time_pairs:
            if time in group_used[g][day]:
                continue
            available_rooms = [room for room in rooms if not room_used[room][day][time]]
            if len(available_rooms) >= needed_rooms:
                room_string = ",".join(available_rooms[:needed_rooms])
                genes.append(Gene(
                    group=g,
                    course=course,
                    type=typ,
                    day=day,
                    time=time,
                    room=room_string,
                    delivery_mode="offline"
                ))
                group_used[g][day].add(time)
                group_ep, group_year = get_group_ep_year(g)
                for assigned_room in available_rooms[:needed_rooms]:
                    room_used[assigned_room][day][time][g] = (course, typ, group_ep, group_year)
                return True
        return False
    else:
        for sz in range(len(groups) - 1, 0, -1):
            for subgroups in itertools.combinations(groups, sz):
                assigned = try_assign_batch(list(subgroups), course, typ, days, slots, rooms, group_used, room_used, genes)
                if assigned:
                    rest = [g for g in groups if g not in subgroups]
                    try_assign_batch(rest, course, typ, days, slots, rooms, group_used, room_used, genes)
                    return True
        return False

def generate_initial_population(raw_genes, rooms):
    population = []
    for _ in range(POPULATION_SIZE):
        genes = []
        group_used = defaultdict(lambda: defaultdict(set))
        room_used = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        def get_gene_group(gene):
            if "joint_groups" in gene:
                return gene["joint_groups"][0]
            else:
                return gene["group"]
        raw_genes_sorted = sorted(raw_genes, key=get_gene_group)
        for gene_data in raw_genes_sorted:
            typ = gene_data["type"]
            delivery_mode = gene_data.get("delivery_mode", "offline")
            if "joint_groups" in gene_data:
                groups = gene_data["joint_groups"]
                course = gene_data["course"]
                group = groups[0]
                days, slots = get_valid_slots_for_group(group)
                try_assign_batch(groups, course, typ, days, slots, rooms, group_used, room_used, genes, delivery_mode)
            else:
                group = gene_data["group"]
                course = gene_data["course"]
                days, slots = get_valid_slots_for_group(group)
                random.shuffle(days)
                random.shuffle(slots)
                is_pe = "physical education" in course.lower() or course.strip().upper() == "PE"
                if typ.lower() == "lecture" and delivery_mode == "online":
                    # Schedule online lectures only at allowed time slots
                    online_slots = ["18:00", "19:00", "20:00", "21:00"]
                    assigned = False
                    for day in days:
                        for time in online_slots:
                            if time not in group_used[group][day]:
                                genes.append(Gene(
                                    group=group,
                                    course=course,
                                    type=typ,
                                    day=day,
                                    time=time,
                                    room="Online",
                                    delivery_mode="online"
                                ))
                                group_used[group][day].add(time)
                                assigned = True
                                break
                        if assigned:
                            break
                    if not assigned:
                        day = random.choice(days)
                        time = random.choice(online_slots)
                        genes.append(Gene(
                            group=group,
                            course=course,
                            type=typ,
                            day=day,
                            time=time,
                            room="Online",
                            delivery_mode="online"
                        ))
                        group_used[group][day].add(time)
                    continue
                if is_pe:
                    room = "Gym"
                    candidate_rooms = ["Gym"]
                else:
                    candidate_rooms = [r for r in rooms if r.strip().lower() != "gym"]
                    random.shuffle(candidate_rooms)
                found = False
                elective_room_count = get_elective_room_count(course)
                # Try ALL day-time combinations, shuffled (KEY FIX)
                day_time_pairs = [(d, t) for d in days for t in slots]
                random.shuffle(day_time_pairs)
                for day, time in day_time_pairs:
                    if time in group_used[group][day]:
                        continue
                    if is_pe:
                        genes.append(Gene(
                            group=group,
                            course=course,
                            type=typ,
                            day=day,
                            time=time,
                            room="Gym",
                            delivery_mode="offline"
                        ))
                        group_used[group][day].add(time)
                        room_used["Gym"][day][time][group] = (course, typ, "GYM", 0)
                        found = True
                        break
                    else:
                        available_rooms = [room for room in candidate_rooms if not room_used[room][day][time]]
                        if len(available_rooms) >= elective_room_count:
                            room_string = ",".join(available_rooms[:elective_room_count])
                            genes.append(Gene(
                                group=group,
                                course=course,
                                type=typ,
                                day=day,
                                time=time,
                                room=room_string,
                                delivery_mode="offline"
                            ))
                            group_used[group][day].add(time)
                            ep, study_year_val = get_group_ep_year(group)
                            for assigned_room in available_rooms[:elective_room_count]:
                                room_used[assigned_room][day][time][group] = (course, typ, ep, study_year_val)
                            found = True
                            break
                if not found:
                    # Could not assign—could add to an "unassigned" list or log
                    pass
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

        # mutate only allowed fields for online lectures
        gene = random.choice(child.genes)
        if getattr(gene, "delivery_mode", "offline") == "online" and gene.type.lower() == "lecture":
            attr = random.choice(["time", "day"])
            if attr == "time":
                gene.time = random.choice(["18:00", "19:00", "20:00", "21:00"])
            elif attr == "day":
                days, _ = get_valid_slots_for_group(gene.group)
                gene.day = random.choice(days)
            # Never mutate room for online lectures!
        else:
            group = gene.group
            days, slots = get_valid_slots_for_group(group)
            child.mutate(timeslots=slots, days=days, rooms=rooms)
        child.calculate_fitness()
        next_gen.append(child)
    return next_gen, best

def run_scheduler(raw_genes, rooms, verbose=True):
    population = generate_initial_population(raw_genes, rooms)

    best_fitness = float("inf")
    stagnant = 0
    best_fitness_progress = []  # Track best fitness at each generation

    for generation in range(GENERATIONS):
        population, best = evolve_population(population, rooms)

        if best.fitness < best_fitness:
            best_fitness = best.fitness
            best_schedule = best
            stagnant = 0
        else:
            stagnant += 1

        best_fitness_progress.append(best_fitness)
        if verbose:
            print(f"Generation {generation + 1} | Best Fitness: {best_fitness}")

        if stagnant >= EARLY_STOP_GENERATIONS:
            if verbose:
                print("Stopping early due to no improvement.")
            break
        print("Best fitness progress:", best_fitness_progress)

    return best_schedule, best_fitness_progress
