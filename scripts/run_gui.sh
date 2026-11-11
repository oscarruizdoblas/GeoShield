#!/usr/bin/env bash
# GeoShield - ventana de Gazebo (cliente GUI) conectada al servidor headless.
# RENDER POR SOFTWARE (llvmpipe): en WSLg la GPU virtual se cae con ogre2 al
# mover la camara; por software va mas lento pero NO se cuelga ni se queda gris.
export GZ_IP=127.0.0.1
export GZ_SIM_RESOURCE_PATH=":/home/oruiz/PX4-Autopilot/Tools/simulation/gz/models:/home/oruiz/PX4-Autopilot/Tools/simulation/gz/worlds"
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export __GLX_VENDOR_LIBRARY_NAME=mesa
echo "[GeoShield] Ventana de Gazebo (render por software, estable en WSLg). Puede ir algo lento."
exec gz sim -g
