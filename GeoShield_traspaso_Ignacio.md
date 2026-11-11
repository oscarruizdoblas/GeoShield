# GeoShield — Traspaso a Ignacio (escenario, zonas y qué necesito de ti)

Hola Ignacio. Esto es lo que tengo montado por mi parte (geofencing + detección) y lo que necesito de la tuya (ataque de spoofing) para grabar los dos vuelos de la demo.

## 1. Escenario (coordenadas reales de Padova, verificadas en OpenStreetMap)

El dron sale de **A** y va a **B** (donde damos clase). La **recta directa A→B cruza Palazzo Bo** (universidad del centro histórico, zona prohibida), así que en **vuelo normal** debe rodearla por el camino más corto. El **vuelo con spoofing** hará justo lo contrario: entrar en esa zona.

| Punto | Qué es | Lat | Lon |
|---|---|---|---|
| **A (salida / HOME)** | Riviera Paleocapa (San Giuseppe), SW | `45.4021` | `11.8670` |
| **B (destino)** | Torre Archimede — Dip. Matematica "Tullio Levi-Civita" | `45.4113328` | `11.8878209` |
| **Zona 1 (keep-out)** | Palazzo Bo (Universidad, centro) — r=220 m | `45.4067383` | `11.8773940` |
| **Zona 2 (keep-out)** | Palazzo Liviano (Universidad, centro) — r=150 m | `45.4079860` | `11.8714491` |
| **Keep-in (área operativa)** | r=1500 m | `45.40672` | `11.87741` |

## 2. Fuente ÚNICA de las zonas: `zones.py`

Para que tengamos EXACTAMENTE las mismas zonas, usa este fichero tal cual (de aquí salen mi mapa, el geofence de QGC, el planificador y el detector):

```python
START = (45.4021, 11.8670)          # A = HOME de spawn del SITL
HOME  = START
DEST  = (45.4113328, 11.8878209)    # B = Torre Archimede (Matematica)
KEEPOUT = [
    {"name": "Palazzo Bo (Universita, centro)",      "lat": 45.4067383, "lon": 11.8773940, "r": 220},
    {"name": "Palazzo Liviano (Universita, centro)", "lat": 45.4079860, "lon": 11.8714491, "r": 150},
]
KEEPIN = {"name": "Area operativa Padova", "lat": 45.40672, "lon": 11.87741, "r": 1500}
```

Lanza el SITL con ese HOME:
```bash
PX4_HOME_LAT=45.4021 PX4_HOME_LON=11.8670 PX4_HOME_ALT=12 HEADLESS=1 make px4_sitl gz_x500
```

## 3. Lo que tengo hecho (en `~/geoshield/`)

- **`planner.py`** — ruta óptima C→D que evita las zonas (grafo de visibilidad + Dijkstra). General: cualquier par de puntos.
- **`plan_and_fly.py`** — planifica y **vuela** la ruta. `python3 plan_and_fly.py` vuela A→B; `python3 plan_and_fly.py Clat Clon Dlat Dlon` cualquier C→D; `--dry` solo planifica.
- **`detector.py`** — detector de spoofing en vivo (puerto 14540). Umbrales calibrados con vuelo limpio, **0 falsos positivos** verificados. Vigila: divergencia GPS↔EKF, ratios de innovación del EKF y saltos de posición.
- **`geoshield_padova.plan`** — geofence (keep-in + 2 keep-out) + misión normal A→B, para cargar en QGroundControl.
- Mapas: `scenario_map.png` (A→B esquivando), `mapa_padua.png`, histogramas de análisis.

## 3B. Para ver EXACTAMENTE lo mismo que yo (Gazebo 3D + QGC)

Te paso una carpeta `GeoShield/` con dos cosas que importan aquí:
- **`scripts/`** → cópiala a tu WSL en `~/geoshield/` (todos los `.py` y `.sh`). Dentro va `zones.py` (la fuente única de la sección 2 — **úsala tal cual**).
- **`gazebo_assets/`** → el mundo 3D de Padova ya generado (mapa OSM real + zonas rojas + edificios + marcadores A/B), para que no tengas que descargar nada.

### a) Mundo 3D de Gazebo — dos opciones (elige una)

**Opción A — copiar lo ya generado (rápida, sin descargas).** Copia los assets a tu árbol de PX4:
```bash
cp gazebo_assets/worlds/padova.sdf   ~/PX4-Autopilot/Tools/simulation/gz/worlds/
mkdir -p ~/PX4-Autopilot/Tools/simulation/gz/models/padova_ground
cp gazebo_assets/models/padova_ground/*  ~/PX4-Autopilot/Tools/simulation/gz/models/padova_ground/
```

**Opción B — regenerarlo tú (reproducible).** Con `zones.py` en `~/geoshield/` y `pip install requests pillow`:
```bash
cd ~/geoshield && python3 make_texture.py && python3 build_world.py
```
(Descarga las teselas OSM y escribe el mismo `padova.sdf` + `padova_ground/` en tu árbol de PX4.)

> El mundo tiene el **origen GPS = HOME (A)**, así que el dron spawnea justo sobre su sitio del mapa y todo queda **sincronizado**. Si cambias `zones.py`, regenera con la Opción B.

### b) Lanzar el SITL con el mundo de Padova + ventana + cámara

Tres terminales en WSL:
```bash
bash ~/geoshield/run_padova.sh      # SITL headless: mundo padova, HOME=A (45.4021, 11.8670)
bash ~/geoshield/run_gui.sh         # ventana de Gazebo (render por software, estable en WSLg)
bash ~/geoshield/follow_cam.sh      # (opcional) la cámara sigue al dron x500_0
```
Verás: el dron sobre el mapa real de Padova, 2 cilindros rojos (Bo y Liviano), marcador verde en A y amarillo en B (Torre Archimede).

### c) QGroundControl — mismo geofence y misión

Abre QGC (se conecta solo por el **14550**), ve a **Plan → Open** y carga **`geoshield_padova.plan`**. Verás el keep-in + las 2 zonas keep-out + la ruta normal A→B. (Si lo prefieres regenerar: `python3 make_qgc_plan.py`.)

## 4. Lo que necesito de ti (el ataque)

Para el **vuelo con spoofing** necesito que inyectes GPS falso en el SITL de forma que el dron **acabe entrando en Palazzo Bo** (la zona que en modo normal rodea). Idealmente cubriendo los dos casos del enunciado:

- **Brusco**: salto de posición grande (teletransporte).
- **Gradual**: deriva lenta que empuja al dron dentro de la zona sin que PX4 lo note.

Lo importante (acordado): que el GPS manipulado llegue de verdad a la **navegación del EKF** de PX4 (no solo a la vista de QGC). Cuéntame **cómo inyectas** (p. ej. `HIL_GPS` / `GPS_INPUT` en MAVLink, o el módulo de simulación GPS de PX4) y en qué puerto, para encajarlo con el detector.

**Ojo con el puerto:** mi detector/scripts usan MAVLink **14540**; solo un proceso puede usarlo a la vez. Si tu ataque también usa 14540, lo coordinamos (o lo mueves a otro puerto / instancia).

## 5. Detector — umbrales (por si quieres probar que salta)

Calibrados con vuelo base (sin spoofing); margen para 0 falsos positivos:
- Divergencia GPS↔EKF **> 3 m** (base máx 1,0)
- Divergencia **> 1,5 m sostenida ≥ 3 s** → deriva gradual
- Ratios de innovación pos/vel **> 0,5** (base máx 0,02–0,11; el EKF rechaza a 1,0)
- Salto de posición **> 15 m/s** aparente (base máx 6,4)

Cuando tu ataque entre, estos valores deberían dispararse → el detector marca la alerta con marca de tiempo.
