#!/usr/bin/env bash
# GeoShield - PX4 SITL in the Padova world with the drone's GPS INTERCEPTABLE (simulation only).
#
# Same as run_padova.sh, but the drone's NavSat (GPS) sensor publishes on /geoshield/navsat_true
# instead of the topic PX4 listens to. PX4 only receives GPS through spoof_relay.py, which
# passes it through unchanged (--mode none) or forges it (--mode jump | drift).
#   => with this launcher the relay MUST be running, otherwise PX4 has no GPS and cannot arm.
#
# The original PX4 model is not modified: a patched copy of x500_base is placed in a folder that
# Gazebo searches first (GZ_SIM_RESOURCE_PATH).
SRC="$HOME/PX4-Autopilot/Tools/simulation/gz/models/x500_base"
DST="$HOME/geoshield/gz_spoof_models/x500_base"
mkdir -p "$HOME/geoshield/gz_spoof_models" "$HOME/geoshield/run"
rm -rf "$DST"; cp -r "$SRC" "$DST"
# add a <topic> to the NavSat sensor so it publishes on our private topic
sed -i 's|<sensor name="navsat_sensor" type="navsat">|<sensor name="navsat_sensor" type="navsat">\n        <topic>/geoshield/navsat_true</topic>|' "$DST/model.sdf"
if ! grep -q "/geoshield/navsat_true" "$DST/model.sdf"; then
  echo "[GeoShield] ERROR: could not redirect the NavSat sensor"; exit 1
fi
# DEMO_SCALE=40 -> the drone is DRAWN 40 times bigger (appearance only; physics unchanged), for the videos
if [ -n "$DEMO_SCALE" ]; then
  python3 "$HOME/geoshield/scale_drone.py" "$DST/model.sdf" "$DEMO_SCALE" || exit 1
fi
export GZ_SIM_RESOURCE_PATH="$HOME/geoshield/gz_spoof_models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
export PX4_HOME_LAT="${PX4_HOME_LAT:-45.4021}"     # HOME = point A (zones.py)
export PX4_HOME_LON="${PX4_HOME_LON:-11.8670}"
export PX4_HOME_ALT="${PX4_HOME_ALT:-12}"
export PX4_GZ_WORLD=padova
export HEADLESS=1
echo "[GeoShield] World=padova  HOME=$PX4_HOME_LAT,$PX4_HOME_LON  (HEADLESS, GPS via spoof_relay.py)"
cd ~/PX4-Autopilot
exec make px4_sitl gz_x500
