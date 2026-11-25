# GeoShield — proyecto de simulación

Proyecto académico para evaluar, en **PX4 SITL**, cómo se comportan la planificación, las geocercas y la detección de anomalías en un escenario de Padova. El trabajo documentado hasta ahora es el vuelo normal de referencia del Experimento 01. Los Experimentos 02–04 siguen pendientes y no se han ejecutado.

## Estructura

```text
code/
├── qground/       # plan de misión y geofence que se abre en QGroundControl
├── gazebo/        # mundo, modelo del terreno y lanzadores de Gazebo
└── python/        # configuración y herramientas Python
docs/
├── experimento-01/ # vuelo normal, informe y evidencias disponibles
├── experimento-02/ # plan de deriva GPS gradual; aún no ejecutado
├── experimento-03/ # plan de salto GPS abrupto; aún no ejecutado
├── experimento-04/ # plan de evaluación de GeoShield; aún no ejecutado
└── README.md       # resumen y estado de los cuatro experimentos
```

La configuración geográfica canónica está en [`code/python/zones.py`](code/python/zones.py). El plan de QGroundControl está en [`code/qground/geoshield_padova.plan`](code/qground/geoshield_padova.plan); el mundo de Gazebo y el plan comparten las zonas de la configuración del proyecto. Consulta [`code/python/README.md`](code/python/README.md) para saber qué hace cada herramienta.

## Estado actual

- **Experimento 01:** vuelo SITL normal A→B→A realizado el 14 de noviembre de 2026. La misión rodeó las zonas configuradas y el vehículo aterrizó en A. El informe enumera qué se midió y qué todavía no quedó demostrado.
- **Experimentos 02, 03 y 04:** definidos como escenarios de software, pero pendientes. Sus carpetas describen el objetivo y la evidencia que habrá que guardar; no contienen resultados de vuelos.
- **Evidencia:** CSV de telemetría y ULog del vuelo normal en `docs/experimento-01/evidencia/`. El vídeo de 1,1 GB se mantiene en Drive, siguiendo la decisión anterior de guardar el enlace en el repositorio en lugar del archivo completo.

## Inicio rápido en WSL2

```bash
cd /mnt/c/Users/Ignacio/Documents/GitHub/GeoShield-compartido/GeoShield
PX4_DIR="$HOME/PX4-Autopilot"
cp code/gazebo/worlds/padova.sdf "$PX4_DIR/Tools/simulation/gz/worlds/"
mkdir -p "$PX4_DIR/Tools/simulation/gz/models/padova_ground"
cp code/gazebo/models/padova_ground/* "$PX4_DIR/Tools/simulation/gz/models/padova_ground/"
```

En terminales separadas, desde la raíz del repositorio:

```bash
bash code/gazebo/launchers/run_padova.sh
bash code/gazebo/launchers/run_gui.sh
bash code/gazebo/launchers/cam_birdseye.sh
```

En QGroundControl, abre **Plan → Open** y selecciona `code/qground/geoshield_padova.plan`. Para instrucciones y dependencias, lee [`docs/traspaso-escenario.md`](docs/traspaso-escenario.md) y los README dentro de `code/`.

## Documentación

- [Resumen de los cuatro experimentos](docs/README.md)
- [Experimento 01: vuelo normal](docs/experimento-01/README.md)
- [Informe técnico detallado del Experimento 01](docs/experimento-01/informe-tecnico-en.md)
- [Traspaso del escenario Padova](docs/traspaso-escenario.md)

Los edificios y el terreno de Gazebo son una representación visual aproximada para SITL; no son un modelo urbano de precisión ni una garantía de colisión física con cada edificio.
