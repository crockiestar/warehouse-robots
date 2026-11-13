# Warehouse robots

Three mobile robots collect parcels, deliver them to dispatch stations, and return
to their docks to charge. Each robot learns its own routing policy as it works.
On the central delivery run, the straight path crosses five slow tiles. The robot
can save time by moving one row over and taking a longer route through clear floor.

## Run

With Python 3.12, install Pygame and launch the dashboard from this directory.

```sh
python -m pip install -r requirements.txt
python robot_sim.py
```

Press **Space** to pause or resume, **R** to restart from the same seed, and **D**
to see the selected robot's recent route and latest learning error. Click a robot
or its fleet row to inspect it. The outline on the floor marks its destination.
Drag the speed slider to change the number of simulation ticks per second.
**Esc** closes the window.

For a reproducible run without a display, use the headless entry point. This mode
uses only the Python standard library.

```sh
python robot_sim.py --headless 6000 --seed 7
python -m unittest discover -s tests
```

## How the robots learn

The dispatcher assigns a pickup and a delivery station. Each robot chooses among
adjacent, unoccupied floor tiles. Each move uses one unit of battery. A normal
tile takes one tick to enter and a slow tile takes five. The fleet reserves cells
as robots move so two robots cannot occupy the same tile.

Each robot keeps a Q-table keyed by destination, current tile, and next tile.
Initially it estimates trips using the number of walkable steps to the station.
After a move finishes, the robot updates its estimate using the time it actually
spent, a reward for arrival, and the estimated value of its next move. A small
fraction of exploratory moves lets it try alternate routes. Running longer trains
the current fleet. Restarting clears the learned values.

Battery management is a dispatcher rule. A robot diverts to its own charger
when its battery approaches the minimum needed to get home. A parcel stays on
board during the detour. The inspector's last delivery time includes any charging
or traffic delays between pickup and dispatch.

## Source

- `warehouse.py` contains the floor, dispatch rules, and simulation clock.
- `learning.py` contains the route policy and duration-aware Q update.
- `dashboard.py` draws the floor and handles keyboard and mouse input.
- `robot_sim.py` launches the interactive or headless runner.
