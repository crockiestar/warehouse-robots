"""Warehouse floor, robot dispatch, and deterministic simulation clock."""

from collections import deque
from dataclasses import dataclass, field
from random import Random

from learning import Cell, RouteLearner


LAYOUT = (
    ".....................",
    ".P..####.....####..D.",
    "....####.....####....",
    ".........~~~.........",
    "....####.~~~.####....",
    ".C..####.~~~.####....",
    ".....................",
    ".P.......~~~~~.....D.",
    ".....................",
    ".C..####.~~~.####....",
    "....####.~~~.####....",
    ".........~~~.........",
    "....####.....####....",
    ".P..####.....####..D.",
    ".C...................",
)
CAPACITY = 80
CHARGE_RATE = 8
CHARGE_RESERVE = 8
SLOW_TICKS = 5


class Floor:
    def __init__(self):
        self.width = len(LAYOUT[0])
        self.height = len(LAYOUT)
        self.tiles = {(x, y): tile for y, row in enumerate(LAYOUT)
                      for x, tile in enumerate(row) if tile != "#"}
        self.pickups = self.stations("P")
        self.dropoffs = self.stations("D")
        self.chargers = self.stations("C")
        self.neighbors = {}
        for x, y in self.tiles:
            adjacent = ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
            self.neighbors[x, y] = tuple(cell for cell in adjacent if cell in self.tiles)
        self.distances = {station: self._hops_to(station)
                          for station in self.pickups + self.dropoffs + self.chargers}

    def stations(self, symbol: str) -> tuple[Cell, ...]:
        return tuple(cell for cell, tile in self.tiles.items() if tile == symbol)

    def _hops_to(self, station: Cell) -> dict[Cell, int]:
        distances = {station: 0}
        queue = deque([station])
        while queue:
            cell = queue.popleft()
            for neighbor in self.neighbors[cell]:
                if neighbor not in distances:
                    distances[neighbor] = distances[cell] + 1
                    queue.append(neighbor)
        return distances

    def travel_time(self, cell: Cell) -> int:
        return SLOW_TICKS if self.tiles[cell] == "~" else 1


@dataclass
class Robot:
    number: int
    position: Cell
    charger: Cell
    pickup: Cell
    dropoff: Cell
    learner: RouteLearner = field(default_factory=RouteLearner)
    battery: int = CAPACITY
    carrying: bool = False
    returning: bool = False
    # A move reserves the arrival tile immediately. Service occurs on its last tick.
    travel_left: int = 0
    move_started: int = 0
    deliveries: int = 0
    charges: int = 0
    last_trip_ticks: int = 0
    loaded_at: int = 0
    trail: deque[Cell] = field(default_factory=lambda: deque(maxlen=24))

    @property
    def destination(self) -> Cell:
        if self.returning:
            return self.charger
        return self.dropoff if self.carrying else self.pickup

    @property
    def task(self) -> str:
        if self.returning:
            return "Charging" if self.position == self.charger and not self.travel_left else "To charger"
        return "Delivering" if self.carrying else "Collecting"


class Warehouse:
    def __init__(self, seed: int = 7):
        self.rng = Random(seed)
        self.floor = Floor()
        self.ticks = 0
        self.robots = [
            Robot(i, dock, dock, self.rng.choice(self.floor.pickups), self.rng.choice(self.floor.dropoffs))
            for i, dock in enumerate(self.floor.chargers, start=1)
        ]

    def step(self) -> None:
        self.ticks += 1
        occupied = {robot.position for robot in self.robots}
        order = self.robots.copy()
        self.rng.shuffle(order)
        for robot in order:
            if robot.travel_left:
                robot.travel_left -= 1
                if robot.travel_left == 0:
                    self._finish_move(robot)
                continue
            if robot.returning and robot.position == robot.charger:
                robot.battery = min(CAPACITY, robot.battery + CHARGE_RATE)
                if robot.battery == CAPACITY:
                    robot.returning = False
                    robot.charges += 1
                continue
            self._drive(robot, occupied)

    def _drive(self, robot: Robot, occupied: set[Cell]) -> None:
        home_distance = self.floor.distances[robot.charger]
        if robot.battery <= home_distance[robot.position] + CHARGE_RESERVE:
            robot.returning = True
            if robot.position == robot.charger:
                return
        position = robot.position
        moves = [cell for cell in self.floor.neighbors[position]
                 if cell not in occupied and home_distance[cell] <= robot.battery - 1]
        if not moves:
            return

        destination = robot.destination
        distances = self.floor.distances[destination]
        exploration = 0.015 + 0.10 / (1 + robot.learner.updates / 200)
        move = robot.learner.choose(position, destination, moves, distances, self.rng, exploration)
        duration = self.floor.travel_time(move)
        occupied.remove(position)
        occupied.add(move)
        robot.trail.append(position)
        robot.position = move
        robot.battery -= 1
        robot.move_started = self.ticks
        robot.travel_left = duration - 1
        if robot.travel_left == 0:
            self._finish_move(robot)

    def _finish_move(self, robot: Robot) -> None:
        cell, destination = robot.position, robot.destination
        elapsed = self.ticks - robot.move_started + 1
        robot.learner.learn(robot.trail[-1], destination, cell, elapsed,
                            self.floor.neighbors[cell], self.floor.distances[destination])
        if robot.returning or cell != destination:
            return
        if robot.carrying:
            robot.deliveries += 1
            robot.last_trip_ticks = self.ticks - robot.loaded_at
            robot.pickup = self.rng.choice(self.floor.pickups)
            robot.dropoff = self.rng.choice(self.floor.dropoffs)
        else:
            robot.loaded_at = self.ticks
        robot.carrying = not robot.carrying
