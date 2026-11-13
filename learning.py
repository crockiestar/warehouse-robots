"""Tabular Q-learning for trips with actions of different durations."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from random import Random

Cell = tuple[int, int]
GAMMA = 0.96
ARRIVAL_BONUS = 12.0


def travel_reward(ticks: int, arrived: bool) -> float:
    """A cost of one per tick and a bonus on the last tick of a completed trip."""
    time_cost = (1 - GAMMA**ticks) / (1 - GAMMA)
    return -time_cost + (GAMMA ** (ticks - 1) * ARRIVAL_BONUS if arrived else 0.0)


@dataclass
class RouteLearner:
    # An untried move is valued as if the remaining route were all ordinary floor.
    values: dict[tuple[Cell, Cell, Cell], float] = field(default_factory=dict)
    updates: int = 0
    last_error: float = 0.0

    def value(self, position: Cell, destination: Cell, move: Cell, remaining: int) -> float:
        key = (destination, position, move)
        if key in self.values:
            return self.values[key]
        return travel_reward(1 + remaining, arrived=True)

    def choose(self, position: Cell, destination: Cell, moves: Sequence[Cell],
               distances: dict[Cell, int], rng: Random, exploration: float) -> Cell:
        if rng.random() < exploration:
            return rng.choice(moves)
        scores = [self.value(position, destination, move, distances[move]) for move in moves]
        best = max(scores)
        return rng.choice([move for move, score in zip(moves, scores) if score == best])

    def learn(self, position: Cell, destination: Cell, move: Cell, ticks: int,
              next_moves: Sequence[Cell], distances: dict[Cell, int]) -> None:
        arrived = move == destination
        target = travel_reward(ticks, arrived)
        if not arrived:
            future = max(self.value(move, destination, step, distances[step]) for step in next_moves)
            target += GAMMA**ticks * future
        old = self.value(position, destination, move, distances[move])
        self.last_error = target - old
        self.values[destination, position, move] = old + 0.45 * self.last_error
        self.updates += 1
