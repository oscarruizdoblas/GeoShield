# GeoShield — Resumen Día 2 (2026-11-04)

**Asignatura:** Cyberphysical and IoT Security (Erasmus, Padova). **Equipo:** Ignacio (simulación PX4/Gazebo + ataque de spoofing) y Oscar (QGC, geofencing, detección, análisis, docs).
**Objetivo del proyecto:** en SIMULACIÓN (sin hardware ni radio real) estudiar ataques de GPS spoofing contra un dron autónomo y construir detección + geofencing resiliente.

Todo el código vive en WSL `~/geoshield/` (copia en `GeoShield/scripts/`). Python = `/home/oruiz/yes/bin/python3`.

---

## 1. Escenario (coordenadas reales de Padova, verificadas en OpenStreetMap)

El dron sale de **A** y va a **B** (donde dan clase). La recta directa A→B **cruza Palazzo Bo** (universidad del centro histórico, zona prohibida), así que en vuelo normal debe rodearla por el camino más corto.

| Punto | Qué es | Lat, Lon |
|---|---|---|
| **A (salida = HOME)** | Riviera Paleocapa (San Giuseppe) | 45.4021, 11.8670 |
| **B (destino)** | Torre Archimede — Dip. Matematica "Tullio Levi-Civita" | 45.4113328, 11.8878209 |
| **Zona 1 (keep-out)** | Palazzo Bo (Universidad, centro) — r=220 m | 45.4067383, 11.8773940 |
| **Zona 2 (keep-out)** | Palazzo Liviano (Universidad, centro) — r=150 m | 45.4079860, 11.8714491 |
| **Keep-in (área operativa)** | r=1500 m | 45.40672, 11.87741 |

Fuente única: **`zones.py`** (de aquí salen mapa, geofence, planificador, detector y mundo 3D).

## 2. Geofencing

- Zonas keep-out circulares (exclusión) + keep-in (inclusión) → **`geoshield_padova.plan`** para QGroundControl (incluye además la ruta normal A→B).
- Mapa propio con zonas en rojo fuerte: **`mapa_padua.png`**, **`scenario_map.png`**.
- **Hallazgo de seguridad:** el geofence de PX4 **rechaza** la entrada normal/comandada en zonas keep-out, pero un flujo de setpoints **OFFBOARD** de velocidad metió al dron en la zona hasta 67 m **sin** disparar RTL → la defensa por geofence no basta (relevante frente al spoofing).

## 3. Planificación autónoma de ruta (evitar zonas)

- **`planner.py`** — ruta óptima C→D que evita las zonas (grafo de visibilidad + Dijkstra). **General**: cualquier par de puntos, no rutas fijas. Margen de seguridad = **75 m** alrededor de cada zona.
- **`plan_and_fly.py`** — planifica y **vuela** la ruta: `python3 plan_and_fly.py` (A→B) o `... Clat Clon Dlat Dlon` (cualquier C→D); `--dry` solo planifica.
- La inteligencia de esquivar y optimizar está en nuestro módulo (lado de tierra); PX4 solo ejecuta los waypoints y su geofence solo bloquea.
- **Validado end-to-end:** vuelo A→B real → el dron rodeó Palazzo Bo (acercamiento mínimo medido; no entró).

## 4. Captura y análisis de telemetría

- **`logger.py`** / **`fly_and_log.py`** — graban a CSV: GPS crudo (`GPS_RAW_INT`), posición EKF (`GLOBAL_POSITION_INT`), NED local, ratios de innovación (`ESTIMATOR_STATUS`).
- **`analyze.py`** — estadísticas (media/std/p50/p99/max) + histogramas (**`baseline_hist.png`**).
- **Señales base (vuelo limpio, sin spoofing):** distancia GPS↔EKF media 0,39 m (máx 1,0); ratios de innovación < 0,11; salto de posición 0,55 m/muestra (vel. aparente máx 6,4 m/s).

## 5. Detección de spoofing

- **`detector.py`** — monitor en vivo (MAVLink 14540). Vigila 4 señales y lanza alertas con marca de tiempo (`logs/detector_*/alerts.csv`). Pilla spoofing **brusco** (teletransporte) y **gradual** (deriva lenta).
- **Umbrales** (calibrados con vuelo base; margen para 0 falsos positivos):
  - Divergencia GPS↔EKF > 3 m · Divergencia > 1,5 m sostenida ≥ 3 s · Innovación pos/vel > 0,5 · Salto > 15 m/s aparente.
- **`check_fp.py`** — validación: **0 falsos positivos** sobre vuelos limpios completos.

## 6. Visualización 3D (Gazebo)

- Mundo **`padova.sdf`** con suelo = textura OSM real centrada en la ruta A↔B, origen en el HOME nuevo (dron y mapa **sincronizados**), zonas rojas translúcidas, edificios y marcadores A (verde) / B (amarillo).
- Generado por **`make_texture.py`** + **`build_world.py`**. Lanzar: `run_padova.sh` (SITL headless) + `run_gui.sh` (ventana) + `follow_cam.sh` (cámara sigue al dron).
- Nota WSL: Gazebo se lanza en **modo dual** (servidor headless + ventana aparte, render por software) para no romper el lockstep. QGC es el visor principal (mapa real + geofence + dron).

## 7. Entregables (carpeta del proyecto)

`zones.py`, `planner.py`, `plan_and_fly.py`, `detector.py`, `analyze.py`, `logger.py`, `check_fp.py`, `make_qgc_plan.py` (en `scripts/`) · `geoshield_padova.plan` · `mapa_padua.png`, `scenario_map.png`, `trayectoria.png`, `baseline_hist.png` · `GeoShield_traspaso_Ignacio.md`.

## 8. Pendiente (Día 3+)

1. **Ataque de spoofing (Ignacio):** inyectar GPS falso para que el dron **entre** en Palazzo Bo (brusco y gradual) y ver al **detector dispararse**. Coordinado vía `GeoShield_traspaso_Ignacio.md`.
2. Grabar los dos vuelos de la demo: normal (esquiva) vs spoofing (atraviesa).
3. Memoria/vídeo final.
