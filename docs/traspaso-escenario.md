# Traspaso del escenario Padova

## Configuración

La definición geográfica compartida está en [`../code/python/zones.py`](../code/python/zones.py): HOME/A en Riviera Paleocapa, destino B en Torre Archimede, dos círculos keep-out y un círculo keep-in. El plan que se abre en QGroundControl está en [`../code/qground/geoshield_padova.plan`](../code/qground/geoshield_padova.plan). El mundo y modelo visual están en [`../code/gazebo/`](../code/gazebo/README.md).

## Preparar Gazebo en WSL2

Desde la raíz del repositorio:

```bash
PX4_DIR="$HOME/PX4-Autopilot"
cp code/gazebo/worlds/padova.sdf "$PX4_DIR/Tools/simulation/gz/worlds/"
mkdir -p "$PX4_DIR/Tools/simulation/gz/models/padova_ground"
cp code/gazebo/models/padova_ground/* "$PX4_DIR/Tools/simulation/gz/models/padova_ground/"
```

Abre tres terminales WSL y ejecuta, desde la raíz:

```bash
bash code/gazebo/launchers/run_padova.sh
bash code/gazebo/launchers/run_gui.sh
bash code/gazebo/launchers/cam_birdseye.sh
```

Los scripts esperan PX4 instalado en `~/PX4-Autopilot`, salvo que se defina `PX4_DIR`. El vuelo normal documentado fue SITL; QGroundControl se conecta por MAVLink.

## QGroundControl y geofence

En QGC abre **Plan → Open** y elige `code/qground/geoshield_padova.plan`. Para regenerarlo desde la configuración canónica, ejecuta `python3 code/python/make_qgc_plan.py`. Para transferir una misión o geofence a PX4, usa los scripts descritos en [`../code/python/README.md`](../code/python/README.md) solo con la simulación correcta conectada.

La ruta planificada evita los círculos. Esto no demuestra por sí solo que PX4 aplicara la geocerca en cada instante del vuelo; el informe del Experimento 01 conserva esa limitación.

## Experimentos y evidencia

- [`experimento-01/`](experimento-01/README.md) documenta el vuelo nominal completado y sus límites.
- [`experimento-02/`](experimento-02/README.md), [`experimento-03/`](experimento-03/README.md) y [`experimento-04/`](experimento-04/README.md) son planes pendientes. No se han ejecutado.
- El vídeo del Experimento 01 está enlazado en Drive porque el archivo pesa aproximadamente 1,1 GB. Los CSV y ULog disponibles se guardan localmente en la carpeta de evidencias del experimento.

Todo el alcance experimental documentado es PX4 SITL. No se han ejecutado ataques en estos registros, no se usa aeronave física y no se transmite RF.
