from __future__ import annotations

from toxinator.api import Game, GameManifest

from .game import JubiladosZombies


def create_game(manifest: GameManifest) -> Game:
    return JubiladosZombies(manifest)
