"""Lectura de gestos y controles, sin Panda3D.

El esquema principal usa los gestos de plataforma (ADR-0010):

- ``shake`` (sacudir el teléfono) dispara;
- ``twist`` (girar la muñeca) recarga a un lado y cambia de arma al otro.

El stick mueve y arrastrar sobre el touchpad apunta. Sin sensores todo sigue
jugable con ×, L1 y R1. El lector nunca bloquea ni lanza.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from toxinator.api import ControllerFrame, Gesture

POINTER_LIMIT = 0.14
LOOK_DEADZONE = 0.0015


@dataclass(frozen=True, slots=True)
class Controls:
    move_x: float = 0.0
    move_y: float = 0.0
    look_dx: float = 0.0
    look_dy: float = 0.0
    fire: bool = False
    fire_pressed: bool = False
    reload: bool = False
    swap: bool = False
    pause: bool = False
    invert_toggled: bool = False
    gesture_turn: float = 0.0
    shake: float = 0.0
    sensors: bool = False
    gyro: bool = False
    invert: bool = False


class ControlReader:
    """Convierte frames y gestos del celular en acciones estables para el juego."""

    def __init__(self) -> None:
        self.invert = False
        self.sensors = False
        self.gyro_seen = False
        self._cross_down = False
        self._l1_down = False
        self._r1_down = False
        self._options_down = False
        self._square_down = False
        self._pointer: tuple[float, float] | None = None
        self._touch_id: int | None = None

    # -- estado -------------------------------------------------------------

    def reset(self) -> None:
        self.sensors = False
        self.gyro_seen = False
        self._cross_down = False
        self._l1_down = False
        self._r1_down = False
        self._options_down = False
        self._square_down = False
        self._pointer = None
        self._touch_id = None

    def update(
        self,
        frame: ControllerFrame | None,
        gestures: Sequence[Gesture],
        dt: float,
    ) -> Controls:
        if frame is None:
            self._pointer = None
            self._touch_id = None
            self._cross_down = self._l1_down = self._r1_down = False
            self._options_down = self._square_down = False
            return Controls(sensors=self.sensors, gyro=self.gyro_seen, invert=self.invert)

        reload_pressed = self._edge(frame, "l1")
        swap_pressed = self._edge(frame, "r1")
        pause_pressed = self._edge(frame, "options")
        square_pressed = self._edge(frame, "square")
        cross_pressed = self._edge(frame, "cross")
        cross_held = frame.button("cross")

        if square_pressed:
            self.invert = not self.invert

        accel_norm = math.sqrt(sum(value * value for value in frame.accel))
        gyro_norm = math.sqrt(sum(value * value for value in frame.gyro))
        orientation_active = any(abs(value) > 0.5 for value in frame.orientation)
        if accel_norm > 0.5 or gyro_norm > 0.01 or orientation_active:
            self.sensors = True
        if gyro_norm > 0.02:
            self.gyro_seen = True

        shake_fired = any(gesture.name == "shake" for gesture in gestures)
        twist = next((gesture for gesture in gestures if gesture.name == "twist"), None)
        reload_gesture = False
        swap_gesture = False
        gesture_turn = 0.0
        if twist is not None:
            if twist.direction == "ccw":
                reload_gesture = not self.invert
                swap_gesture = self.invert
                gesture_turn = -1.0
            else:  # "cw"
                swap_gesture = not self.invert
                reload_gesture = self.invert
                gesture_turn = 1.0

        look_dx, look_dy = self._pointer_delta(frame)
        return Controls(
            move_x=max(-1.0, min(1.0, frame.axis("move_x"))),
            move_y=max(-1.0, min(1.0, frame.axis("move_y"))),
            look_dx=look_dx,
            look_dy=look_dy,
            fire=shake_fired or cross_held,
            fire_pressed=shake_fired or cross_pressed,
            reload=reload_gesture or reload_pressed,
            swap=swap_gesture or swap_pressed,
            pause=pause_pressed,
            invert_toggled=square_pressed,
            gesture_turn=gesture_turn,
            shake=1.0 if shake_fired else 0.0,
            sensors=self.sensors,
            gyro=self.gyro_seen,
            invert=self.invert,
        )

    # -- helpers ------------------------------------------------------------

    def _edge(self, frame: ControllerFrame, name: str) -> bool:
        attr = {
            "cross": "_cross_down",
            "l1": "_l1_down",
            "r1": "_r1_down",
            "options": "_options_down",
            "square": "_square_down",
        }[name]
        down = frame.button(name)
        was = getattr(self, attr)
        setattr(self, attr, down)
        return down and not was

    def _pointer_delta(self, frame: ControllerFrame) -> tuple[float, float]:
        pointer = frame.pointer
        if pointer is None:
            self._pointer = None
            self._touch_id = None
            return 0.0, 0.0

        touch_id = frame.touch[0].id if frame.touch else None
        if touch_id is not None and touch_id != self._touch_id:
            self._touch_id = touch_id
            self._pointer = pointer
            return 0.0, 0.0

        previous = self._pointer
        self._pointer = pointer
        if previous is None:
            return 0.0, 0.0
        dx = max(-POINTER_LIMIT, min(POINTER_LIMIT, pointer[0] - previous[0]))
        dy = max(-POINTER_LIMIT, min(POINTER_LIMIT, pointer[1] - previous[1]))
        if abs(dx) < LOOK_DEADZONE:
            dx = 0.0
        if abs(dy) < LOOK_DEADZONE:
            dy = 0.0
        return dx, dy
