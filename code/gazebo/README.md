# Escenario Gazebo Padova

Este directorio reúne el SDF, el modelo del terreno y los lanzadores. PX4 busca el mundo y el modelo dentro de su árbol local; copia los recursos desde la raíz del repositorio en WSL2:

```bash
PX4_DIR="$HOME/PX4-Autopilot"
cp code/gazebo/worlds/padova.sdf "$PX4_DIR/Tools/simulation/gz/worlds/"
mkdir -p "$PX4_DIR/Tools/simulation/gz/models/padova_ground"
cp code/gazebo/models/padova_ground/* "$PX4_DIR/Tools/simulation/gz/models/padova_ground/"
```

Abre terminales WSL separadas desde la raíz del repositorio:

```bash
bash code/gazebo/launchers/run_padova.sh
bash code/gazebo/launchers/run_gui.sh
bash code/gazebo/launchers/cam_birdseye.sh
```

`run_padova.sh` inicia PX4 SITL con el mundo instalado en PX4; `run_gui.sh` abre la interfaz de Gazebo; `cam_birdseye.sh` intenta seguir `x500_0`. Los otros dos lanzadores, `follow_cam.sh` y `gz_env.sh`, ofrecen una cámara alternativa y diagnóstico de entorno.

El terreno se proyecta como una textura visual y algunos edificios son volúmenes aproximados. El escenario está alineado con el origen configurado para SITL, pero esta escena visual no representa con precisión constructiva cada edificio ni constituye prueba de colisión o geofence.
