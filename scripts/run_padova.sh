#!/usr/bin/env bash
# GeoShield - PX4 SITL con el MUNDO 3D de Padova (suelo = mapa OSM, zonas rojas, edificios).
# HOME en Prato della Valle. Headless + abrir la ventana aparte con run_gui.sh.
export PX4_HOME_LAT="${PX4_HOME_LAT:-45.4021}"
export PX4_HOME_LON="${PX4_HOME_LON:-11.8670}"
export PX4_HOME_ALT="${PX4_HOME_ALT:-12}"
export PX4_GZ_WORLD=padova
export HEADLESS=1
echo "[GeoShield] Mundo=padova  HOME=$PX4_HOME_LAT,$PX4_HOME_LON  (HEADLESS)"
cd ~/PX4-Autopilot
exec make px4_sitl gz_x500
