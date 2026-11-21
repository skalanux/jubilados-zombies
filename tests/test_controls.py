"""Pruebas puras de gestos de plataforma: sin Panda3D ni celular."""

from __future__ import annotations

from toxinator.api import ControllerFrame, Gesture, TouchPoint

from jubilados_zombies.controls import ControlReader


def frame(
    *,
    accel: tuple[float, float, float] = (0.0, 0.0, 9.81),
    gyro: tuple[float, float, float] = (0.0, 0.0, 0.0),
    orientation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    buttons: frozenset[str] = frozenset(),
    pointer: tuple[float, float] | None = None,
    touch: tuple[TouchPoint, ...] = (),
    axes: dict[str, float] | None = None,
) -> ControllerFrame:
    return ControllerFrame(
        controller_id="test",
        timestamp=0.0,
        buttons=buttons,
        axes=axes or {},
        accel=accel,
        gyro=gyro,
        orientation=orientation,
        pointer=pointer,
        touch=touch,
    )


def gesture(
    name: str, direction: str = "none", *, intensity: float = 0.5
) -> Gesture:
    return Gesture(
        slot=0,
        controller_id="test",
        name=name,
        direction=direction,
        intensity=intensity,
        timestamp=0.0,
    )


def test_shake_gesture_fires() -> None:
    reader = ControlReader()
    controls = reader.update(frame(), [gesture("shake")], 0.05)
    assert controls.fire is True
    assert controls.fire_pressed is True

    again = reader.update(frame(), [], 0.05)
    assert again.fire is False


def test_calm_frames_do_not_fire() -> None:
    reader = ControlReader()
    for _ in range(20):
        controls = reader.update(frame(), [], 0.05)
    assert controls.fire is False


def test_twist_ccw_reloads() -> None:
    reader = ControlReader()
    controls = reader.update(frame(), [gesture("twist", "ccw")], 0.05)
    assert controls.reload is True
    assert controls.swap is False


def test_twist_cw_swaps_weapon() -> None:
    reader = ControlReader()
    controls = reader.update(frame(), [gesture("twist", "cw")], 0.05)
    assert controls.swap is True
    assert controls.reload is False


def test_square_inverts_twist_mapping() -> None:
    reader = ControlReader()
    toggled = reader.update(frame(buttons=frozenset({"square"})), [], 0.05)
    assert toggled.invert is True
    assert toggled.invert_toggled is True

    controls = reader.update(frame(), [gesture("twist", "ccw")], 0.05)
    assert controls.swap is True
    assert controls.reload is False


def test_buttons_fire_on_edge_only() -> None:
    reader = ControlReader()
    first = reader.update(frame(buttons=frozenset({"l1"})), [], 0.05)
    second = reader.update(frame(buttons=frozenset({"l1"})), [], 0.05)
    assert first.reload is True
    assert second.reload is False

    swap = reader.update(frame(buttons=frozenset({"r1"})), [], 0.05)
    assert swap.swap is True


def test_cross_fires_while_held() -> None:
    reader = ControlReader()
    first = reader.update(frame(buttons=frozenset({"cross"})), [], 0.05)
    second = reader.update(frame(buttons=frozenset({"cross"})), [], 0.05)
    assert first.fire is True and first.fire_pressed is True
    assert second.fire is True and second.fire_pressed is False


def test_twist_does_not_fire_and_shake_does_not_reload() -> None:
    reader = ControlReader()
    controls = reader.update(frame(), [gesture("twist", "cw")], 0.05)
    assert controls.fire is False
    assert controls.reload is False
    assert controls.swap is True

    controls = reader.update(frame(), [gesture("shake")], 0.05)
    assert controls.fire is True
    assert controls.reload is False


def test_pointer_drag_ignores_first_sample_and_new_touches() -> None:
    reader = ControlReader()
    first = reader.update(frame(pointer=(0.5, 0.5)), [], 0.05)
    second = reader.update(frame(pointer=(0.6, 0.4)), [], 0.05)
    assert first.look_dx == 0.0 and first.look_dy == 0.0
    assert second.look_dx > 0.0
    assert second.look_dy < 0.0

    touch_a = reader.update(
        frame(pointer=(0.2, 0.2), touch=(TouchPoint(1, 0.2, 0.2),)), [], 0.05
    )
    touch_b = reader.update(
        frame(pointer=(0.7, 0.7), touch=(TouchPoint(2, 0.7, 0.7),)), [], 0.05
    )
    assert touch_a.look_dx == 0.0
    assert touch_b.look_dx == 0.0
