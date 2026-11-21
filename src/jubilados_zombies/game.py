"""Jubilados Zombies: Doom de jubilados con gestos del celular."""

from __future__ import annotations

import math
from typing import Any

from toxinator.api import GameContext, GameManifest

from .controls import ControlReader, Controls
from .hud import CREAM, CRIMSON, GOLD, JADE, Hud
from .scene import GameScene
from .sim import PLAYER_EYE, WEAPON_BY_KEY, SimEvent, ZombieSim


class JubiladosZombies:
    """Un jugador, oleadas de zombis y un teléfono usado como arma."""

    def __init__(self, manifest: GameManifest) -> None:
        self.manifest = manifest
        self.ctx: GameContext | None = None
        self.base: Any = None
        self.root: Any = None
        self.ui_root: Any = None
        self.sim = ZombieSim()
        self.reader = ControlReader()
        self.scene: GameScene | None = None
        self.hud: Hud | None = None
        self.paused = False
        self.elapsed = 0.0
        self._cam_kick = 0.0
        self._cam_shake = 0.0
        self._sfx_cd = 0.0
        self._saved_cam: tuple[Any, Any, float, float] | None = None

    # -- ciclo de vida ------------------------------------------------------

    def start(self, ctx: GameContext) -> None:
        self.ctx = ctx
        self.base = ctx.base
        self.root = ctx.scene.attach_new_node("jubilados-zombies")
        self.ui_root = ctx.ui.attach_new_node("jubilados-zombies-ui")
        self._save_camera()

        self.sim = ZombieSim()
        self.sim.reset()
        self.reader.reset()
        self.paused = False
        self.elapsed = 0.0
        self._cam_kick = 0.0
        self._cam_shake = 0.0
        self._sfx_cd = 0.0

        self.scene = GameScene(self.base, self.root)
        self.hud = Hud(self.ui_root)
        controls = Controls(invert=self.reader.invert)
        self._update_camera(0.0)
        self.scene.update(self.sim, 0.0)
        self.hud.update(self.sim, controls, 0.0, False)

    def stop(self) -> None:
        if self.ctx is not None:
            self.ctx.phone.stop()
        if self.hud is not None:
            self.hud.destroy()
            self.hud = None
        if self.scene is not None:
            self.scene.destroy()
            self.scene = None
        self._restore_camera()
        if self.ui_root is not None:
            self.ui_root.remove_node()
            self.ui_root = None
        if self.root is not None:
            self.root.remove_node()
            self.root = None
        self.ctx = None
        self.base = None

    # -- frame --------------------------------------------------------------

    def update(self, dt: float) -> None:
        if self.ctx is None or self.scene is None or self.hud is None:
            return
        dt = max(0.0, min(dt, 0.1))
        self.elapsed += dt
        self._sfx_cd = max(0.0, self._sfx_cd - dt)
        frame = self.ctx.input_state.primary_frame()
        controls = self.reader.update(frame, self.ctx.input_state.gestures, dt)
        events: list[SimEvent] = []

        if controls.invert_toggled:
            state = "INVERTIDO" if controls.invert else "NORMAL"
            self.hud.message(
                f"GIRO {state}",
                GOLD,
                1.6,
                "GIRÁ A LA IZQUIERDA: RECARGAR | A LA DERECHA: ARMA" if not controls.invert else "GIRÁ A LA IZQUIERDA: ARMA | A LA DERECHA: RECARGAR",
            )

        if self.sim.phase == "title":
            if controls.fire_pressed:
                events.extend(self.sim.begin())
                self.paused = False
        elif self.sim.phase == "gameover":
            if controls.fire_pressed:
                events.extend(self.sim.restart())
                self.paused = False
                self.hud.reset()
                events.extend(self.sim.step(dt, controls.move_x, controls.move_y))
        elif self.paused:
            if controls.pause:
                self.paused = False
        elif controls.pause:
            self.paused = True
        else:
            self.sim.look(controls.look_dx, controls.look_dy)
            if controls.reload:
                events.extend(self.sim.start_reload())
            if controls.swap:
                events.extend(self.sim.swap_weapon())
            if controls.fire:
                events.extend(self.sim.fire())
            events.extend(self.sim.step(dt, controls.move_x, controls.move_y))

        self._handle_events(events)
        self._update_camera(dt)
        self.scene.update(self.sim, dt)
        self.hud.update(self.sim, controls, dt, self.paused)

    # -- eventos ------------------------------------------------------------

    def _handle_events(self, events: list[SimEvent]) -> None:
        if self.ctx is None or self.scene is None or self.hud is None:
            return
        phone = self.ctx.phone
        for event in events:
            if event.kind == "shot":
                self.scene.fire(event.value)
                self._cam_kick = min(12.0, self._cam_kick + 1.6 + event.value * 1.1)
                spec = WEAPON_BY_KEY.get(event.text)
                if spec is not None and self._sfx_cd <= 0.0:
                    self._sfx_cd = 0.075
                    if event.text == "escopeta":
                        phone.vibrate([28, 18, 34])
                        phone.tone(spec.tone, 90, volume=0.30)
                    elif event.text == "subfusil":
                        phone.vibrate([7])
                        phone.tone(spec.tone, 28, volume=0.10)
                    else:
                        phone.vibrate([14])
                        phone.tone(spec.tone, 45, volume=0.20)
            elif event.kind == "hit":
                self.scene.blood(event.x, event.y)
                self.hud.hit()
                self._cam_shake = max(self._cam_shake, 0.12)
                phone.tone(1080, 22, volume=0.10)
            elif event.kind == "kill":
                self.scene.blood(event.x, event.y, heavy=True)
                self.scene.stain(event.x, event.y)
                self.hud.hit()
                phone.vibrate([18, 15, 26])
            elif event.kind == "hurt":
                self.hud.flash(0.55)
                self.hud.message("¡TE ALCANZARON!", CRIMSON, 1.2)
                self._cam_shake = max(self._cam_shake, 1.0)
                phone.vibrate([70, 35, 110])
                phone.tone(95, 190, volume=0.42)
            elif event.kind == "empty":
                self.hud.message("SIN MUNICIÓN", CRIMSON, 1.4, "GIRÁ A LA IZQUIERDA O L1 PARA RECARGAR")
                phone.tone(150, 55, volume=0.20)
            elif event.kind == "reload":
                spec = WEAPON_BY_KEY.get(event.text)
                name = spec.name if spec is not None else "ARMA"
                self.hud.message(f"RECARGANDO {name}", GOLD, 1.0)
                phone.tone(320, 60, volume=0.16)
            elif event.kind == "reload_done":
                self.hud.message("¡LISTO!", JADE, 0.8)
                phone.tone(560, 55, volume=0.16)
            elif event.kind == "swap":
                self.scene.swap()
                spec = WEAPON_BY_KEY.get(event.text)
                name = spec.name if spec is not None else "ARMA"
                self.hud.message(name, CREAM, 1.0, "GIRÁ A LA DERECHA O R1 PARA LA SIGUIENTE")
                phone.tone(460, 60, volume=0.18)
            elif event.kind == "wave":
                wave = int(event.value)
                sub = (
                    "SACUDÍ EL CELULAR PARA DISPARAR"
                    if wave == 1
                    else "VIENEN MÁS JUBILADOS"
                )
                self.hud.message(f"¡OLEADA {wave}!", GOLD, 2.4, sub)
                phone.vibrate([45, 35, 45])
                phone.tone(650, 100, volume=0.24)
            elif event.kind == "clear":
                self.hud.message(
                    "OLEADA LIMPIA",
                    JADE,
                    2.6,
                    f"+{int(event.value)} PUNTOS | SALUD +{event.text}",
                )
                phone.vibrate([30, 40, 30, 40, 60])
                phone.tone(880, 110, volume=0.22)
            elif event.kind == "gameover":
                self.paused = False
                self._cam_shake = 1.2
                phone.vibrate([220, 90, 220, 90, 360])
                phone.tone(72, 460, volume=0.46)

    # -- cámara -------------------------------------------------------------

    def _update_camera(self, dt: float) -> None:
        if self.base is None:
            return
        self._cam_kick *= math.exp(-max(dt, 0.0) * 15.0)
        self._cam_shake = max(0.0, self._cam_shake - dt * 2.6)
        sim = self.sim
        bob = math.sin(sim.player.bob_phase) * 0.030 * sim.player.moving
        shake = self._cam_shake
        time = self.elapsed
        yaw = sim.player.heading + math.sin(time * 97.0) * shake * 1.7
        pitch = sim.player.pitch + self._cam_kick + math.cos(time * 83.0) * shake * 0.9
        roll = math.sin(time * 61.0) * shake * 1.4
        self.base.cam.set_pos(
            sim.player.x + math.sin(time * 71.0) * shake * 0.045,
            sim.player.y + math.cos(time * 67.0) * shake * 0.040,
            PLAYER_EYE + bob + math.sin(time * 101.0) * shake * 0.060,
        )
        self.base.cam.set_hpr(yaw, pitch, roll)

    def _save_camera(self) -> None:
        if self.base is None:
            return
        cam = self.base.cam
        self._saved_cam = (
            cam.get_pos(),
            cam.get_hpr(),
            self.base.camLens.getFov(),
            self.base.camLens.getNear(),
        )
        self.base.camLens.setFov(80.0)
        self.base.camLens.setNear(0.05)

    def _restore_camera(self) -> None:
        if self.base is None or self._saved_cam is None:
            return
        pos, hpr, fov, near = self._saved_cam
        self.base.cam.set_pos(pos)
        self.base.cam.set_hpr(hpr)
        self.base.camLens.setFov(fov)
        self.base.camLens.setNear(near)
        self._saved_cam = None
