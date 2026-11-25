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
export PX4_HOME_LAT="${PX4_HOME_LAT:-45.4021}"
export PX4_HOME_LON="${PX4_HOME_LON:-11.8670}"
export PX4_HOME_ALT="${PX4_HOME_ALT:-12}"
export PX4_GZ_WORLD=padova
export PX4_GZ_MODELS="${PX4_GZ_MODELS:-$PX4_DIR/Tools/simulation/gz/models}"
export PX4_GZ_WORLDS="${PX4_GZ_WORLDS:-$PX4_DIR/Tools/simulation/gz/worlds}"
export GZ_SIM_RESOURCE_PATH="$PX4_GZ_MODELS:$PX4_GZ_WORLDS${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
export HEADLESS=1
if [[ ! -x "$PX4_DIR/build/px4_sitl_default/bin/px4" ]]; then
  echo "ERROR: no encuentro el binario SITL en $PX4_DIR/build/px4_sitl_default/bin/px4" >&2; exit 1
fi
if [[ ! -f "$PX4_GZ_WORLDS/padova.sdf" || ! -f "$PX4_GZ_MODELS/padova_ground/model.sdf" ]]; then
  echo "ERROR: faltan padova.sdf o el modelo padova_ground; prepara primero los recursos locales." >&2; exit 1
fi
echo "[GeoShield] PX4=$PX4_DIR WORLD=padova HOME=$PX4_HOME_LAT,$PX4_HOME_LON,$PX4_HOME_ALT (SITL headless)"
cd "$PX4_DIR"
exec make px4_sitl gz_x500
