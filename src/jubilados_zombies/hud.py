"""HUD de Jubilados Zombies: salud, munición, avisos y pantallas."""

from __future__ import annotations

import math

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import CardMaker, NodePath, TextNode, Vec4

from .controls import Controls
from .sim import ZombieSim, angle_to, wrap_degrees

CREAM = Vec4(0.93, 0.95, 0.90, 1.0)
MUTED = Vec4(0.58, 0.66, 0.62, 1.0)
BONE = Vec4(0.82, 0.85, 0.74, 1.0)
GOLD = Vec4(1.0, 0.79, 0.27, 1.0)
JADE = Vec4(0.42, 0.96, 0.56, 1.0)
CRIMSON = Vec4(1.0, 0.25, 0.22, 1.0)
SHADOW = Vec4(0.0, 0.0, 0.0, 0.82)
DARK = Vec4(0.008, 0.014, 0.012, 1.0)
OVERLAY_CLEAR = Vec4(DARK[0], DARK[1], DARK[2], 0.0)


class Hud:
    """Textos y carteles 2D del juego."""

    def __init__(self, root: NodePath) -> None:
        self.root = root
        self.texts: dict[str, OnscreenText] = {}
        self.time = 0.0
        self.flash_alpha = 0.0
        self.hit_timer = 0.0
        self.message_text = ""
        self.message_sub = ""
        self.message_timer = 0.0
        self.message_color = GOLD
        self._overlay = self._card(0.0, 30)
        self._flash = self._card(0.0, 20)
        self._wave_text = ""
        self._score_text = ""
        self._health_text = ""
        self._health_bar_text = ""
        self._threats_text = ""
        self._weapon_text = ""
        self._ammo_text = ""
        self._reload_text = ""
        self._gameover_stats = ""
        self._build()

    # -- construcción -------------------------------------------------------

    def _card(self, alpha: float, sort: int) -> NodePath:
        maker = CardMaker("hud-card")
        maker.set_frame(-2.0, 2.0, -1.2, 1.2)
        card = self.root.attach_new_node(maker.generate())
        card.set_color(Vec4(DARK[0], DARK[1], DARK[2], alpha))
        card.set_transparency(1)
        card.set_bin("fixed", sort)
        card.set_depth_test(False)
        card.set_depth_write(False)
        return card

    def _text(
        self,
        key: str,
        *,
        pos: tuple[float, float],
        scale: float,
        color: Vec4,
        align: int = TextNode.ACenter,
        sort: int = 50,
    ) -> OnscreenText:
        text = OnscreenText(
            text="",
            parent=self.root,
            pos=pos,
            scale=scale,
            fg=color,
            align=align,
            shadow=SHADOW,
            mayChange=True,
        )
        text.set_bin("fixed", sort)
        text.set_depth_test(False)
        self.texts[key] = text
        return text

    def _build(self) -> None:
        self._text("title", pos=(0.0, 0.46), scale=0.115, color=GOLD, sort=55)
        self._text("subtitle", pos=(0.0, 0.32), scale=0.048, color=CREAM, sort=55)
        self._text("title_a", pos=(0.0, 0.13), scale=0.038, color=JADE, sort=55)
        self._text("title_b", pos=(0.0, 0.055), scale=0.038, color=JADE, sort=55)
        self._text("title_c", pos=(0.0, -0.02), scale=0.038, color=JADE, sort=55)
        self._text("title_d", pos=(0.0, -0.095), scale=0.032, color=MUTED, sort=55)
        self._text("title_start", pos=(0.0, -0.26), scale=0.050, color=CREAM, sort=55)

        self._text("wave", pos=(-1.52, 0.88), scale=0.042, color=CREAM, align=TextNode.ALeft)
        self._text("score", pos=(1.52, 0.88), scale=0.042, color=GOLD, align=TextNode.ARight)
        self._text("sensor", pos=(0.0, 0.93), scale=0.026, color=MUTED)
        self._text(
            "health", pos=(-1.52, -0.80), scale=0.044, color=CREAM, align=TextNode.ALeft
        )
        self._text(
            "health_bar", pos=(-1.52, -0.865), scale=0.032, color=JADE, align=TextNode.ALeft
        )
        self._text(
            "threats", pos=(-1.52, -0.925), scale=0.029, color=MUTED, align=TextNode.ALeft
        )
        self._text(
            "weapon", pos=(1.52, -0.80), scale=0.042, color=CREAM, align=TextNode.ARight
        )
        self._text(
            "ammo", pos=(1.52, -0.865), scale=0.032, color=BONE, align=TextNode.ARight
        )
        self._text(
            "reload", pos=(1.52, -0.925), scale=0.028, color=GOLD, align=TextNode.ARight
        )
        self._text("crosshair", pos=(0.0, 0.0), scale=0.072, color=JADE)
        self._text("hitmark", pos=(0.0, 0.0), scale=0.095, color=CRIMSON)
        self._text("message", pos=(0.0, 0.30), scale=0.073, color=GOLD)
        self._text("message_sub", pos=(0.0, 0.205), scale=0.040, color=CREAM)
        self._text("hint", pos=(0.0, -0.930), scale=0.026, color=MUTED)
        self._text("hint2", pos=(0.0, -0.970), scale=0.026, color=MUTED)
        self._text("low", pos=(0.0, 0.13), scale=0.052, color=CRIMSON)
        self._text("pause", pos=(0.0, 0.06), scale=0.10, color=CREAM)
        self._text("pause_sub", pos=(0.0, -0.05), scale=0.042, color=MUTED)
        self._text(
            "threat_left", pos=(-1.24, -0.05), scale=0.042, color=CRIMSON, align=TextNode.ALeft
        )
        self._text(
            "threat_right", pos=(1.24, -0.05), scale=0.042, color=CRIMSON, align=TextNode.ARight
        )
        self._text("gameover", pos=(0.0, 0.36), scale=0.115, color=CRIMSON, sort=55)
        self._text("gameover_stats", pos=(0.0, 0.17), scale=0.045, color=CREAM, sort=55)
        self._text("gameover_prompt", pos=(0.0, -0.06), scale=0.050, color=GOLD, sort=55)

        self.texts["title"].setText("JUBILADOS ZOMBIES")
        self.texts["subtitle"].setText("El club de jubilados fue invadido")
        self.texts["title_a"].setText("SACUDÍ EL CELULAR  >  DISPARAR")
        self.texts["title_b"].setText("GIRÁ A LA IZQUIERDA  >  RECARGAR")
        self.texts["title_c"].setText("GIRÁ A LA DERECHA  >  CAMBIAR DE ARMA")
        self.texts["title_d"].setText("TELÉFONO DE COSTADO | STICK MOVER | ARRASTRÁ APUNTAR | SIN SENSORES: X / L1 / R1")
        self.texts["title_start"].setText("SACUDÍ O APRETÁ X PARA EMPEZAR")
        self.texts["pause"].setText("")
        self.texts["pause_sub"].setText("")
        self.texts["crosshair"].setText("")
        self.texts["hitmark"].setText("")

    # -- API para el juego --------------------------------------------------

    def message(
        self,
        text: str,
        color: Vec4 = GOLD,
        duration: float = 1.8,
        sub: str = "",
    ) -> None:
        self.message_text = text
        self.message_color = color
        self.message_timer = max(0.0, duration)
        self.message_sub = sub

    def flash(self, amount: float = 0.5) -> None:
        self.flash_alpha = max(self.flash_alpha, amount)

    def hit(self) -> None:
        self.hit_timer = 0.16

    def reset(self) -> None:
        self.flash_alpha = 0.0
        self.hit_timer = 0.0
        self.message_text = ""
        self.message_sub = ""
        self.message_timer = 0.0

    # -- actualización ------------------------------------------------------

    def update(self, sim: ZombieSim, controls: Controls, dt: float, paused: bool) -> None:
        self.time += dt
        self.flash_alpha = max(0.0, self.flash_alpha - dt * 1.8)
        self.hit_timer = max(0.0, self.hit_timer - dt)
        self.message_timer = max(0.0, self.message_timer - dt)

        self._update_bars(sim)
        self._update_message(sim)
        self._update_threat(sim)
        self._update_flash(sim, paused)
        self._update_overlay(sim, paused)
        if sim.phase in ("wave", "break"):
            self._update_sensor(controls)
            self._update_hint(controls)
        else:
            self.texts["sensor"].setText("")
            self.texts["hint"].setText("")
            self.texts["hint2"].setText("")

        if sim.phase == "wave" and not paused:
            self.texts["crosshair"].setText("+")
            self.texts["crosshair"].setFg(CRIMSON if self.hit_timer > 0.0 else JADE)
            self.texts["hitmark"].setText("x" if self.hit_timer > 0.0 else "")
        else:
            self.texts["crosshair"].setText("")
            self.texts["hitmark"].setText("")

    # -- partes -------------------------------------------------------------

    def _show_gameplay(self, visible: bool) -> None:
        values = {
            "wave": self._wave_text,
            "score": self._score_text,
            "health": self._health_text,
            "health_bar": self._health_bar_text,
            "threats": self._threats_text,
            "weapon": self._weapon_text,
            "ammo": self._ammo_text,
            "reload": self._reload_text,
        }
        for key, value in values.items():
            self.texts[key].setText(value if visible else "")
        if not visible:
            for key in ("message", "message_sub", "sensor", "hint", "hint2", "low"):
                self.texts[key].setText("")

    def _show_title(self, visible: bool) -> None:
        for key in ("title", "subtitle", "title_a", "title_b", "title_c", "title_d", "title_start"):
            self.texts[key].setText(self._title_text(key) if visible else "")

    @staticmethod
    def _title_text(key: str) -> str:
        return {
            "title": "JUBILADOS ZOMBIES",
            "subtitle": "El club de jubilados fue invadido",
            "title_a": "SACUDÍ EL CELULAR  >  DISPARAR",
            "title_b": "GIRÁ A LA IZQUIERDA  >  RECARGAR",
            "title_c": "GIRÁ A LA DERECHA  >  CAMBIAR DE ARMA",
            "title_d": "TELÉFONO DE COSTADO | STICK MOVER | ARRASTRÁ APUNTAR | SIN SENSORES: X / L1 / R1",
            "title_start": "SACUDÍ O APRETÁ X PARA EMPEZAR",
        }[key]

    def _show_gameover(self, visible: bool) -> None:
        for key in ("gameover", "gameover_stats", "gameover_prompt"):
            self.texts[key].setText("" if not visible else self._gameover_text(key))

    def _gameover_text(self, key: str) -> str:
        return {
            "gameover": "TE ALCANZARON",
            "gameover_stats": self._gameover_stats,
            "gameover_prompt": "X / SACUDIDA PARA OTRA TANDA",
        }[key]

    def _update_overlay(self, sim: ZombieSim, paused: bool) -> None:
        if sim.phase == "title":
            self._overlay.set_color(Vec4(DARK[0], DARK[1], DARK[2], 0.58))
            self._show_title(True)
            self._show_gameplay(False)
            self._show_gameover(False)
            self.texts["pause"].setText("")
            self.texts["pause_sub"].setText("")
            return

        self._show_title(False)
        if sim.phase == "gameover":
            self._overlay.set_color(Vec4(DARK[0], DARK[1], DARK[2], 0.66))
            self._gameover_stats = (
                f"PUNTOS {sim.score}  |  ZOMBIS {sim.kills}  |  OLEADA {sim.wave}"
            )
            self._show_gameplay(True)
            self._show_gameover(True)
            self.texts["pause"].setText("")
            self.texts["pause_sub"].setText("")
            return

        self._show_gameover(False)
        if paused:
            self._overlay.set_color(Vec4(DARK[0], DARK[1], DARK[2], 0.60))
            self.texts["pause"].setText("PAUSA")
            self.texts["pause_sub"].setText("OPTIONS PARA SEGUIR")
            self.texts["message"].setText("")
            self.texts["message_sub"].setText("")
            self.texts["low"].setText("")
        else:
            self._overlay.set_color(OVERLAY_CLEAR)
            self.texts["pause"].setText("")
            self.texts["pause_sub"].setText("")
        self._show_gameplay(True)

    def _update_bars(self, sim: ZombieSim) -> None:
        ratio = max(0.0, min(1.0, sim.player.health / 100.0))
        filled = round(ratio * 10.0)
        bar = "#" * filled + "." * (10 - filled)
        self._health_text = f"SALUD {math.ceil(sim.player.health):3d}"
        self._health_bar_text = f"[{bar}]"
        color = JADE if ratio > 0.55 else (GOLD if ratio > 0.25 else CRIMSON)
        self.texts["health_bar"].setFg(color)
        self.texts["health"].setFg(CRIMSON if ratio <= 0.25 else CREAM)

        state = sim.weapons[sim.current_weapon]
        spec = sim.weapon
        self._weapon_text = spec.name
        if state.reload_timer > 0.0:
            self._ammo_text = f"{spec.short}  RECARGANDO"
            progress = int(sim.reload_progress * 10.0)
            self._reload_text = "[" + "#" * progress + "." * (10 - progress) + "]"
        else:
            self._ammo_text = f"{state.ammo:02d}/{spec.magazine:02d}"
            pips = 12
            filled = round(state.ammo / max(1, spec.magazine) * pips)
            self._reload_text = "|" * filled + "." * (pips - filled)
        self.texts["ammo"].setFg(CRIMSON if state.ammo == 0 else BONE)
        self.texts["reload"].setFg(GOLD if state.reload_timer > 0.0 else MUTED)

        self._wave_text = (
            f"OLEADA {sim.wave:02d}  |  {sim.zombie_count + len(sim.pending):02d} ZOMBIS"
        )
        self._score_text = f"PUNTOS {sim.score:06d}"
        self._threats_text = f"BAJAS {sim.kills:03d}"

        if sim.phase == "break":
            self._wave_text = f"OLEADA {sim.wave:02d} LIMPIA  |  PREPARATE"

    def _update_message(self, sim: ZombieSim) -> None:
        if sim.phase not in ("wave", "break"):
            self.texts["message"].setText("")
            self.texts["message_sub"].setText("")
            return
        if self.message_timer > 0.0:
            self.texts["message"].setText(self.message_text)
            self.texts["message"].setFg(self.message_color)
            self.texts["message_sub"].setText(self.message_sub)
            self.texts["message_sub"].setFg(CREAM)
            return
        if sim.phase == "break":
            self.texts["message"].setText("OLEADA COMPLETA")
            self.texts["message"].setFg(JADE)
            self.texts["message_sub"].setText("SALUD RECUPERADA | PREPARATE")
            self.texts["message_sub"].setFg(CREAM)
            return
        state = sim.weapons[sim.current_weapon]
        if state.reload_timer > 0.0:
            self.texts["message"].setText("RECARGANDO...")
            self.texts["message"].setFg(GOLD)
            self.texts["message_sub"].setText("")
            return
        if state.ammo == 0:
            self.texts["message"].setText("")
            self.texts["message_sub"].setText(
                "SIN MUNICIÓN | GIRÁ A LA IZQUIERDA O L1 PARA RECARGAR"
            )
            self.texts["message_sub"].setFg(CRIMSON)
            return
        self.texts["message"].setText("")
        self.texts["message_sub"].setText("")

    def _update_threat(self, sim: ZombieSim) -> None:
        nearest = sim.nearest_zombie()
        if nearest is None or sim.phase not in ("wave", "break"):
            self.texts["threat_left"].setText("")
            self.texts["threat_right"].setText("")
            return
        distance = math.hypot(nearest.x - sim.player.x, nearest.y - sim.player.y)
        relative = wrap_degrees(
            angle_to((sim.player.x, sim.player.y), (nearest.x, nearest.y)) - sim.player.heading
        )
        if abs(relative) < 22.0:
            self.texts["threat_left"].setText("")
            self.texts["threat_right"].setText("")
            return
        text = f"<< {distance:4.1f}m" if relative > 0.0 else f"{distance:4.1f}m >>"
        color = CRIMSON if distance < 6.0 else GOLD
        key = "threat_left" if relative > 0.0 else "threat_right"
        other = "threat_right" if key == "threat_left" else "threat_left"
        self.texts[other].setText("")
        self.texts[key].setText(text)
        self.texts[key].setFg(color)

    def _update_flash(self, sim: ZombieSim, paused: bool) -> None:
        ratio = max(0.0, sim.player.health / 100.0)
        pulse = 0.0
        if ratio <= 0.25 and sim.phase == "wave" and not paused:
            pulse = (math.sin(self.time * 6.0) + 1.0) * 0.5 * 0.12
        alpha = max(pulse, self.flash_alpha)
        self._flash.set_color(Vec4(0.55, 0.02, 0.03, min(0.42, alpha)))
        if ratio <= 0.25 and sim.phase == "wave" and not paused:
            self.texts["low"].setText("¡SALUD CRÍTICA!")
        else:
            self.texts["low"].setText("")

    def _update_sensor(self, controls: Controls) -> None:
        if controls.sensors:
            sensor = (
                "SENSORES OK | SACUDIDA + GIRO"
                if controls.gyro
                else "SIN GIRO | SACUDÍ O X | L1 / R1"
            )
        else:
            sensor = "SIN SENSORES | X DISPARA | L1 RECARGA | R1 ARMA"
        if controls.invert:
            sensor += " | GIRO INVERTIDO (CUADRADO)"
        self.texts["sensor"].setText(sensor)

    def _update_hint(self, controls: Controls) -> None:
        if controls.gyro:
            self.texts["hint"].setText(
                "SACUDÍ > DISPARAR | GIRÁ < RECARGAR | GIRÁ > ARMA"
            )
        else:
            self.texts["hint"].setText("X DISPARAR | L1 RECARGAR | R1 CAMBIAR")
        self.texts["hint2"].setText("STICK MOVER | ARRASTRÁ APUNTAR")

    def destroy(self) -> None:
        for text in self.texts.values():
            text.remove_node()
        self.texts.clear()
        self._overlay.remove_node()
        self._flash.remove_node()
