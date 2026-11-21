"""Pruebas puras del combate, oleadas y colisiones."""

from __future__ import annotations

from jubilados_zombies.sim import (
    PLAYER_MAX_HEALTH,
    WEAPONS,
    ZombieSim,
    resolve_circle,
)


def ready_sim() -> ZombieSim:
    sim = ZombieSim()
    sim.begin()
    sim.pending = []
    sim.zombies = []
    return sim


def test_starts_with_revolver_and_full_magazine() -> None:
    sim = ZombieSim()
    assert sim.phase == "title"
    assert sim.weapon.key == "revolver"
    assert sim.ammo == WEAPONS[0].magazine


def test_revolver_kills_a_zombie_in_front() -> None:
    sim = ready_sim()
    sim.player.x, sim.player.y = 3.0, -15.0
    zombie = sim.add_zombie("caminante", 3.0, -5.0)
    seen: list[str] = []
    for _ in range(4):
        sim.weapons[sim.current_weapon].cooldown = 0.0
        seen.extend(event.kind for event in sim.fire())
        sim.step(0.1, 0.0, 0.0)
        if not zombie.alive:
            break
    assert zombie.alive is False
    assert "hit" in seen and "kill" in seen
    assert sim.score >= zombie.score
    assert sim.kills == 1
    assert len(sim.zombies) == 1  # el cadáver se queda un momento


def test_wall_blocks_the_shot() -> None:
    sim = ready_sim()
    sim.player.x, sim.player.y = -6.5, -15.0
    sim.add_zombie("caminante", -6.5, -3.0)  # detrás de la fuente
    events = sim.fire()
    assert [event.kind for event in events] == ["shot"]


def test_reload_takes_time_and_refills() -> None:
    sim = ready_sim()
    sim.fire()
    assert sim.ammo == WEAPONS[0].magazine - 1
    events = sim.start_reload()
    assert [event.kind for event in events] == ["reload"]
    for _ in range(30):
        events = sim.step(0.05, 0.0, 0.0)
        if any(event.kind == "reload_done" for event in events):
            break
    assert sim.ammo == WEAPONS[0].magazine
    assert sim.reload_timer == 0.0


def test_weapon_cycles_and_cancels_reload() -> None:
    sim = ready_sim()
    sim.start_reload()
    events = sim.swap_weapon()
    assert [event.kind for event in events] == ["swap"]
    assert sim.current_weapon == 1
    assert sim.weapon.key == "escopeta"
    assert sim.reload_timer == 0.0
    sim.swap_weapon()
    sim.swap_weapon()
    assert sim.current_weapon == 0


def test_empty_magazine_reports_empty() -> None:
    sim = ready_sim()
    sim.weapons[0].ammo = 0
    events = sim.fire()
    assert [event.kind for event in events] == ["empty"]
    assert sim.ammo == 0
    sim.step(0.3, 0.0, 0.0)
    assert sim.fire() == []  # no repite el aviso en cada frame


def test_shotgun_hits_close_targets() -> None:
    sim = ready_sim()
    sim.player.x, sim.player.y = 3.0, -15.0
    sim.current_weapon = 1
    zombie = sim.add_zombie("caminante", 3.0, -10.0)
    events = sim.fire()
    damage = sum(event.value for event in events if event.kind == "hit")
    assert damage > 0.0
    assert zombie.health < zombie.max_health


def test_wave_clear_and_next_wave() -> None:
    sim = ZombieSim()
    assert sim.phase == "title"
    sim.begin()
    assert sim.phase == "wave"
    assert sim.wave == 1
    for _ in range(20):
        sim.step(0.1, 0.0, 0.0)
    assert sim.zombie_count > 0

    sim.pending = []
    sim.zombies = []
    events = sim.step(0.1, 0.0, 0.0)
    assert sim.phase == "break"
    assert any(event.kind == "clear" for event in events)

    all_events = []
    for _ in range(40):
        all_events.extend(sim.step(0.1, 0.0, 0.0))
    assert sim.wave == 2
    assert sim.phase == "wave"
    assert any(event.kind == "wave" for event in all_events)


def test_player_stops_at_the_perimeter() -> None:
    sim = ready_sim()
    sim.player.x, sim.player.y = 0.0, -15.0
    for _ in range(100):
        sim.step(0.05, 0.0, -1.0)
    assert sim.player.y > -18.5
    assert sim.player.y < -17.4


def test_circle_resolution_keeps_player_out_of_walls() -> None:
    x, y = resolve_circle(-6.5, -7.0, 0.4)
    assert (x, y) != (-6.5, -7.0)


def test_zombie_attack_damages_player() -> None:
    sim = ready_sim()
    sim.player.x, sim.player.y = 0.0, 0.0
    sim.add_zombie("caminante", 0.0, 0.8)
    events = []
    for _ in range(40):
        events.extend(sim.step(0.05, 0.0, 0.0))
    assert sim.player.health < PLAYER_MAX_HEALTH
    assert any(event.kind == "hurt" for event in events)


def test_player_death_ends_the_run() -> None:
    sim = ready_sim()
    sim.player.x, sim.player.y = 0.0, 0.0
    sim.player.health = 5.0
    sim.add_zombie("tanque", 0.0, 0.9)
    events = []
    for _ in range(80):
        events.extend(sim.step(0.05, 0.0, 0.0))
        if sim.phase == "gameover":
            break
    assert sim.phase == "gameover"
    assert sim.player.health == 0.0
    assert any(event.kind == "gameover" for event in events)


def test_restart_resets_score_and_health() -> None:
    sim = ready_sim()
    sim.score = 1234
    sim.player.health = 12.0
    sim.restart()
    assert sim.phase == "wave"
    assert sim.wave == 1
    assert sim.score == 0
    assert sim.player.health == PLAYER_MAX_HEALTH
    assert sim.ammo == WEAPONS[0].magazine
