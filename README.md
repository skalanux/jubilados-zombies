# Jubilados Zombies

Un FPS de oleadas para Toxinator: el club de jubilados quedó rodeado de
zombis. Apuntás con el dedo, te movés con el stick y usás el teléfono de
costado como si fuera el arma.

## Gestos

| Gesto | Acción |
|---|---|
| **Sacudir** el teléfono | Disparar |
| **Girar a la izquierda** | Recargar |
| **Girar a la derecha** | Cambiar de arma |
| Stick izquierdo | Moverte |
| Arrastrar sobre el touchpad | Apuntar |
| **×** / **L1** / **R1** | Disparar / recargar / cambiar (sin sensores) |
| **□** | Invertir el sentido del giro |
| **OPTIONS** | Pausa (la plataforma sigue siendo dueña de ○) |

Los gestos de giro usan el giroscopio y funcionan sin calibrar el teléfono.
La sacudida usa el acelerómetro. Si el navegador no entrega sensores (por
ejemplo en HTTP), todo sigue jugable con ×, L1 y R1; el HUD lo avisa.

## Instalar y jugar

El juego ya vive en `~/Projects/toxinator-games/jubilados-zombies`, así que la
consola lo descubre al iniciar. Si lo movés a otro lado, enlazalo:

```bash
cd /home/ska/Projects/toxinator
uv run toxinator install /ruta/a/jubilados-zombies
uv run toxinator play jubilados-zombies --cloudflare
```

`--cloudflare` (o `--https`) es lo que habilita los sensores del celular. En
HTTP el juego sigue andando con **× / L1 / R1**, pero no hay sacudida ni giro.
Si el teléfono entra por la LAN, agregá `--host 0.0.0.0` (o la IP de la máquina)
para que el QR no apunte a loopback.

Para probar sin celular, `--demo` inyecta movimiento sintético. Como el demo no
sacude el teléfono, los disparos salen con **×** retenida.

```bash
uv run toxinator play jubilados-zombies --demo
uv run toxinator play jubilados-zombies --demo --offscreen \
  --screenshot /tmp/jubilados.png --screenshot-after 3 --seconds 5
```

## Qué hay adentro

- Tres armas con cargador, cadencia y recarga propias: revólver, escopeta y
  subfusil.
- Oleadas de caminantes, corredores y tanques. La salud se recupera un poco al
  limpiar una oleada.
- Colisiones, cobertura que bloquea tiros, ayuda de puntería, sangre, impactos,
  barras de salud sobre los zombis y un arma en primera persona.
- HUD con salud, munición, puntaje, bajas, aviso de recarga y una flecha para
  ubicar al zombi más cercano.

## Estructura

```text
src/jubilados_zombies/
├── __init__.py     # create_game(manifest)
├── manifest.toml   # perfil landscape + etiquetas del mando
├── game.py         # ciclo de vida, cámara, eventos y feedback del celular
├── controls.py     # gestos puros (sacudida + giro), sin Panda3D
├── sim.py          # armas, oleadas, IA, colisiones y puntaje, sin Panda3D
├── scene.py        # patio 3D, zombis, armas y efectos
└── hud.py          # textos, barras y pantallas
tests/
├── test_controls.py
└── test_sim.py
```

## Reglas de la plataforma

- Solo se importa `toxinator.api` del runtime.
- No se crea `ShowBase`, ventanas ni `run()` propios.
- El input sale de `ctx.input_state.primary_frame()`; ○ queda reservado.
- Todo lo visual cuelga de `ctx.scene` / `ctx.ui` y se limpia en `stop`
  (incluida el arma colgada de la cámara y el estado de la lente).

## Chequeos

Con el venv de la consola:

```bash
cd /home/ska/Projects/toxinator-games/jubilados-zombies
/home/ska/Projects/toxinator/.venv/bin/ruff check src tests
/home/ska/Projects/toxinator/.venv/bin/mypy
/home/ska/Projects/toxinator/.venv/bin/python -m pytest -q
```
