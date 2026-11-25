# Herramientas Python

Todas las coordenadas y radios compartidos están definidos en [`zones.py`](zones.py). Ejecuta los comandos desde la raíz del repositorio, por ejemplo `python3 code/python/plan_and_fly.py`. Los programas que envían mensajes MAVLink hablan con PX4 SITL; comprueba que la simulación sea la esperada antes de ejecutarlos. No lances dos consumidores que escuchen UDP 14540 al mismo tiempo.

| Archivo | Qué hace |
|---|---|
| [`zones.py`](zones.py) | Fuente única de HOME/A, destino B, dos zonas keep-out y el área keep-in de Padova. La usan el planificador, los generadores, el mundo y las herramientas MAVLink. |
| [`planner.py`](planner.py) | Construye una ruta alrededor de círculos keep-out con un grafo de visibilidad y Dijkstra. No controla el dron. |
| [`make_qgc_plan.py`](make_qgc_plan.py) | Genera el archivo de misión/geofence `.plan` para QGroundControl usando `zones.py` y `planner.py`. Escribe en `code/qground/` por defecto. |
| [`plan_route.py`](plan_route.py) | Genera una visualización 2D de la ruta y las zonas a partir del escenario; puede descargar teselas OSM y requiere las dependencias de gráficos indicadas en el propio script. |
| [`plan_and_fly.py`](plan_and_fly.py) | En PX4 SITL, calcula la ruta normal A→B y regreso, envía comandos de vuelo y registra CSV MAVLink. Es el programa usado en el vuelo normal documentado. |
| [`upload_fence.py`](upload_fence.py) | Lee/actualiza y verifica parámetros de geocerca de PX4 mediante MAVLink. No arma el vehículo. |
| [`upload_mission.py`](upload_mission.py) | Carga la misión del archivo QGC a PX4 y solicita una lectura de vuelta para comprobarla. No arma ni inicia el vuelo. |
| [`logger.py`](logger.py) | Guarda telemetría MAVLink en CSV de forma independiente. No debe competir por el mismo puerto UDP con otro consumidor. |
| [`detector.py`](detector.py) | Evalúa reglas de divergencia GPS/EKF, innovación y saltos sobre telemetría recibida; guarda alertas y registros. No se ejecutó en el Experimento 01. |
| [`analyze.py`](analyze.py) | Calcula estadísticas y gráficas a partir de CSV de telemetría existentes. Es análisis posterior, no prueba de geocerca. |
| [`check_fp.py`](check_fp.py) | Revisa registros para estimar falsos positivos del detector; los resultados dependen de las trazas que se le proporcionen. |
| [`build_world.py`](build_world.py) | Genera el SDF del mundo de Padova, el terreno, edificios visuales, marcadores A/B y círculos keep-out a partir de `zones.py`. Hace copia de seguridad de destinos que ya existan en PX4. |
| [`make_texture.py`](make_texture.py) | Descarga teselas de OpenStreetMap y prepara la textura satelital del suelo para Gazebo. Requiere conexión y `requests`/`Pillow`. Hace copia de seguridad de una textura anterior. |

## Dependencias y notas

- `pymavlink`: `plan_and_fly.py`, `upload_fence.py`, `upload_mission.py`, `logger.py` y `detector.py`.
- `numpy`, `pandas`, `matplotlib`: análisis y visualización (`analyze.py`, `check_fp.py`, `plan_route.py`).
- `requests`, `Pillow`: generación de textura y mapa 2D (`make_texture.py`, `plan_route.py`).
- Los lanzadores de Gazebo están separados en [`../gazebo/launchers/`](../gazebo/launchers/).
- Las salidas de telemetría se guardan bajo `~/geoshield/logs/` en la configuración actual. El ULog lo genera PX4 dentro de su directorio de logs.

No se han ejecutado aquí nuevas pruebas de vuelo ni los escenarios 02–04.
