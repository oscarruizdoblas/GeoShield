#!/usr/bin/env bash
# sync_wsl.sh is a Bash setup and synchronization script for the GeoShield project.
#
# It copies the Python programs, experiment launchers, Gazebo launchers and demo tools from the
# repository to the WSL working directory (~/geoshield). If the PX4 installation is available, it
# also copies the Padova world and ground model when they are missing. Finally, it checks Python
# compilation and shell-script syntax.
#
# The script prepares and validates the local environment; it does not launch Gazebo,
# QGroundControl, a flight or an attack.
#
# Usage (from the repository root, inside WSL):
#   bash code/sync_wsl.sh
set -e
REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
G="${GEOSHIELD_DIR:-$HOME/geoshield}"; PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
mkdir -p "$G"
cp "$REPO"/code/python/*.py "$REPO"/code/python/launchers/*.sh "$G/"
cp "$REPO"/code/gazebo/launchers/*.sh "$G/"
cp "$REPO"/code/demo/*.py "$REPO"/code/demo/*.sh "$REPO"/code/demo/gui_video.config "$G/"
sed -i 's/\r$//' "$G"/*.sh "$G"/*.py
if [ -d "$PX4_DIR/Tools/simulation/gz" ]; then
  W="$PX4_DIR/Tools/simulation/gz/worlds/padova.sdf"
  [ -f "$W" ] || cp "$REPO/code/gazebo/worlds/padova.sdf" "$W"
  M="$PX4_DIR/Tools/simulation/gz/models/padova_ground"
  [ -d "$M" ] || { mkdir -p "$M"; cp "$REPO"/code/gazebo/models/padova_ground/* "$M/"; }
fi
PY="${GEOSHIELD_PY:-python3}"; $PY -c "import pymavlink" 2>/dev/null || { [ -x "$HOME/yes/bin/python3" ] && PY="$HOME/yes/bin/python3"; }
cd "$G"
$PY -m py_compile zones.py planner.py plan_and_fly.py detector.py return_home.py upload_fence.py logger.py analyze.py analyze_attack.py evaluate_campaign.py offboard_breach_test.py make_qgc_plan.py build_world.py detector_panel.py && echo "python ($PY): OK"
/usr/bin/python3 -m py_compile spoof_relay.py real_pos_qgc.py scale_drone.py && echo "system python (gz): OK"
for f in *.sh; do bash -n "$f" || echo "SYNTAX ERROR in $f"; done; echo "launchers: OK"
echo "synchronised to $G"
