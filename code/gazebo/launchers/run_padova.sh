#!/usr/bin/env bash
# GeoShield - PX4 SITL with the Padova 3D WORLD (ground = OSM map, red no-fly zones, buildings).
# HOME at A (Riviera Paleocapa). Headless; open the window separately with run_gui.sh.
# The GPS goes straight to PX4 here (no attack possible); experiments use run_padova_spoof.sh.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"
PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
PX4_GZ_WORLDS_OVERRIDE="${PX4_GZ_WORLDS:-}"
if [[ ! -f "$PX4_DIR/build/px4_sitl_default/gz_env.sh" ]]; then
  echo "[GeoShield] PX4/Gazebo not found in $PX4_DIR" >&2
  exit 1
fi
source "$PX4_DIR/build/px4_sitl_default/gz_env.sh"
export PX4_HOME_LAT="${PX4_HOME_LAT:-45.4021}"
export PX4_HOME_LON="${PX4_HOME_LON:-11.8670}"
export PX4_HOME_ALT="${PX4_HOME_ALT:-12}"
export PX4_GZ_WORLD="${PX4_GZ_WORLD:-padova}"
export PX4_GZ_MODELS="${PX4_GZ_MODELS:-$PX4_DIR/Tools/simulation/gz/models}"
export PX4_GZ_WORLDS="${PX4_GZ_WORLDS_OVERRIDE:-$PROJECT_DIR/code/gazebo/worlds}"
export GZ_SIM_RESOURCE_PATH="$PROJECT_DIR/code/gazebo/models:$PX4_GZ_MODELS:$PX4_GZ_WORLDS:$PX4_DIR/Tools/simulation/gz/worlds${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
export HEADLESS=1
echo "[GeoShield] World=$PX4_GZ_WORLD  HOME=$PX4_HOME_LAT,$PX4_HOME_LON  PX4=$PX4_DIR (HEADLESS)"
cd "$PX4_DIR" || exit 1
exec make px4_sitl gz_x500
