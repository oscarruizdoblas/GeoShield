#!/usr/bin/env bash
# GeoShield - Gazebo window (GUI client) attached to the headless simulation server.
# SOFTWARE RENDERING (llvmpipe): under WSLg the virtual GPU crashes with ogre2 when the camera
# moves; software rendering is slower but does NOT hang or turn grey.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"
PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
if [[ -f "$PX4_DIR/build/px4_sitl_default/gz_env.sh" ]]; then
  source "$PX4_DIR/build/px4_sitl_default/gz_env.sh"
fi
PX4_GZ_MODELS="${PX4_GZ_MODELS:-$PX4_DIR/Tools/simulation/gz/models}"
PX4_GZ_WORLDS="${PX4_GZ_WORLDS:-$PROJECT_DIR/code/gazebo/worlds}"
export GZ_IP="${GZ_IP:-127.0.0.1}"
export GZ_SIM_RESOURCE_PATH="$PROJECT_DIR/code/gazebo/models:$PX4_GZ_MODELS:$PX4_GZ_WORLDS:$PX4_DIR/Tools/simulation/gz/worlds${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export __GLX_VENDOR_LIBRARY_NAME=mesa
echo "[GeoShield] Gazebo window (software rendering, stable on WSLg). It may be a bit slow."
exec gz sim -g
