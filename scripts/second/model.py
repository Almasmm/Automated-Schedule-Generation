"""Простейшие структуры данных для GA."""
from deap import base, creator

# один агрегированный fitness (меньше = лучше, потому что отрицательные штрафы)
creator.create("Fitness", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.Fitness)
