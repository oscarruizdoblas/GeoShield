#!/usr/bin/env bash
set -euo pipefail
export GZ_SIM_RESOURCE_PATH="${GZ_SIM_RESOURCE_PATH:-}"
export GZ_SIM_SYSTEM_PLUGIN_PATH="${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
export GZ_SIM_SERVER_CONFIG_PATH="${GZ_SIM_SERVER_CONFIG_PATH:-}"
PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
if [[ -f "$PX4_DIR/build/px4_sitl_default/gz_env.sh" ]]; then
  # Load the Gazebo plugins and server config built for this PX4 checkout.
  # shellcheck disable=SC1090
  source "$PX4_DIR/build/px4_sitl_default/gz_env.sh"
fi
export GZ_IP="${GZ_IP:-127.0.0.1}"
export PX4_GZ_MODELS="${PX4_GZ_MODELS:-$PX4_DIR/Tools/simulation/gz/models}"
export PX4_GZ_WORLDS="${PX4_GZ_WORLDS:-$PX4_DIR/Tools/simulation/gz/worlds}"
export GZ_SIM_RESOURCE_PATH="$PX4_GZ_MODELS:$PX4_GZ_WORLDS${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export __GLX_VENDOR_LIBRARY_NAME=mesa
echo "[GeoShield] Abriendo cliente Gazebo en WSLg (render por software)."
exec gz sim -g
