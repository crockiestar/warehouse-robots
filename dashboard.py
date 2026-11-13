"""Interactive Pygame view of the warehouse and its learning controllers."""

import pygame

from warehouse import CAPACITY, Warehouse

CELL = 34
MAP_X, MAP_Y = 24, 102
PANEL_X, PANEL_W = 762, 300
SIZE = (1086, 696)
PAPER, INK, MUTED = "#f4f4ed", "#152b31", "#576d70"
LINE, FLOOR, GRID = "#c5ceca", "#edf1ec", "#dbe4de"
SHELF, SLOW, AMBER = "#344d56", "#f5e6c5", "#a5631a"
TEAL, BLUE, PLUM = "#087863", "#2669ad", "#875187"
COLORS = (BLUE, TEAL, PLUM)


def tile_rect(cell):
    x, y = cell
    return pygame.Rect(MAP_X + x * CELL, MAP_Y + y * CELL, CELL, CELL)


def meter(surface, rect, fraction, color, background=LINE):
    pygame.draw.rect(surface, background, rect, border_radius=2)
    width = round(rect.width * max(0, min(1, fraction)))
    if width:
        pygame.draw.rect(surface, color, (rect.x, rect.y, width, rect.height), border_radius=2)


class Slider:
    """Drag the speed control, or click anywhere along its track."""
    def __init__(self, x, y, width):
        self.track = pygame.Rect(x, y, width, 4)
        self.value = 8
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.dragging = self.track.inflate(16, 26).collidepoint(event.pos)
        if self.dragging and event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
            fraction = max(0, min(1, (event.pos[0] - self.track.left) / self.track.width))
            self.value = 1 + round(fraction * 39)

    def draw(self, surface):
        fraction = (self.value - 1) / 39
        meter(surface, self.track, fraction, TEAL)
        center = (self.track.left + round(self.track.width * fraction), self.track.centery)
        pygame.draw.circle(surface, TEAL, center, 8)
        pygame.draw.circle(surface, PAPER, center, 3)


class Dashboard:
    def __init__(self, screen, seed):
        self.screen = screen
        self.seed = seed
        self.world = Warehouse(seed)
        self.selected = 0
        self.paused = False
        self.debug = False
        self.pending_ticks = 0.0
        self.speed = Slider(PANEL_X + 1, 621, PANEL_W - 2)
        self.fonts = {
            "title": pygame.font.SysFont("Segoe UI,Arial", 31, bold=True),
            "heading": pygame.font.SysFont("Segoe UI,Arial", 20, bold=True),
            "body": pygame.font.SysFont("Segoe UI,Arial", 16),
            "mono": pygame.font.SysFont("Consolas,monospace", 16),
            "small": pygame.font.SysFont("Consolas,monospace", 13),
        }
        self.base = self._draw_floor()

    def text(self, label, pos, style="body", color=INK, right=False, surface=None):
        image = self.fonts[style].render(str(label), True, color)
        box = image.get_rect()
        if right:
            box.topright = pos
        else:
            box.topleft = pos
        (self.screen if surface is None else surface).blit(image, box)

    def _draw_floor(self):
        base = pygame.Surface(SIZE)
        base.fill(PAPER)
        floor = self.world.floor
        for y in range(floor.height):
            for x in range(floor.width):
                box = tile_rect((x, y))
                tile = floor.tiles.get((x, y), "#")
                bg = {"#": SHELF, "~": SLOW, "P": "#cce6df", "D": "#d8e4f0", "C": "#ebdfeb"}.get(tile, FLOOR)
                pygame.draw.rect(base, GRID, box)
                pygame.draw.rect(base, bg, (box.x, box.y, CELL - 1, CELL - 1))
                if tile == "#":
                    for offset in (10, 22):
                        pygame.draw.line(base, "#48606b", (box.x + 5, box.y + offset),
                                         (box.right - 6, box.y + offset), 2)
                elif tile == "~":
                    for offset in (6, 15, 24):
                        pygame.draw.line(base, "#d4b78c", (box.x + offset, box.centery + 4),
                                         (box.x + offset + 4, box.centery - 4), 2)
                elif tile in ("P", "D", "C"):
                    self.text(tile, (box.x + 11, box.y + 7), "mono", INK, surface=base)
        return base

    def handle(self, event):
        self.speed.handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
            elif event.key == pygame.K_d:
                self.debug = not self.debug
            elif event.key == pygame.K_r:
                self.world = Warehouse(self.seed)
                self.pending_ticks = 0.0
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, robot in enumerate(self.world.robots):
                if tile_rect(robot.position).collidepoint(event.pos) or self.fleet_row(index).collidepoint(event.pos):
                    self.selected = index

    def advance(self, seconds):
        if self.paused:
            return
        self.pending_ticks += min(seconds, 0.25) * self.speed.value
        steps = int(self.pending_ticks)
        for _ in range(steps):
            self.world.step()
        self.pending_ticks -= steps

    def fleet_row(self, index):
        return pygame.Rect(PANEL_X, 131 + index * 49, PANEL_W, 42)

    def _draw_robots(self):
        selected = self.world.robots[self.selected]
        accent = COLORS[self.selected]
        if self.debug and selected.trail:
            points = [tile_rect(p).center for p in selected.trail]
            pygame.draw.lines(self.screen, accent, False, points + [tile_rect(selected.position).center], 2)
        goal = tile_rect(selected.destination).inflate(-4, -4)
        pygame.draw.rect(self.screen, accent, goal, 2, border_radius=4)
        for index, robot in enumerate(self.world.robots):
            box = tile_rect(robot.position)
            if index == self.selected:
                pygame.draw.rect(self.screen, INK, box.inflate(-2, -2), 2, border_radius=6)
            chassis = box.inflate(-10, -10)
            pygame.draw.rect(self.screen, INK, (chassis.x - 2, chassis.y + 5, chassis.w + 4, chassis.h - 9), border_radius=3)
            pygame.draw.rect(self.screen, COLORS[index], chassis, border_radius=4)
            self.text(robot.number, (chassis.x + 8, chassis.y + 2), "mono", "#ffffff")
            if robot.carrying:
                pygame.draw.rect(self.screen, "#ffd888", (chassis.right - 6, chassis.bottom - 7, 7, 7))

    def _panel(self):
        self.text("Fleet", (PANEL_X, 99), "heading")
        for index, robot in enumerate(self.world.robots):
            row = self.fleet_row(index)
            active = index == self.selected
            pygame.draw.rect(self.screen, "#e0e7e2" if active else "#eaeee8", row, border_radius=4)
            pygame.draw.rect(self.screen, COLORS[index], (row.x, row.y + 6, 4, row.height - 12))
            self.text(f"R{robot.number:02}", (row.x + 12, row.y + 11), "mono")
            self.text(robot.task, (row.x + 70, row.y + 9))
            self.text(f"{100 * robot.battery / CAPACITY:.0f}%", (row.right - 12, row.y + 11), "mono", right=True)

        robot = self.world.robots[self.selected]
        pygame.draw.line(self.screen, LINE, (PANEL_X, 297), (PANEL_X + PANEL_W, 297))
        self.text(f"Robot {robot.number:02}", (PANEL_X, 318), "heading")
        percent = robot.battery / CAPACITY
        self.text("Battery", (PANEL_X, 359))
        self.text(f"{robot.battery} / {CAPACITY}", (PANEL_X + PANEL_W, 359), "mono", right=True)
        meter(self.screen, pygame.Rect(PANEL_X, 386, PANEL_W, 6), percent, TEAL if percent > 0.25 else AMBER)
        x, y = robot.destination
        metrics = [
            ("Destination", f"{x:02}, {y:02}"),
            ("Parcels delivered", str(robot.deliveries)),
            ("Last delivery", f"{robot.last_trip_ticks} ticks" if robot.deliveries else "—"),
            ("Q-learning updates", f"{robot.learner.updates:,}"),
        ]
        if self.debug:
            metrics.append(("Last TD error", f"{robot.learner.last_error:+.3f}"))
        for index, (label, value) in enumerate(metrics):
            y = 408 + index * 30
            self.text(label, (PANEL_X, y), color=MUTED)
            self.text(value, (PANEL_X + PANEL_W, y), "mono", right=True)
        self.text("Speed", (PANEL_X, 579), "heading")
        self.text(f"{self.speed.value} ticks/s", (PANEL_X + PANEL_W, 583), "mono", right=True)
        self.speed.draw(self.screen)

    def draw(self):
        self.screen.blit(self.base, (0, 0))
        self.text("Warehouse robots", (24, 17), "title")
        self.text("Floor plan", (24, 72), "body")
        total = sum(robot.deliveries for robot in self.world.robots)
        self.text(f"{total:,} delivered", (PANEL_X + PANEL_W, 25), "heading", right=True)
        status = "Paused" if self.paused else "Running"
        self.text(f"{status}   /   Tick {self.world.ticks:,}", (PANEL_X + PANEL_W, 60), "mono", MUTED, right=True)
        self._draw_robots()
        self._panel()
        for x, label, color in ((24, "P  Pickup", TEAL), (161, "D  Dispatch", BLUE),
                                (332, "C  Charger", PLUM), (490, "///  Slow aisle", AMBER)):
            self.text(label, (x, 623), "mono", color)
        pygame.draw.line(self.screen, LINE, (24, 656), (SIZE[0] - 24, 656))
        self.text("Space  pause/resume      R  restart      D  diagnostics      Click a robot to inspect",
                  (24, 668), "small", MUTED)


def run(seed):
    pygame.init()
    try:
        screen = pygame.display.set_mode(SIZE)
        pygame.display.set_caption("Warehouse robots")
        dashboard = Dashboard(screen, seed)
        clock = pygame.time.Clock()
        while True:
            seconds = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    return
                dashboard.handle(event)
            dashboard.advance(seconds)
            dashboard.draw()
            pygame.display.flip()
    finally:
        pygame.quit()
