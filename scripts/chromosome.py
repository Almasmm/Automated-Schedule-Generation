# scripts/chromosome.py

import random
from typing import List
from copy import deepcopy
from scripts.gene import Gene
from scripts.evaluator import evaluate_fitness

class Chromosome:
    def __init__(self, genes: List[Gene]):
        self.genes = genes  # list of Gene objects
        self.fitness = None

    # Evaluate fitness score using constraint logic
    def calculate_fitness(self):
        self.fitness = evaluate_fitness(self.genes)
        return self.fitness

    # Randomly mutate a gene's time, day, or room
    def mutate(self, timeslots, days, rooms):
        gene = random.choice(self.genes)
        if "physical education" in gene.course.lower() or gene.course.strip().upper() == "PE":
            attr = random.choice(["time", "day"])  # can't change room
        else:
            attr = random.choice(["time", "day", "room"])
        # Choose which attribute to mutate
        attr = random.choice(["time", "day", "room"])
        if attr == "time":
            gene.time = random.choice(timeslots)
        elif attr == "day":
            gene.day = random.choice(days)
        elif attr == "room":
            gene.room = random.choice(rooms)

    # One-point crossover to create a new offspring
    def crossover(self, other: 'Chromosome') -> 'Chromosome':
        point = random.randint(1, len(self.genes) - 1)
        child_genes = self.genes[:point] + other.genes[point:]
        return Chromosome(deepcopy(child_genes))

    def __str__(self):
        sorted_genes = sorted(self.genes, key=lambda g: (g.group, g.day, g.time))
        return "\n".join(str(g) for g in sorted_genes)

    # Convert schedule to JSON-serializable format
    def to_json(self):
        grouped = {}
        for gene in self.genes:
            if gene.group not in grouped:
                grouped[gene.group] = []
            grouped[gene.group].append(gene.to_dict())

        for group in grouped:
            grouped[group] = sorted(grouped[group], key=lambda x: (x["day"], x["time"]))

        return grouped
