#!/usr/bin/env bash
# GeoShield - get EVERYTHING ready to record a demo (it does not start any flight):
#   SITL with interceptable GPS, transparent relay, Gazebo 3D-only window with the enlarged drone and
#   the demo camera, QGroundControl, geofence loaded, REAL position in QGC (vehicle 2) and detector panel.
#
#   bash prepare_demo.sh [SCALE]        (drawing scale of the drone, default 40; 1 = real size)
#
# Then, in a visible terminal:
#   SHOW=1 bash ~/geoshield/run_attack_test.sh video_drift drift no --verbose
# Uses the scripts copied to ~/geoshield (code/sync_wsl.sh). Everything is simulated.
SCALE="${1:-40}"
G="${GEOSHIELD_DIR:-$HOME/geoshield}"; PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
PY="${GEOSHIELD_PY:-python3}"; $PY -c "import pymavlink" 2>/dev/null || { [ -x "$HOME/yes/bin/python3" ] && PY="$HOME/yes/bin/python3"; }
export GZ_IP=127.0.0.1

# 1) stop whatever was running (QGC is left open if it already is)
pkill -f "[r]un_attack_test"; pkill -f "[p]lan_and_fly.py"; pkill -f "[r]eturn_home.py"; pkill -f "[d]etector.py"
pkill -f "[d]etector_panel"; pkill -f "[r]eal_pos_qgc"; pkill -f "[s]poof_relay.py"
pkill -9 -x px4; pkill -9 -f "[g]z sim"; pkill -f "[r]un_padova_spoof"; pkill -f "[s]leep infinity"; sleep 3
rm -f "$G/run/ABORT" "$G/run/ATTACK_STOP" "$G/run/RESPONSE_DONE"

# 2) SITL (stdin blocked: otherwise the pxh console loops) + transparent relay
: > "$HOME/sitl.log"
setsid -f bash -c "sleep infinity | DEMO_SCALE=$SCALE bash $G/run_padova_spoof.sh > $HOME/sitl.log 2>&1"
for i in $(seq 1 90); do grep -aq "INFO  \[commander\]" "$HOME/sitl.log" && break; sleep 2; done; sleep 5
setsid -f bash -c "/usr/bin/python3 $G/spoof_relay.py --mode none --logdir $G/logs/_relay_idle > $HOME/relay.log 2>&1 < /dev/null"

# 3) windows: Gazebo 3D-only and QGC
setsid -f bash -c "bash $G/run_gui_video.sh > $HOME/gui.log 2>&1"
pgrep -f "[Q]GroundControl" >/dev/null || setsid -f bash -c "cd $HOME/QGC && ./QGroundControl.AppImage --appimage-extract-and-run > $HOME/qgc.log 2>&1"
for i in $(seq 1 40); do gz service -l 2>/dev/null | grep -q "/gui/follow" && break; sleep 2; done; sleep 3
if [ "$SCALE" = "1" ]; then bash "$G/cam.sh" oblique; else bash "$G/cam.sh" demo; fi
# the green A and B markers (60 m tall cylinders) hide the drone: sink them so they remain as discs
for m in start_A dest_B; do
  P=$(grep -A3 "name=.$m" "$PX4_DIR/Tools/simulation/gz/worlds/padova.sdf" | grep -o "<pose>[^<]*" | head -1 | sed "s/<pose>//"); set -- $P
  gz service -s /world/padova/set_pose --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 3000 \
     --req "name: \"$m\", position: {x: $1, y: $2, z: -29.5}" >/dev/null
done

# 4) geofence, real position in QGC and detector panel
for i in $(seq 1 60); do grep -aq "home set" "$HOME/sitl.log" && break; sleep 2; done; sleep 8
(cd "$G" && $PY upload_fence.py | grep -E "ACK|GF_ACTION")
setsid -f bash -c "/usr/bin/python3 $G/real_pos_qgc.py > $HOME/realpos.log 2>&1"
setsid -f bash -c "$PY $G/detector_panel.py > $HOME/panel.log 2>&1"
echo "DEMO READY (drone drawn x$SCALE). Start the flight with:"
echo "  SHOW=1 bash $G/run_attack_test.sh video_drift drift no --verbose"
