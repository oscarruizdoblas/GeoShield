#!/usr/bin/env bash
# GeoShield - Gazebo window with ONLY the 3D view (no side panels or toolbars), for screen recording.
# Same as run_gui.sh (software rendering, stable on WSLg) but with gui_video.config.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
CONF="$SCRIPT_DIR/gui_video.config"
[ -f "$CONF" ] || CONF="$HOME/geoshield/gui_video.config"
export GZ_IP="${GZ_IP:-127.0.0.1}"
export GZ_SIM_RESOURCE_PATH="$PX4_DIR/Tools/simulation/gz/models:$PX4_DIR/Tools/simulation/gz/worlds${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
export LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe __GLX_VENDOR_LIBRARY_NAME=mesa
exec gz sim -g --gui-config "$CONF"
