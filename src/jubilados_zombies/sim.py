"""Reglas de Jubilados Zombies, sin Panda3D.

El club de jubilados está rodeado. El jugador se mueve por el patio, dispara
en primera persona y aguanta oleadas de ex-socios. Este módulo concentra
colisiones, armas, IA, oleadas y puntaje para poder probarlo sin ventana.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

Vec2 = tuple[float, float]
Rect = tuple[float, float, float, float]

PLAYER_RADIUS = 0.38
PLAYER_SPEED = 3.9
PLAYER_EYE = 1.62
PLAYER_MAX_HEALTH = 100.0

ARENA_HALF_X = 14.6
ARENA_HALF_Y = 18.6

# Obstáculos del patio: (x0, y0, x1, y1). Todos bloquean movimiento y tiros.
OBSTACLES: tuple[Rect, ...] = (
    # Muro perimetral del club.
    (-15.2, -19.2, 15.2, -18.6),
    (-15.2, 18.6, 15.2, 19.2),
    (-15.2, -19.2, -14.6, 19.2),
    (14.6, -19.2, 15.2, 19.2),
    # Fuente al oeste del centro.
    (-8.6, -8.2, -4.8, -5.8),
    # Kiosco de bebidas.
    (2.4, 1.8, 6.6, 4.4),
    # Canteros con setos.
    (-11.2, -3.8, -9.0, -1.6),
    (9.0, -3.8, 11.2, -1.6),
    (-11.2, 8.8, -9.0, 11.0),
    (9.0, 8.8, 11.2, 11.0),
    # Biombos bajos y columnas.
    (-7.8, 4.8, -4.2, 5.4),
    (4.2, 8.4, 7.8, 9.0),
    (-10.8, -12.8, -10.0, -12.0),
    (10.0, -12.8, 10.8, -12.0),
    # Escenario / barra del norte.
    (-3.2, 15.6, 3.2, 17.2),
)

SPAWN_POINTS: tuple[Vec2, ...] = (
    (-12.6, -16.4),
    (12.6, -16.4),
    (-12.6, 16.2),
    (12.6, 16.2),
    (-12.9, 2.0),
    (12.9, 2.0),
    (-8.2, 13.4),
    (8.2, 13.4),
    (-6.2, -1.2),
    (6.2, -2.2),
    (0.0, 6.2),
    (0.0, -2.6),
    (-4.8, -11.4),
    (7.0, -10.6),
)

PLAYER_START: Vec2 = (0.0, -16.0)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def wrap_degrees(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def heading_vector(heading: float) -> Vec2:
    """Dirección en el piso para un rumbo Panda (+ grados gira a la izquierda)."""
    radians = math.radians(heading)
    return (-math.sin(radians), math.cos(radians))


def angle_to(origin: Vec2, target: Vec2) -> float:
    """Rumbo desde ``origin`` hasta ``target`` con la convención del juego."""
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    return math.degrees(math.atan2(-dx, dy))


# -- armas -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WeaponSpec:
    key: str
    name: str
    short: str
    magazine: int
    damage: float
    pellets: int
    spread: float
    range: float
    interval: float
    reload_time: float
    kick: float
    falloff: float
    tone: int


WEAPONS: tuple[WeaponSpec, ...] = (
    WeaponSpec(
        key="revolver",
        name="REVÓLVER",
        short="REV",
        magazine=6,
        damage=34.0,
        pellets=1,
        spread=1.2,
        range=30.0,
        interval=0.34,
        reload_time=1.10,
        kick=1.0,
        falloff=0.35,
        tone=300,
    ),
    WeaponSpec(
        key="escopeta",
        name="ESCOPETA",
        short="ESC",
        magazine=5,
        damage=16.0,
        pellets=7,
        spread=6.5,
        range=13.0,
        interval=0.78,
        reload_time=1.55,
        kick=2.2,
        falloff=0.62,
        tone=170,
    ),
    WeaponSpec(
        key="subfusil",
        name="SUBFUSIL",
        short="SMG",
        magazine=30,
        damage=9.0,
        pellets=1,
        spread=3.2,
        range=28.0,
        interval=0.095,
        reload_time=1.70,
        kick=0.55,
        falloff=0.50,
        tone=430,
    ),
)
WEAPON_BY_KEY = {spec.key: spec for spec in WEAPONS}


@dataclass(slots=True)
class WeaponState:
    ammo: int
    reload_timer: float = 0.0
    cooldown: float = 0.0
    dry: bool = False


# -- zombis ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ZombieSpec:
    kind: str
    health: float
    speed: float
    damage: float
    attack_interval: float
    radius: float
    score: int
    scale: float
    min_wave: int


ZOMBIE_SPECS: dict[str, ZombieSpec] = {
    "caminante": ZombieSpec(
        kind="caminante",
        health=58.0,
        speed=1.36,
        damage=8.0,
        attack_interval=1.0,
        radius=0.34,
        score=100,
        scale=1.0,
        min_wave=1,
    ),
    "corredor": ZombieSpec(
        kind="corredor",
        health=40.0,
        speed=2.15,
        damage=6.0,
        attack_interval=0.75,
        radius=0.30,
        score=150,
        scale=0.94,
        min_wave=2,
    ),
    "tanque": ZombieSpec(
        kind="tanque",
        health=190.0,
        speed=0.76,
        damage=16.0,
        attack_interval=1.25,
        radius=0.48,
        score=300,
        scale=1.32,
        min_wave=3,
    ),
}


@dataclass(slots=True)
class Zombie:
    uid: int
    kind: str
    x: float
    y: float
    health: float
    max_health: float
    speed: float
    damage: float
    attack_interval: float
    radius: float
    score: int
    scale: float
    heading: float = 0.0
    phase: float = 0.0
    attack_cd: float = 0.35
    flash: float = 0.0
    alive: bool = True
    death_timer: float = 0.0
    avoid_timer: float = 0.0
    avoid_side: float = 1.0


@dataclass(slots=True)
class Player:
    x: float = PLAYER_START[0]
    y: float = PLAYER_START[1]
    heading: float = 0.0
    pitch: float = 0.0
    health: float = PLAYER_MAX_HEALTH
    bob_phase: float = 0.0
    moving: float = 0.0


@dataclass(frozen=True, slots=True)
class SimEvent:
    kind: str
    value: float = 0.0
    x: float = 0.0
    y: float = 0.0
    text: str = ""


# -- colisiones ------------------------------------------------------------


def _circle_push(x: float, y: float, radius: float, rect: Rect) -> Vec2:
    x0, y0, x1, y1 = rect
    nearest_x = clamp(x, x0, x1)
    nearest_y = clamp(y, y0, y1)
    dx = x - nearest_x
    dy = y - nearest_y
    distance_sq = dx * dx + dy * dy
    if distance_sq >= radius * radius:
        return x, y
    if distance_sq > 1e-9:
        distance = math.sqrt(distance_sq)
        push = radius - distance
        return x + dx / distance * push, y + dy / distance * push
    # Centro exactamente dentro de la caja: salir por el lado más cercano.
    left = x - x0
    right = x1 - x
    bottom = y - y0
    top = y1 - y
    smallest = min(left, right, bottom, top)
    if smallest == left:
        return x0 - radius, y
    if smallest == right:
        return x1 + radius, y
    if smallest == bottom:
        return x, y0 - radius
    return x, y1 + radius


def resolve_circle(x: float, y: float, radius: float) -> Vec2:
    for _ in range(3):
        moved = False
        for rect in OBSTACLES:
            nx, ny = _circle_push(x, y, radius, rect)
            if nx != x or ny != y:
                x, y = nx, ny
                moved = True
        if not moved:
            break
    return x, y


def _point_clear(x: float, y: float, radius: float) -> bool:
    for rect in OBSTACLES:
        nx, ny = _circle_push(x, y, radius, rect)
        if nx != x or ny != y:
            return False
    return True


def _ray_rect(px: float, py: float, dx: float, dy: float, rect: Rect) -> float | None:
    x0, y0, x1, y1 = rect
    t_min = 0.0
    t_max = 1.0
    for origin, delta, low, high in ((px, dx, x0, x1), (py, dy, y0, y1)):
        if abs(delta) < 1e-9:
            if origin < low or origin > high:
                return None
            continue
        first = (low - origin) / delta
        second = (high - origin) / delta
        if first > second:
            first, second = second, first
        t_min = max(t_min, first)
        t_max = min(t_max, second)
        if t_min > t_max:
            return None
    return t_min if 0.0 <= t_min <= 1.0 else None


def segment_blocked(origin: Vec2, target: Vec2) -> bool:
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    for rect in OBSTACLES:
        hit = _ray_rect(origin[0], origin[1], dx, dy, rect)
        if hit is not None and 0.03 < hit < 0.98:
            return True
    return False


# -- simulación ------------------------------------------------------------


@dataclass
class ZombieSim:
    """Una partida completa: jugador, armas, oleadas y zombis."""

    rng: random.Random = field(default_factory=lambda: random.Random(20261120))
    player: Player = field(default_factory=Player)
    phase: str = "title"
    wave: int = 0
    score: int = 0
    kills: int = 0
    wave_kills: int = 0
    zombies: list[Zombie] = field(default_factory=list)
    weapons: list[WeaponState] = field(default_factory=list)
    current_weapon: int = 0
    pending: list[str] = field(default_factory=list)
    spawn_timer: float = 0.0
    break_timer: float = 0.0
    _next_uid: int = 1

    def __post_init__(self) -> None:
        if not self.weapons:
            self.weapons = [WeaponState(spec.magazine) for spec in WEAPONS]
        if self.current_weapon >= len(self.weapons):
            self.current_weapon = 0

    # -- ciclo de partida ---------------------------------------------------

    @property
    def weapon(self) -> WeaponSpec:
        return WEAPONS[self.current_weapon]

    @property
    def ammo(self) -> int:
        return self.weapons[self.current_weapon].ammo

    @property
    def reload_timer(self) -> float:
        return self.weapons[self.current_weapon].reload_timer

    @property
    def reload_progress(self) -> float:
        spec = self.weapon
        state = self.weapons[self.current_weapon]
        if state.reload_timer <= 0.0:
            return 1.0
        return clamp(1.0 - state.reload_timer / spec.reload_time, 0.0, 1.0)

    @property
    def alive_zombies(self) -> list[Zombie]:
        return [zombie for zombie in self.zombies if zombie.alive]

    @property
    def zombie_count(self) -> int:
        return sum(1 for zombie in self.zombies if zombie.alive)

    @property
    def game_over(self) -> bool:
        return self.phase == "gameover"

    def reset(self) -> None:
        self.player = Player()
        self.phase = "title"
        self.wave = 0
        self.score = 0
        self.kills = 0
        self.wave_kills = 0
        self.zombies = []
        self.weapons = [WeaponState(spec.magazine) for spec in WEAPONS]
        self.current_weapon = 0
        self.pending = []
        self.spawn_timer = 0.0
        self.break_timer = 0.0
        self._next_uid = 1

    def begin(self) -> list[SimEvent]:
        self.reset()
        self.wave = 1
        return self._start_wave()

    def restart(self) -> list[SimEvent]:
        return self.begin()

    def _start_wave(self) -> list[SimEvent]:
        self.phase = "wave"
        self.wave_kills = 0
        count = min(18, 3 + self.wave * 2)
        self.pending = [self._roll_kind() for _ in range(count)]
        self.spawn_timer = 1.35 if self.wave == 1 else 0.55
        return [SimEvent("wave", value=float(self.wave), text=str(self.wave))]

    def _roll_kind(self) -> str:
        roll = self.rng.random()
        if self.wave >= 3 and roll < 0.14:
            return "tanque"
        if self.wave >= 2 and roll < 0.40:
            return "corredor"
        return "caminante"

    # -- entrada ------------------------------------------------------------

    def look(self, dx: float, dy: float) -> None:
        self.player.heading = wrap_degrees(self.player.heading - dx * 175.0)
        self.player.pitch = clamp(self.player.pitch - dy * 120.0, -7.0, 7.0)

    def start_reload(self) -> list[SimEvent]:
        if self.phase not in ("wave", "break"):
            return []
        state = self.weapons[self.current_weapon]
        spec = self.weapon
        if state.reload_timer > 0.0 or state.ammo >= spec.magazine:
            return []
        state.reload_timer = spec.reload_time
        return [SimEvent("reload", text=spec.key)]

    def swap_weapon(self) -> list[SimEvent]:
        if self.phase not in ("wave", "break"):
            return []
        old = self.weapons[self.current_weapon]
        old.reload_timer = 0.0
        self.current_weapon = (self.current_weapon + 1) % len(self.weapons)
        new = self.weapons[self.current_weapon]
        new.cooldown = max(new.cooldown, 0.24)
        return [SimEvent("swap", text=self.weapon.key)]

    def add_zombie(self, kind: str, x: float, y: float) -> Zombie:
        spec = ZOMBIE_SPECS[kind]
        zombie = Zombie(
            uid=self._next_uid,
            kind=kind,
            x=x,
            y=y,
            health=spec.health,
            max_health=spec.health,
            speed=spec.speed,
            damage=spec.damage,
            attack_interval=spec.attack_interval,
            radius=spec.radius,
            score=spec.score,
            scale=spec.scale,
            heading=angle_to((x, y), (self.player.x, self.player.y)),
        )
        self._next_uid += 1
        self.zombies.append(zombie)
        return zombie

    # -- disparo ------------------------------------------------------------

    def fire(self) -> list[SimEvent]:
        if self.phase not in ("wave", "break"):
            return []
        state = self.weapons[self.current_weapon]
        spec = self.weapon
        if state.reload_timer > 0.0 or state.cooldown > 0.0:
            return []
        if state.ammo <= 0:
            state.cooldown = 0.25
            if state.dry:
                return []
            state.dry = True
            return [SimEvent("empty", text=spec.key)]

        state.ammo -= 1
        state.dry = False
        state.cooldown = spec.interval
        events = [SimEvent("shot", value=spec.kick, text=spec.key)]
        assist = self._assist_angle(spec.range)
        for _ in range(spec.pellets):
            base = assist if assist is not None else self.player.heading
            angle = base + self.rng.uniform(-spec.spread, spec.spread)
            target = self._ray_hit(angle, spec.range)
            if target is None:
                continue
            distance = math.hypot(target.x - self.player.x, target.y - self.player.y)
            falloff = 1.0 - spec.falloff * clamp(distance / spec.range, 0.0, 1.0)
            damage = spec.damage * max(0.25, falloff)
            self._damage_zombie(target, damage, events)
        return events

    def _assist_angle(self, weapon_range: float) -> float | None:
        best: Zombie | None = None
        best_angle = 0.0
        best_diff = 5.0
        origin = (self.player.x, self.player.y)
        for zombie in self.zombies:
            if not zombie.alive:
                continue
            distance = math.hypot(zombie.x - self.player.x, zombie.y - self.player.y)
            if distance > weapon_range:
                continue
            angle = angle_to(origin, (zombie.x, zombie.y))
            diff = abs(wrap_degrees(angle - self.player.heading))
            if diff < best_diff and not segment_blocked(origin, (zombie.x, zombie.y)):
                best = zombie
                best_angle = angle
                best_diff = diff
        return best_angle if best is not None else None

    def _ray_hit(self, angle: float, weapon_range: float) -> Zombie | None:
        origin = (self.player.x, self.player.y)
        best: Zombie | None = None
        best_distance = weapon_range
        for zombie in self.zombies:
            if not zombie.alive:
                continue
            dx = zombie.x - self.player.x
            dy = zombie.y - self.player.y
            distance = math.hypot(dx, dy)
            if distance <= 0.05 or distance > weapon_range:
                continue
            target_angle = angle_to(origin, (zombie.x, zombie.y))
            diff = abs(wrap_degrees(target_angle - angle))
            angular_radius = math.degrees(math.atan2(zombie.radius * 1.15 + 0.08, distance))
            if diff > angular_radius:
                continue
            if segment_blocked(origin, (zombie.x, zombie.y)):
                continue
            if distance < best_distance:
                best = zombie
                best_distance = distance
        return best

    def _damage_zombie(self, zombie: Zombie, damage: float, events: list[SimEvent]) -> None:
        if not zombie.alive:
            return
        zombie.health -= damage
        zombie.flash = 0.16
        events.append(
            SimEvent("hit", value=damage, x=zombie.x, y=zombie.y, text=zombie.kind)
        )
        if zombie.health <= 0.0:
            zombie.health = 0.0
            zombie.alive = False
            zombie.death_timer = 0.95
            self.score += zombie.score
            self.kills += 1
            self.wave_kills += 1
            events.append(
                SimEvent("kill", value=float(zombie.score), x=zombie.x, y=zombie.y, text=zombie.kind)
            )

    # -- frame --------------------------------------------------------------

    def step(self, dt: float, move_x: float = 0.0, move_y: float = 0.0) -> list[SimEvent]:
        if self.phase in ("title", "gameover"):
            return []
        dt = clamp(dt, 0.0, 0.1)
        events: list[SimEvent] = []

        for index, state in enumerate(self.weapons):
            state.cooldown = max(0.0, state.cooldown - dt)
            if index == self.current_weapon and state.reload_timer > 0.0:
                state.reload_timer = max(0.0, state.reload_timer - dt)
                if state.reload_timer == 0.0:
                    state.ammo = WEAPONS[index].magazine
                    state.dry = False
                    events.append(SimEvent("reload_done", text=WEAPONS[index].key))

        self._move_player(dt, move_x, move_y)
        self._spawn_pending(dt)
        self._update_zombies(dt, events)

        if self.phase == "wave" and not self.pending and not self.alive_zombies:
            bonus = 150 * self.wave
            self.score += bonus
            self.phase = "break"
            self.break_timer = 3.6
            healed = min(12.0, PLAYER_MAX_HEALTH - self.player.health)
            self.player.health += healed
            events.append(
                SimEvent("clear", value=float(bonus), text=f"{healed:.0f}")
            )
        elif self.phase == "break":
            self.break_timer -= dt
            if self.break_timer <= 0.0:
                self.wave += 1
                events.extend(self._start_wave())

        if self.player.health <= 0.0 and self.phase != "gameover":
            self.player.health = 0.0
            self.phase = "gameover"
            events.append(SimEvent("gameover"))
        return events

    def _move_player(self, dt: float, move_x: float, move_y: float) -> None:
        length = math.hypot(move_x, move_y)
        if length > 1.0:
            move_x /= length
            move_y /= length
        forward = heading_vector(self.player.heading)
        right = (math.cos(math.radians(self.player.heading)), math.sin(math.radians(self.player.heading)))
        speed = PLAYER_SPEED
        dx = (forward[0] * move_y + right[0] * move_x) * speed * dt
        dy = (forward[1] * move_y + right[1] * move_x) * speed * dt
        old_x, old_y = self.player.x, self.player.y
        self.player.x, self.player.y = resolve_circle(
            self.player.x + dx, self.player.y + dy, PLAYER_RADIUS
        )
        moved = math.hypot(self.player.x - old_x, self.player.y - old_y)
        self.player.moving = min(1.0, moved / max(speed * dt, 1e-6))
        self.player.bob_phase += moved * 4.4

    def _spawn_pending(self, dt: float) -> None:
        if not self.pending:
            return
        self.spawn_timer -= dt
        if self.spawn_timer > 0.0:
            return
        kind = self.pending.pop(0)
        point = self._pick_spawn()
        self.add_zombie(kind, point[0], point[1])
        self.spawn_timer = max(0.32, 0.82 - self.wave * 0.035)

    def _pick_spawn(self) -> Vec2:
        forward = heading_vector(self.player.heading)
        far = [
            point
            for point in SPAWN_POINTS
            if math.hypot(point[0] - self.player.x, point[1] - self.player.y) > 9.0
        ]
        in_front: list[Vec2] = []
        for point in far:
            dx = point[0] - self.player.x
            dy = point[1] - self.player.y
            distance = math.hypot(dx, dy)
            if (dx * forward[0] + dy * forward[1]) / max(distance, 1e-6) > 0.20:
                in_front.append(point)
        candidates = in_front or far or list(SPAWN_POINTS)
        x, y = self.rng.choice(candidates)
        x += self.rng.uniform(-0.7, 0.7)
        y += self.rng.uniform(-0.7, 0.7)
        return resolve_circle(x, y, 0.42)

    def _update_zombies(self, dt: float, events: list[SimEvent]) -> None:
        speed_scale = min(1.35, 1.0 + 0.045 * (self.wave - 1))
        for zombie in self.zombies:
            zombie.flash = max(0.0, zombie.flash - dt)
            if not zombie.alive:
                zombie.death_timer = max(0.0, zombie.death_timer - dt)
                continue

            dx = self.player.x - zombie.x
            dy = self.player.y - zombie.y
            distance = math.hypot(dx, dy)
            if distance > 0.02:
                zombie.heading = math.degrees(math.atan2(-dx, dy))
            zombie.attack_cd = max(0.0, zombie.attack_cd - dt)

            attack_range = 1.0 + zombie.radius
            if distance > attack_range:
                desired_x = dx / max(distance, 1e-6)
                desired_y = dy / max(distance, 1e-6)
                nx, ny = desired_x, desired_y
                if zombie.avoid_timer > 0.0:
                    zombie.avoid_timer = max(0.0, zombie.avoid_timer - dt)
                    tx, ty = -ny * zombie.avoid_side, nx * zombie.avoid_side
                    nx = nx * 0.42 + tx * 0.58
                    ny = ny * 0.42 + ty * 0.58
                move = zombie.speed * speed_scale * dt
                old_x, old_y = zombie.x, zombie.y
                zombie.x, zombie.y = resolve_circle(
                    zombie.x + nx * move, zombie.y + ny * move, zombie.radius
                )
                actual = math.hypot(zombie.x - old_x, zombie.y - old_y)
                zombie.phase += actual * 5.2
                if actual < move * 0.30 and zombie.avoid_timer <= 0.0:
                    zombie.avoid_side = self._pick_avoid_side(
                        zombie, desired_x, desired_y
                    )
                    zombie.avoid_timer = 0.9
            else:
                zombie.phase += dt * 1.4
                if zombie.attack_cd <= 0.0:
                    zombie.attack_cd = zombie.attack_interval
                    self.player.health = max(0.0, self.player.health - zombie.damage)
                    events.append(
                        SimEvent(
                            "hurt",
                            value=zombie.damage,
                            x=self.player.x,
                            y=self.player.y,
                            text=zombie.kind,
                        )
                    )

            # Empujar al zombi fuera del cuerpo del jugador.
            dx = zombie.x - self.player.x
            dy = zombie.y - self.player.y
            distance = math.hypot(dx, dy)
            minimum = zombie.radius + PLAYER_RADIUS
            if 0.0 < distance < minimum:
                zombie.x = self.player.x + dx / distance * minimum
                zombie.y = self.player.y + dy / distance * minimum

        self._separate_zombies()
        self.zombies = [
            zombie for zombie in self.zombies if zombie.alive or zombie.death_timer > 0.0
        ]

    def _pick_avoid_side(self, zombie: Zombie, nx: float, ny: float) -> float:
        """Elegí el rodeo que deje al zombi más cerca del jugador."""
        probe = 1.0
        best_side = zombie.avoid_side
        best_distance = float("inf")
        for side in (1.0, -1.0):
            tx = -ny * side
            ty = nx * side
            px = zombie.x + tx * probe
            py = zombie.y + ty * probe
            if not _point_clear(px, py, max(0.20, zombie.radius * 0.9)):
                continue
            ex = px + tx * 0.8 + nx * 0.4
            ey = py + ty * 0.8 + ny * 0.4
            distance = math.hypot(self.player.x - ex, self.player.y - ey)
            if distance < best_distance:
                best_distance = distance
                best_side = side
        if best_side == 0.0:
            return 1.0
        return best_side

    def _separate_zombies(self) -> None:
        for index, first in enumerate(self.zombies):
            if not first.alive:
                continue
            for second in self.zombies[index + 1 :]:
                if not second.alive:
                    continue
                dx = second.x - first.x
                dy = second.y - first.y
                distance = math.hypot(dx, dy)
                minimum = first.radius + second.radius
                if distance <= 1e-6 or distance >= minimum:
                    continue
                push = (minimum - distance) * 0.5
                nx = dx / distance
                ny = dy / distance
                first.x = clamp(first.x - nx * push, -ARENA_HALF_X, ARENA_HALF_X)
                first.y = clamp(first.y - ny * push, -ARENA_HALF_Y, ARENA_HALF_Y)
                second.x = clamp(second.x + nx * push, -ARENA_HALF_X, ARENA_HALF_X)
                second.y = clamp(second.y + ny * push, -ARENA_HALF_Y, ARENA_HALF_Y)

    # -- consultas para el HUD ---------------------------------------------

    def nearest_zombie(self) -> Zombie | None:
        best: Zombie | None = None
        best_distance = float("inf")
        for zombie in self.zombies:
            if not zombie.alive:
                continue
            distance = math.hypot(zombie.x - self.player.x, zombie.y - self.player.y)
            if distance < best_distance:
                best = zombie
                best_distance = distance
        return best
