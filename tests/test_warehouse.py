from random import Random
import unittest

from learning import RouteLearner
from warehouse import CAPACITY, Floor, Warehouse


class WarehouseTests(unittest.TestCase):
    def test_learning_reduces_elapsed_time_on_central_delivery(self):
        floor = Floor()
        policy = RouteLearner()
        rng = Random(7)
        start, goal = (1, 7), (19, 7)
        distances = floor.distances[goal]

        def trip(training):
            cell, elapsed = start, 0
            while cell != goal and elapsed < 500:
                move = policy.choose(cell, goal, floor.neighbors[cell], distances,
                                     rng, 0.03 if training else 0.0)
                duration = floor.travel_time(move)
                if training:
                    policy.learn(cell, goal, move, duration, floor.neighbors[move], distances)
                elapsed += duration
                cell = move
            self.assertEqual(cell, goal)
            return elapsed

        self.assertEqual(trip(False), 38)
        for _ in range(40):
            trip(True)
        self.assertEqual(trip(False), 20)

    def test_fleet_completes_jobs_and_recharges(self):
        world = Warehouse(seed=7)
        for _ in range(1500):
            previous = [(r.position, r.carrying, r.deliveries) for r in world.robots]
            world.step()
            self.assertEqual(len({r.position for r in world.robots}), 3)
            for robot, (old_position, loaded, deliveries) in zip(world.robots, previous):
                if robot.position != old_position:
                    self.assertIn(robot.position, world.floor.neighbors[old_position])
                self.assertLessEqual(robot.battery, CAPACITY)
                self.assertGreaterEqual(robot.battery, world.floor.distances[robot.charger][robot.position])
                if robot.carrying != loaded:
                    stations = world.floor.pickups if robot.carrying else world.floor.dropoffs
                    self.assertIn(robot.position, stations)
                    self.assertEqual(robot.deliveries, deliveries + int(loaded))
        for robot in world.robots:
            self.assertGreater(robot.deliveries, 0)
            self.assertGreater(robot.charges, 0)
            self.assertGreater(robot.learner.updates, 0)
