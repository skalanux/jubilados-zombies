"""Escena 3D del club de jubilados: patio, zombis, armas y efectos."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from panda3d.core import (
    AmbientLight,
    CardMaker,
    DirectionalLight,
    Fog,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    PointLight,
    TextNode,
    Vec3,
    Vec4,
)

from .sim import OBSTACLES, PLAYER_EYE, Rect, Zombie, ZombieSim

type Color = Vec4

FLOOR = Vec4(0.175, 0.190, 0.165, 1.0)
FLOOR_LINE = Vec4(0.205, 0.218, 0.185, 1.0)
WALL = Vec4(0.300, 0.325, 0.285, 1.0)
WALL_TOP = Vec4(0.180, 0.205, 0.180, 1.0)
WOOD = Vec4(0.430, 0.300, 0.175, 1.0)
WOOD_DARK = Vec4(0.250, 0.170, 0.100, 1.0)
STONE = Vec4(0.510, 0.520, 0.470, 1.0)
STONE_DARK = Vec4(0.330, 0.345, 0.315, 1.0)
HEDGE = Vec4(0.140, 0.300, 0.145, 1.0)
HEDGE_2 = Vec4(0.185, 0.380, 0.180, 1.0)
WATER = Vec4(0.090, 0.240, 0.245, 1.0)
BANNER_RED = Vec4(0.430, 0.075, 0.075, 1.0)
BANNER_GOLD = Vec4(0.780, 0.590, 0.200, 1.0)
LAMP = Vec4(1.0, 0.790, 0.410, 1.0)
BLOOD = Vec4(0.380, 0.020, 0.030, 1.0)
BLOOD_BRIGHT = Vec4(0.650, 0.035, 0.045, 1.0)
GUN_STEEL = Vec4(0.430, 0.455, 0.475, 1.0)
GUN_DARK = Vec4(0.155, 0.165, 0.175, 1.0)
GUN_WOOD = Vec4(0.495, 0.295, 0.135, 1.0)
FLASH = Vec4(1.0, 0.850, 0.330, 1.0)
INK = Vec4(0.010, 0.015, 0.012, 1.0)

ZOMBIE_LOOKS: dict[str, dict[str, Color]] = {
    "caminante": {
        "shirt": Vec4(0.390, 0.430, 0.320, 1.0),
        "pants": Vec4(0.155, 0.165, 0.145, 1.0),
        "skin": Vec4(0.590, 0.650, 0.455, 1.0),
        "hair": Vec4(0.760, 0.755, 0.700, 1.0),
        "accent": Vec4(0.780, 0.680, 0.220, 1.0),
    },
    "corredor": {
        "shirt": Vec4(0.520, 0.190, 0.160, 1.0),
        "pants": Vec4(0.135, 0.150, 0.155, 1.0),
        "skin": Vec4(0.560, 0.690, 0.470, 1.0),
        "hair": Vec4(0.480, 0.460, 0.420, 1.0),
        "accent": Vec4(0.900, 0.780, 0.300, 1.0),
    },
    "tanque": {
        "shirt": Vec4(0.215, 0.295, 0.235, 1.0),
        "pants": Vec4(0.110, 0.120, 0.115, 1.0),
        "skin": Vec4(0.520, 0.610, 0.410, 1.0),
        "hair": Vec4(0.690, 0.680, 0.630, 1.0),
        "accent": Vec4(0.850, 0.600, 0.180, 1.0),
    },
}


@dataclass(slots=True)
class ZombieView:
    root: NodePath
    head: NodePath
    arm_l: NodePath
    arm_r: NodePath
    leg_l: NodePath
    leg_r: NodePath
    eyes: tuple[NodePath, NodePath]
    badge: NodePath
    hp_bg: NodePath
    hp_fill: NodePath


@dataclass(slots=True)
class Particle:
    node: NodePath
    vx: float
    vy: float
    vz: float
    life: float
    max_life: float
    gravity: float


class GameScene:
    """Todo lo que se ve en 3D, colgado de ``ctx.scene``."""

    def __init__(self, base: Any, root: NodePath) -> None:
        self.base = base
        self.root = root
        self.rng = random.Random(4242)
        self.world = root.attach_new_node("club-world")
        self.props = root.attach_new_node("club-props")
        self.zombies_root = root.attach_new_node("club-zombies")
        self.fx_root = root.attach_new_node("club-fx")
        self._box_model = base.loader.loadModel("models/box")
        self._sphere_model = base.loader.loadModel("models/misc/sphere")
        self._views: dict[int, ZombieView] = {}
        self._particles: list[Particle] = []
        self._stains: list[NodePath] = []
        self._time = 0.0
        self._current_weapon = -1
        self._recoil = 0.0
        self._swap_dip = 0.0
        self._flash_timer = 0.0
        self.gun: NodePath | None = None
        self.gun_groups: dict[str, NodePath] = {}
        self.gun_flash: NodePath | None = None
        self.lamp_node: NodePath | None = None
        self._build_lights()
        self._build_arena()
        self._build_fixtures()
        self._build_gun()

    # -- construcción -------------------------------------------------------

    def _box(
        self,
        parent: NodePath,
        center: tuple[float, float, float],
        size: tuple[float, float, float],
        color: Color,
        *,
        lit: bool = False,
    ) -> NodePath:
        model = self._box_model.copy_to(parent)
        model.set_texture_off(1)
        model.set_scale(*size)
        model.set_pos(
            center[0] - size[0] / 2.0,
            center[1] - size[1] / 2.0,
            center[2] - size[2] / 2.0,
        )
        model.set_color(color)
        if not lit:
            model.set_light_off(1)
        return model

    def _sphere(
        self,
        parent: NodePath,
        center: tuple[float, float, float],
        scale: float | tuple[float, float, float],
        color: Color,
        *,
        lit: bool = False,
    ) -> NodePath:
        model = self._sphere_model.copy_to(parent)
        model.set_texture_off(1)
        if isinstance(scale, (int, float)):
            model.set_scale(float(scale), float(scale), float(scale))
        else:
            model.set_scale(*scale)
        model.set_pos(*center)
        model.set_color(color)
        if not lit:
            model.set_light_off(1)
        return model

    def _card(
        self,
        parent: NodePath,
        center: tuple[float, float, float],
        width: float,
        height: float,
        color: Color,
        *,
        hpr: tuple[float, float, float] = (0.0, 0.0, 0.0),
        two_sided: bool = False,
        alpha: bool = False,
    ) -> NodePath:
        maker = CardMaker("club-card")
        maker.set_frame(-width / 2.0, width / 2.0, -height / 2.0, height / 2.0)
        card = parent.attach_new_node(maker.generate())
        card.set_pos(*center)
        card.set_hpr(*hpr)
        card.set_color(color)
        if two_sided:
            card.set_two_sided(True)
        if alpha or color.get_w() < 1.0:
            card.set_transparency(1)
        card.set_light_off(1)
        return card

    def _disc(
        self,
        parent: NodePath,
        center: tuple[float, float, float],
        radius: float,
        color: Color,
        *,
        segments: int = 28,
    ) -> NodePath:
        data = GeomVertexData("disc", GeomVertexFormat.get_v3n3c4(), Geom.UHStatic)
        vertex = GeomVertexWriter(data, "vertex")
        normal = GeomVertexWriter(data, "normal")
        colour = GeomVertexWriter(data, "color")

        vertex.add_data3(0.0, 0.0, 0.0)
        normal.add_data3(0.0, 0.0, 1.0)
        colour.add_data4(color)
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            vertex.add_data3(math.cos(angle) * radius, math.sin(angle) * radius, 0.0)
            normal.add_data3(0.0, 0.0, 1.0)
            colour.add_data4(color)

        triangles = GeomTriangles(Geom.UHStatic)
        for index in range(segments):
            triangles.add_vertices(0, index + 1, (index + 1) % segments + 1)
        triangles.close_primitive()
        geom = Geom(data)
        geom.add_primitive(triangles)
        node = GeomNode("disc")
        node.add_geom(geom)
        disc = parent.attach_new_node(node)
        disc.set_pos(*center)
        disc.set_two_sided(True)
        disc.set_light_off(1)
        if color.get_w() < 1.0:
            disc.set_transparency(1)
        return disc

    def _label(
        self,
        parent: NodePath,
        text: str,
        pos: tuple[float, float, float],
        scale: float,
        color: Color,
        hpr: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> NodePath:
        node = TextNode("club-label")
        node.set_text(text)
        node.set_align(TextNode.ACenter)
        node.set_text_color(color)
        label = parent.attach_new_node(node)
        label.set_pos(*pos)
        label.set_hpr(*hpr)
        label.set_scale(scale)
        label.set_light_off(1)
        return label

    def _rect_box(
        self,
        parent: NodePath,
        rect: Rect,
        z0: float,
        z1: float,
        color: Color,
        *,
        lit: bool = False,
    ) -> NodePath:
        x0, y0, x1, y1 = rect
        return self._box(
            parent,
            ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0),
            (x1 - x0, y1 - y0, z1 - z0),
            color,
            lit=lit,
        )

    # -- luces y atmósfera --------------------------------------------------

    def _build_lights(self) -> None:
        ambient = AmbientLight("club-ambient")
        ambient.set_color(Vec4(0.480, 0.510, 0.450, 1.0))
        self.root.set_light(self.root.attach_new_node(ambient))

        moon = DirectionalLight("club-moon")
        moon.set_color(Vec4(0.780, 0.860, 0.780, 1.0))
        moon_node = self.root.attach_new_node(moon)
        moon_node.set_hpr(35.0, -58.0, 0.0)
        self.root.set_light(moon_node)

        lamp = PointLight("club-torch")
        lamp.set_color(Vec4(1.0, 0.860, 0.620, 1.0))
        lamp.set_attenuation(Vec3(1.0, 0.025, 0.004))
        lamp.set_max_distance(26.0)
        self.lamp_node = self.root.attach_new_node(lamp)
        self.root.set_light(self.lamp_node)

        for pos, tint in (
            ((-8.0, -8.0, 3.4), Vec4(1.0, 0.680, 0.340, 1.0)),
            ((8.0, 7.0, 3.4), Vec4(0.760, 0.920, 0.660, 1.0)),
        ):
            bulb = PointLight(f"club-bulb-{pos[0]}")
            bulb.set_color(tint)
            bulb.set_attenuation(Vec3(1.0, 0.140, 0.035))
            bulb.set_max_distance(10.0)
            node = self.root.attach_new_node(bulb)
            node.set_pos(*pos)
            self.root.set_light(node)

        fog = Fog("club-fog")
        fog.set_color(Vec4(0.030, 0.055, 0.045, 1.0))
        fog.set_linear_range(7.0, 38.0)
        self.root.set_fog(fog)

    # -- arena --------------------------------------------------------------

    def _build_arena(self) -> None:
        self._box(self.world, (0.0, 0.0, -0.08), (31.0, 39.0, 0.16), FLOOR, lit=True)
        self._box(
            self.world,
            (0.0, 0.0, 4.22),
            (31.0, 39.0, 0.20),
            Vec4(0.095, 0.110, 0.095, 1.0),
            lit=True,
        )


        # Muro perimetral.
        for index in range(4):
            self._rect_box(self.world, OBSTACLES[index], 0.0, 4.2, WALL, lit=True)
        for z, color in ((2.55, WALL_TOP), (0.10, STONE_DARK)):
            self._box(self.world, (0.0, 18.56, z), (30.0, 0.05, 0.12), color)
            self._box(self.world, (0.0, -18.56, z), (30.0, 0.05, 0.12), color)
            self._box(self.world, (-14.56, 0.0, z), (0.05, 38.0, 0.12), color)
            self._box(self.world, (14.56, 0.0, z), (0.05, 38.0, 0.12), color)

        # Líneas del piso.
        for grid_y in range(-16, 19, 3):
            self._card(
                self.world,
                (0.0, float(grid_y), 0.015),
                29.6,
                0.045,
                FLOOR_LINE,
            )

        # Emblema central y manchas viejas.
        self._disc(self.world, (0.0, 0.0, 0.018), 3.4, Vec4(0.470, 0.330, 0.100, 1.0))
        self._disc(self.world, (0.0, 0.0, 0.020), 3.12, FLOOR)
        for stain_x, stain_y in (
            (-9.0, -13.5),
            (7.0, -4.0),
            (-4.0, 11.0),
            (10.0, 14.0),
            (-12.0, 4.0),
        ):
            self._disc(
                self.world,
                (stain_x, stain_y, 0.019),
                self.rng.uniform(0.45, 0.95),
                Vec4(0.250, 0.015, 0.020, 0.72),
            )

        self._build_obstacles()

    def _build_obstacles(self) -> None:
        # Fuente.
        fountain = OBSTACLES[4]
        self._rect_box(self.world, fountain, 0.0, 0.72, STONE_DARK, lit=True)
        x0, y0, x1, y1 = fountain
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        self._disc(self.world, (cx, cy, 0.76), 1.25, WATER)
        self._box(self.world, (cx, cy, 1.55), (0.52, 0.52, 1.55), STONE, lit=True)
        self._sphere(self.world, (cx, cy, 2.46), 0.42, STONE, lit=True)

        # Kiosco.
        kiosk = OBSTACLES[5]
        self._rect_box(self.world, kiosk, 0.0, 2.35, WOOD_DARK, lit=True)
        x0, y0, x1, y1 = kiosk
        self._box(
            self.world,
            ((x0 + x1) / 2.0, (y0 + y1) / 2.0, 2.55),
            (x1 - x0 + 0.5, y1 - y0 + 0.5, 0.12),
            BANNER_RED,
        )
        self._label(
            self.world,
            "KIOSCO",
            ((x0 + x1) / 2.0, y0 - 0.03, 1.85),
            0.62,
            BANNER_GOLD,
            hpr=(0.0, 90.0, 0.0),
        )
        for index in range(4):
            self._sphere(
                self.world,
                (x0 + 0.55 + index * 0.7, y0 + 0.35, 2.10),
                0.11,
                Vec4(0.35 + 0.12 * index, 0.78, 0.42, 1.0),
            )

        # Canteros.
        for index in (6, 7, 8, 9):
            rect = OBSTACLES[index]
            self._rect_box(self.world, rect, 0.0, 0.90, WOOD, lit=True)
            x0, y0, x1, y1 = rect
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            for offset in ((-0.45, -0.35), (0.38, 0.28), (0.0, 0.0)):
                self._sphere(
                    self.world,
                    (cx + offset[0], cy + offset[1], 1.32),
                    (0.62, 0.62, 0.50),
                    HEDGE if index % 2 == 0 else HEDGE_2,
                    lit=True,
                )

        # Biombos / tabiques.
        for index, color in ((10, BANNER_RED), (11, BANNER_GOLD)):
            rect = OBSTACLES[index]
            self._rect_box(self.world, rect, 0.0, 2.15, color, lit=True)
            x0, y0, x1, y1 = rect
            self._box(
                self.world,
                ((x0 + x1) / 2.0, (y0 + y1) / 2.0, 2.28),
                (x1 - x0 + 0.22, y1 - y0 + 0.22, 0.10),
                WOOD_DARK,
            )

        # Columnas.
        for index in (12, 13):
            rect = OBSTACLES[index]
            self._rect_box(self.world, rect, 0.0, 0.45, STONE_DARK, lit=True)
            self._rect_box(self.world, rect, 0.45, 3.0, STONE, lit=True)
            x0, y0, x1, y1 = rect
            self._box(
                self.world,
                ((x0 + x1) / 2.0, (y0 + y1) / 2.0, 3.10),
                (x1 - x0 + 0.24, y1 - y0 + 0.24, 0.18),
                STONE_DARK,
            )

        # Barra del norte.
        bar = OBSTACLES[14]
        self._rect_box(self.world, bar, 0.0, 1.15, WOOD_DARK, lit=True)
        self._rect_box(self.world, bar, 1.15, 2.10, WOOD, lit=True)
        x0, y0, x1, y1 = bar
        self._box(
            self.world,
            ((x0 + x1) / 2.0, (y0 + y1) / 2.0, 2.26),
            (x1 - x0 + 0.45, y1 - y0 + 0.45, 0.15),
            BANNER_GOLD,
        )
        self._label(
            self.world,
            "BINGO",
            ((x0 + x1) / 2.0, y0 - 0.04, 1.70),
            0.78,
            Vec4(0.960, 0.860, 0.560, 1.0),
            hpr=(0.0, 90.0, 0.0),
        )
        for index in range(7):
            self._sphere(
                self.world,
                (x0 + 0.55 + index * 0.62, y0 + 0.32, 2.28),
                0.10,
                Vec4(0.80, 0.42 + 0.06 * index, 0.18, 1.0),
            )

    def _build_fixtures(self) -> None:
        # Cartel del club en la pared norte.
        self._card(
            self.props,
            (0.0, 18.54, 2.95),
            11.5,
            1.8,
            BANNER_RED,
            hpr=(0.0, 90.0, 0.0),
            two_sided=False,
        )
        self._label(
            self.props,
            "CLUB DE JUBILADOS",
            (0.0, 18.49, 2.63),
            0.92,
            Vec4(0.980, 0.850, 0.500, 1.0),
            hpr=(0.0, 90.0, 0.0),
        )
        self._label(
            self.props,
            "PROHIBIDO MORIRSE",
            (0.0, 18.49, 3.25),
            0.40,
            Vec4(0.930, 0.900, 0.760, 1.0),
            hpr=(0.0, 90.0, 0.0),
        )

        # Carteles laterales, visibles desde la entrada.
        for y, text, base, ink in (
            (-6.0, "BINGO", BANNER_RED, BANNER_GOLD),
            (8.0, "SILENCIO", BANNER_GOLD, BANNER_RED),
        ):
            self._card(
                self.props,
                (14.54, y, 2.15),
                4.2,
                1.45,
                base,
                hpr=(-90.0, 90.0, 0.0),
            )
            self._label(
                self.props,
                text,
                (14.48, y, 1.92),
                0.58,
                ink,
                hpr=(-90.0, 90.0, 0.0),
            )
            self._card(
                self.props,
                (-14.54, y, 2.15),
                4.2,
                1.45,
                base,
                hpr=(90.0, 90.0, 0.0),
            )
            self._label(
                self.props,
                text,
                (-14.48, y, 1.92),
                0.58,
                ink,
                hpr=(90.0, 90.0, 0.0),
            )

        # Pasacalle sobre el patio.
        self._card(
            self.props,
            (0.0, 5.6, 3.05),
            8.6,
            0.95,
            BANNER_RED,
            hpr=(0.0, 90.0, 0.0),
        )
        self._label(
            self.props,
            "CLUB DE JUBILADOS",
            (0.0, 5.53, 2.86),
            0.52,
            Vec4(0.980, 0.850, 0.500, 1.0),
            hpr=(0.0, 90.0, 0.0),
        )
        for x in (-3.7, 3.7):
            self._box(self.props, (x, 5.60, 3.72), (0.022, 0.022, 0.42), INK)

        # Banderines y luces colgantes.
        for x in (-10.5, -5.25, 0.0, 5.25, 10.5):
            self._sphere(
                self.props,
                (x, 18.30, 3.86),
                0.075,
                LAMP,
            )
            self._box(self.props, (x, 18.56, 3.55), (0.022, 0.022, 0.62), INK)
        for x, y in ((-8.0, -8.0), (8.0, 7.0), (-9.0, 12.0), (7.0, -13.0)):
            self._box(self.props, (x, y, 3.62), (0.035, 0.035, 1.12), INK)
            self._sphere(self.props, (x, y, 3.02), 0.20, LAMP)
            self._sphere(self.props, (x, y, 3.02), 0.11, Vec4(1.0, 0.960, 0.760, 1.0))

        # Plantas secas y sillas contra la pared, sólo decorativas.
        for x, y, heading in ((-12.5, 7.0, 15), (12.7, -9.5, -20), (-12.7, -12.0, 5)):
            self._box(self.props, (x, y, 0.48), (0.52, 0.52, 0.52), WOOD_DARK)
            self._sphere(self.props, (x, y, 0.86), (0.45, 0.45, 0.32), HEDGE)
        for x in (-13.2, -12.4, 12.4, 13.2):
            self._box(self.props, (x, -16.5, 0.36), (0.70, 0.70, 0.12), WOOD)
            self._box(self.props, (x, -16.5, 0.70), (0.66, 0.12, 0.58), WOOD)

    # -- arma en primera persona -------------------------------------------

    def _build_gun(self) -> None:
        self.gun = self.base.cam.attach_new_node("jubilados-gun")
        self.gun.set_scale(0.62)
        self.gun.set_pos(0.235, 0.460, -0.275)
        self.gun.set_hpr(-3.0, 2.0, 0.0)
        self.gun.set_depth_test(False)
        self.gun.set_depth_write(False)
        self.gun.set_bin("fixed", 15)

        self.gun_groups["revolver"] = self._build_revolver(self.gun)
        self.gun_groups["escopeta"] = self._build_shotgun(self.gun)
        self.gun_groups["subfusil"] = self._build_smg(self.gun)

        self.gun_flash = self._sphere(self.gun, (0.0, 0.72, 0.05), 0.045, FLASH)
        self.gun_flash.set_scale(0.045)
        self.gun_flash.set_depth_test(False)
        self.gun_flash.set_depth_write(False)
        self.gun_flash.set_bin("fixed", 16)
        self.gun_flash.hide()

        for group in self.gun_groups.values():
            group.hide()

    def _build_revolver(self, parent: NodePath) -> NodePath:
        group = parent.attach_new_node("revolver")
        self._box(group, (0.0, 0.10, 0.0), (0.10, 0.22, 0.10), GUN_STEEL)
        self._box(group, (0.0, 0.31, 0.035), (0.050, 0.30, 0.052), GUN_STEEL)
        self._sphere(group, (0.0, 0.12, 0.015), (0.072, 0.072, 0.072), GUN_DARK)
        self._box(group, (0.0, -0.045, -0.11), (0.085, 0.10, 0.21), GUN_WOOD)
        self._box(group, (0.0, 0.045, -0.155), (0.065, 0.14, 0.045), GUN_DARK)
        self._box(group, (0.0, 0.33, 0.070), (0.018, 0.08, 0.018), GUN_DARK)
        return group

    def _build_shotgun(self, parent: NodePath) -> NodePath:
        group = parent.attach_new_node("escopeta")
        self._box(group, (0.0, 0.10, 0.0), (0.13, 0.34, 0.13), GUN_STEEL)
        self._box(group, (0.0, 0.45, 0.030), (0.058, 0.58, 0.058), GUN_STEEL)
        self._box(group, (0.0, 0.45, -0.035), (0.052, 0.58, 0.052), GUN_DARK)
        self._box(group, (0.0, 0.30, -0.075), (0.145, 0.20, 0.085), GUN_WOOD)
        self._box(group, (0.0, -0.19, -0.035), (0.13, 0.34, 0.23), GUN_WOOD)
        self._box(group, (0.0, -0.045, -0.15), (0.085, 0.12, 0.18), GUN_DARK)
        return group

    def _build_smg(self, parent: NodePath) -> NodePath:
        group = parent.attach_new_node("subfusil")
        self._box(group, (0.0, 0.16, 0.0), (0.13, 0.44, 0.13), GUN_STEEL)
        self._box(group, (0.0, 0.48, 0.02), (0.035, 0.28, 0.035), GUN_DARK)
        self._box(group, (0.0, 0.08, -0.16), (0.075, 0.19, 0.24), GUN_DARK)
        self._box(group, (0.0, -0.11, -0.02), (0.10, 0.18, 0.16), GUN_DARK)
        self._box(group, (0.0, 0.28, -0.065), (0.06, 0.22, 0.06), GUN_WOOD)
        self._box(group, (0.0, 0.50, 0.070), (0.015, 0.14, 0.015), GUN_STEEL)
        return group

    # -- efectos ------------------------------------------------------------

    def fire(self, kick: float) -> None:
        self._recoil = min(1.8, self._recoil + 0.48 + kick * 0.32)
        self._flash_timer = 0.055
        if self.gun_flash is not None:
            self.gun_flash.show()
            size = self.rng.uniform(0.030, 0.055)
            self.gun_flash.set_scale(size)
            self.gun_flash.set_hpr(0.0, 0.0, self.rng.uniform(0.0, 360.0))

    def blood(self, x: float, y: float, *, heavy: bool = False) -> None:
        count = 9 if heavy else 5
        for _ in range(count):
            z = self.rng.uniform(0.75, 1.45)
            speed = self.rng.uniform(1.0, 3.0 if not heavy else 4.2)
            angle = self.rng.uniform(0.0, math.tau)
            self._particle(
                (x, y, z),
                Vec3(math.cos(angle) * speed, math.sin(angle) * speed, self.rng.uniform(0.6, 2.2)),
                Vec4(BLOOD_BRIGHT if self.rng.random() < 0.35 else BLOOD),
                0.55 if heavy else 0.40,
                self.rng.uniform(0.040, 0.075),
            )

    def stain(self, x: float, y: float) -> None:
        radius = self.rng.uniform(0.40, 0.75)
        node = self._disc(
            self.fx_root,
            (x, y, 0.021),
            radius,
            Vec4(0.220, 0.010, 0.016, 0.62),
        )
        node.set_h(self.rng.uniform(0.0, 360.0))
        self._stains.append(node)
        if len(self._stains) > 36:
            self._stains.pop(0).remove_node()

    def _particle(
        self,
        position: tuple[float, float, float],
        velocity: Vec3,
        color: Color,
        life: float,
        size: float,
    ) -> None:
        node = self._sphere(
            self.fx_root,
            position,
            size,
            Vec4(color[0], color[1], color[2], 1.0),
        )
        node.set_transparency(1)
        node.set_bin("fixed", 25)
        node.set_depth_write(False)
        self._particles.append(
            Particle(node, velocity[0], velocity[1], velocity[2], life, life, 7.0)
        )

    def swap(self) -> None:
        self._swap_dip = 0.18

    # -- frame --------------------------------------------------------------

    def update(self, sim: ZombieSim, dt: float) -> None:
        self._time += dt
        if self.lamp_node is not None:
            flicker = 0.90 + 0.07 * math.sin(self._time * 11.0) + 0.03 * math.sin(self._time * 37.0)
            self.lamp_node.set_pos(
                sim.player.x,
                sim.player.y,
                PLAYER_EYE + 0.72,
            )
            self.lamp_node.set_color(Vec4(1.0, 0.820 * flicker, 0.560 * flicker, 1.0))

        self._sync_zombies(sim)
        self._update_particles(dt)
        self._update_gun(sim, dt)

    def _sync_zombies(self, sim: ZombieSim) -> None:
        alive_ids = {zombie.uid for zombie in sim.zombies}
        for uid in list(self._views):
            if uid not in alive_ids:
                self._views.pop(uid).root.remove_node()

        for zombie in sim.zombies:
            view = self._views.get(zombie.uid)
            if view is None:
                view = self._build_zombie(zombie)
                self._views[zombie.uid] = view
            self._pose_zombie(view, zombie)

    def _build_zombie(self, zombie: Zombie) -> ZombieView:
        look = ZOMBIE_LOOKS[zombie.kind]
        root = self.zombies_root.attach_new_node(f"zombie-{zombie.uid}")
        root.set_scale(zombie.scale)
        root.set_pos(zombie.x, zombie.y, 0.0)

        # Camisa y pantalón.
        self._box(root, (0.0, 0.0, 1.08), (0.54, 0.31, 0.72), look["shirt"], lit=True)
        self._box(root, (0.0, 0.0, 0.76), (0.42, 0.27, 0.24), look["pants"], lit=True)
        # Cabeza, cuello, pelo y ojos (pivote en el cuello para cabecear).
        self._box(root, (0.0, 0.02, 1.50), (0.16, 0.16, 0.12), look["skin"], lit=True)
        head = root.attach_new_node("head")
        head.set_pos(0.0, 0.0, 1.50)
        self._sphere(head, (0.0, 0.02, 0.14), (0.195, 0.195, 0.205), look["skin"], lit=True)
        self._sphere(head, (0.0, -0.015, 0.23), (0.190, 0.178, 0.095), look["hair"], lit=True)
        eye_l = self._sphere(head, (-0.070, 0.185, 0.165), 0.032, Vec4(1.0, 0.220, 0.120, 1.0))
        eye_r = self._sphere(head, (0.070, 0.185, 0.165), 0.032, Vec4(1.0, 0.220, 0.120, 1.0))
        # Badge de socio.
        badge = self._sphere(
            root, (0.17, 0.165, 1.19), (0.060, 0.015, 0.060), look["accent"]
        )

        arm_l = root.attach_new_node("arm-l")
        arm_l.set_pos(-0.355, 0.0, 1.36)
        arm_l.set_h(13.0)
        self._box(arm_l, (0.0, 0.0, -0.30), (0.145, 0.145, 0.60), look["shirt"], lit=True)
        self._sphere(arm_l, (0.0, 0.0, -0.62), 0.075, look["skin"], lit=True)
        arm_r = root.attach_new_node("arm-r")
        arm_r.set_pos(0.355, 0.0, 1.36)
        arm_r.set_h(-13.0)
        self._box(arm_r, (0.0, 0.0, -0.30), (0.145, 0.145, 0.60), look["shirt"], lit=True)
        self._sphere(arm_r, (0.0, 0.0, -0.62), 0.075, look["skin"], lit=True)
        if zombie.kind == "caminante":
            self._card(
                arm_l,
                (0.0, 0.05, -0.70),
                0.18,
                0.24,
                Vec4(0.90, 0.88, 0.72, 1.0),
                hpr=(80.0, 0.0, 0.0),
            )

        leg_l = root.attach_new_node("leg-l")
        leg_l.set_pos(-0.145, 0.0, 0.83)
        self._box(leg_l, (0.0, 0.0, -0.38), (0.185, 0.205, 0.74), look["pants"], lit=True)
        self._box(leg_l, (0.0, 0.055, -0.775), (0.19, 0.30, 0.10), GUN_DARK)
        leg_r = root.attach_new_node("leg-r")
        leg_r.set_pos(0.145, 0.0, 0.83)
        self._box(leg_r, (0.0, 0.0, -0.38), (0.185, 0.205, 0.74), look["pants"], lit=True)
        self._box(leg_r, (0.0, 0.055, -0.775), (0.19, 0.30, 0.10), GUN_DARK)

        hp_bg = self._card(
            root,
            (0.0, 0.0, 2.12),
            0.64,
            0.12,
            Vec4(0.010, 0.012, 0.010, 0.82),
            alpha=True,
        )
        hp_fill = self._card(
            root,
            (0.0, 0.0, 2.12),
            0.56,
            0.062,
            Vec4(0.880, 0.140, 0.120, 1.0),
        )
        for bar in (hp_bg, hp_fill):
            bar.set_billboard_point_eye()
            bar.set_depth_write(False)
            bar.set_bin("fixed", 26)
        hp_bg.set_bin("fixed", 25)

        return ZombieView(
            root, head, arm_l, arm_r, leg_l, leg_r, (eye_l, eye_r), badge, hp_bg, hp_fill
        )

    def _pose_zombie(self, view: ZombieView, zombie: Zombie) -> None:
        view.root.set_pos(zombie.x, zombie.y, 0.0)
        view.root.set_h(zombie.heading)
        if not zombie.alive:
            progress = 1.0 - max(0.0, zombie.death_timer) / 0.95
            progress = max(0.0, min(1.0, progress))
            view.root.set_p(-84.0 * progress)
            view.root.set_z(-0.48 * progress)
            view.root.set_color_scale(Vec4(1.0, 0.72, 0.72, 1.0))
            view.hp_bg.hide()
            view.hp_fill.hide()
            if progress >= 1.0:
                view.root.hide()
            return

        ratio = max(0.0, min(1.0, zombie.health / zombie.max_health))
        view.hp_bg.show()
        view.hp_fill.show()
        view.hp_fill.set_scale(max(0.02, ratio), 1.0, 1.0)
        if ratio > 0.55:
            view.hp_fill.set_color(Vec4(0.420, 0.940, 0.360, 1.0))
        elif ratio > 0.25:
            view.hp_fill.set_color(Vec4(0.980, 0.740, 0.200, 1.0))
        else:
            view.hp_fill.set_color(Vec4(0.920, 0.150, 0.120, 1.0))

        swing = math.sin(zombie.phase)
        view.leg_l.set_p(swing * 27.0)
        view.leg_r.set_p(-swing * 27.0)
        view.arm_l.set_p(63.0 + math.sin(zombie.phase + math.pi) * 8.0)
        view.arm_r.set_p(63.0 + math.sin(zombie.phase) * 8.0)
        view.head.set_h(math.sin(zombie.phase * 0.5) * 5.0)
        view.head.set_p(math.sin(zombie.phase * 0.7) * 3.0)
        flash = zombie.flash > 0.0
        view.root.set_color_scale(
            Vec4(2.2, 0.70, 0.70, 1.0) if flash else Vec4(1.0, 1.0, 1.0, 1.0)
        )
        pulse = 1.0 + 0.12 * math.sin(zombie.phase * 0.8)
        view.badge.set_scale(0.060 * pulse, 0.015 * pulse, 0.060 * pulse)

    def _update_particles(self, dt: float) -> None:
        alive: list[Particle] = []
        for particle in self._particles:
            particle.life -= dt
            if particle.life <= 0.0:
                particle.node.remove_node()
                continue
            particle.vz -= particle.gravity * dt
            position = particle.node.get_pos()
            particle.node.set_pos(
                position[0] + particle.vx * dt,
                position[1] + particle.vy * dt,
                position[2] + particle.vz * dt,
            )
            alpha = max(0.0, particle.life / particle.max_life)
            color = particle.node.get_color()
            particle.node.set_color(Vec4(color[0], color[1], color[2], alpha))
            alive.append(particle)
        self._particles = alive

    def _update_gun(self, sim: ZombieSim, dt: float) -> None:
        if self.gun is None:
            return
        if sim.current_weapon != self._current_weapon:
            for key, group in self.gun_groups.items():
                if key == sim.weapon.key:
                    group.show()
                else:
                    group.hide()
            self._current_weapon = sim.current_weapon
            if self.gun_flash is not None:
                tips = {
                    "revolver": (0.0, 0.50, 0.055),
                    "escopeta": (0.0, 0.78, 0.030),
                    "subfusil": (0.0, 0.64, 0.020),
                }
                self.gun_flash.set_pos(*tips[sim.weapon.key])

        self._recoil = max(0.0, self._recoil - dt * 5.2)
        self._swap_dip = max(0.0, self._swap_dip - dt)
        self._flash_timer = max(0.0, self._flash_timer - dt)
        if self.gun_flash is not None and self._flash_timer <= 0.0:
            self.gun_flash.hide()

        reloading = sim.reload_timer > 0.0
        reload_dip = 0.0
        if reloading:
            reload_dip = math.sin(min(1.0, sim.reload_progress) * math.pi) * 0.16
        bob = math.sin(sim.player.bob_phase) * 0.012 * sim.player.moving
        sway = math.sin(sim.player.bob_phase * 0.5) * 0.008
        base_x = 0.235 + sway
        base_y = 0.460 - self._recoil * 0.075 - self._swap_dip * 0.8
        base_z = -0.275 - self._recoil * 0.040 - reload_dip - self._swap_dip * 0.9 + bob
        self.gun.set_pos(base_x, base_y, base_z)
        self.gun.set_hpr(
            -3.0 + self._recoil * 2.0,
            2.0 - self._recoil * 7.0 - reload_dip * 35.0,
            0.0,
        )

    # -- limpieza -----------------------------------------------------------

    def destroy(self) -> None:
        if self.gun is not None:
            self.gun.remove_node()
            self.gun = None
        self.gun_groups.clear()
        self.gun_flash = None
        for view in self._views.values():
            view.root.remove_node()
        self._views.clear()
        for particle in self._particles:
            particle.node.remove_node()
        self._particles.clear()
        for stain in self._stains:
            stain.remove_node()
        self._stains.clear()
