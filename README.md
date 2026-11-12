# GeoShield

Proyecto de **Cyberphysical and IoT Security** (Erasmus, Padova). En **simulación** (PX4 SITL + Gazebo, sin hardware ni radio real) estudiamos ataques de **GPS spoofing** contra un dron autónomo y construimos **detección + geofencing resiliente**.

- **Oscar** (oscarruizdoblas): geofencing, planificación de ruta, detector, análisis, QGC, mundo 3D.
- **Ignacio**: simulación PX4/Gazebo y módulo de ataque (spoofing).

## Escenario (Padova, coords reales OSM)
- **A (salida / HOME):** Riviera Paleocapa — `45.4021, 11.8670`
- **B (destino):** Torre Archimede / Dip. Matematica "Tullio Levi-Civita" — `45.4113328, 11.8878209`
- **Zonas prohibidas (keep-out):** Palazzo Bo (`45.4067383, 11.8773940`, r=220 m) y Palazzo Liviano (`45.4079860, 11.8714491`, r=150 m)
- La recta A→B **cruza Palazzo Bo** → en vuelo normal lo rodea; el vuelo con spoofing lo hará entrar.

> **Fuente única de las zonas: [`scripts/zones.py`](scripts/zones.py).** Los dos usamos el mismo fichero.

## Estructura
- `scripts/` — todo el código (`zones.py`, `planner.py`, `plan_and_fly.py`, `detector.py`, `analyze.py`, `check_fp.py`, `logger.py`, `make_qgc_plan.py`, `make_texture.py`, `build_world.py`, `upload_fence.py`) y los lanzadores (`run_padova.sh`, `run_gui.sh`, `cam_birdseye.sh`, `follow_cam.sh`, `gz_env.sh`).
- `gazebo_assets/` — mundo 3D de Padova ya generado (`worlds/padova.sdf` + `models/padova_ground/`), para no re-descargar teselas.
- `geoshield_padova.plan` — geofence + misión A→B para QGroundControl.
- `GeoShield_traspaso_Ignacio.md` — **cómo montar el mismo mapa e interfaz** (empieza por aquí).

## Puesta en marcha rápida (WSL)
```bash
# 1) copiar el mundo 3D al arbol de PX4 (una vez)
cp gazebo_assets/worlds/padova.sdf   ~/PX4-Autopilot/Tools/simulation/gz/worlds/
mkdir -p ~/PX4-Autopilot/Tools/simulation/gz/models/padova_ground
cp gazebo_assets/models/padova_ground/*  ~/PX4-Autopilot/Tools/simulation/gz/models/padova_ground/

# 2) lanzar (3 terminales)
bash scripts/run_padova.sh      # SITL headless, mundo padova, HOME=A
bash scripts/run_gui.sh         # ventana de Gazebo
bash scripts/cam_birdseye.sh    # camara cenital siguiendo al dron

# 3) geofence en PX4 (QGC lo pinta solo) y vuelo de comprobacion A->B->A
python3 scripts/upload_fence.py
python3 scripts/plan_and_fly.py
```
Los scripts esperan estar en `~/geoshield/` (copia ahí el contenido de `scripts/`). En QGC también se puede cargar a mano: Plan → Open → `geoshield_padova.plan`.
Detalles y la opción de regenerar el mundo: ver `GeoShield_traspaso_Ignacio.md`.
