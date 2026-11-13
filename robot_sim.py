"""Run the warehouse robot simulator in a window or on a headless clock."""

import argparse

from warehouse import Warehouse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7, help="random seed (default 7)")
    parser.add_argument("--headless", type=int, metavar="TICKS", help="run for TICKS without a display")
    args = parser.parse_args()
    if args.headless is None:
        from dashboard import run
        run(args.seed)
        return
    if args.headless < 0:
        parser.error("TICKS must be zero or positive")
    world = Warehouse(args.seed)
    for _ in range(args.headless):
        world.step()
    print(f"Tick {world.ticks:,}")
    for robot in world.robots:
        print(f"R{robot.number:02}  deliveries={robot.deliveries}  charges={robot.charges}"
              f"  learning_updates={robot.learner.updates}  battery={robot.battery}")


if __name__ == "__main__":
    main()
