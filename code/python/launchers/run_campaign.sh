#!/usr/bin/env bash
# GeoShield - campaign of repeated flights: many flights in a row, unattended.
#
#   bash run_campaign.sh [TAG]          (default TAG: campaign)
#
# Before EVERY flight it restarts the SITL (headless, no QGC: plan_and_fly.py acts as the GCS),
# restarts the transparent relay, reloads the geofence and checks the parameters the response
# changes (GF_ACTION=3, EKF2_GPS_CTRL=7, EKF2_NOAID_TOUT=5000000). So every flight starts from
# the same state and a broken flight cannot contaminate the next one.
# Attacks run with the "corte" (GPS cut) response: the detection delay is the same as without a
# response (the detector is identical up to the first alert) and the flight takes ~4 min, not 10.
# If an attack is NOT detected, the flight continues to B: that is recorded as a missed detection.
# Scenarios are interleaved by rounds (round 1 of every scenario, then round 2...), so no scenario
# benefits from the order and an interrupted campaign still has data for all of them.
# Flights already present are skipped, so the campaign can be resumed.
#
# Each flight leaves its folder in ~/geoshield/logs/<date>_<TAG>_<scenario>_r<N>/.
# Then: python3 evaluate_campaign.py TAG  -> tables and figures in ~/geoshield/results/campaign/.
TAG="${1:-campaign}"
PY="${GEOSHIELD_PY:-python3}"; $PY -c "import pymavlink" 2>/dev/null || { [ -x "$HOME/yes/bin/python3" ] && PY="$HOME/yes/bin/python3"; }
G="$HOME/geoshield"; cd "$G"
PROG="$G/logs/campaign_${TAG}.log"     # campaign progress log

# scenario | mode | response | relay args | repetitions
SCEN=(
  "normal|none|no||5"
  "jump|jump|corte||5"
  "drift3|drift|corte|--rate 3|5"
  "drift2|drift|corte|--rate 2|3"
  "drift1|drift|corte|--rate 1|3"
  "drift05|drift|corte|--rate 0.5|3"
  "drift1_novel|drift|corte|--rate 1 --no-vel|3"
)

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$PROG"; }

restart_sim() {
  # kill everything, start a fresh SITL + transparent relay, reload fence and parameters
  pkill -f "[r]un_attack_test"; pkill -f "[p]lan_and_fly.py"; pkill -f "[r]eturn_home.py"; pkill -f "[d]etector.py"
  pkill -f "[s]poof_relay.py"; pkill -9 -x px4; pkill -9 -f "[g]z sim"; pkill -f "[r]un_padova_spoof"; pkill -f "[s]leep infinity"
  sleep 3
  rm -f "$G/run/ABORT" "$G/run/ATTACK_STOP" "$G/run/RESPONSE_DONE" "$G/run/attack_start"
  : > "$HOME/sitl.log"
  setsid -f bash -c 'sleep infinity | bash ~/geoshield/run_padova_spoof.sh > ~/sitl.log 2>&1'
  for i in $(seq 1 90); do grep -aq "INFO  \[commander\]" "$HOME/sitl.log" && break; sleep 2; done
  sleep 5
  setsid -f bash -c '/usr/bin/python3 ~/geoshield/spoof_relay.py --mode none --logdir ~/geoshield/logs/_relay_idle > ~/relay.log 2>&1 < /dev/null'
  for i in $(seq 1 60); do grep -aq "home set" "$HOME/sitl.log" && break; sleep 2; done
  grep -aq "home set" "$HOME/sitl.log" || return 1
  sleep 5                      # without a GCS PX4 never prints "Ready for takeoff": GPS + home is enough
  $PY upload_fence.py > /dev/null 2>&1
  $PY - <<'P'
import struct, time
from pymavlink import mavutil
m = mavutil.mavlink_connection('udpin:0.0.0.0:14540'); m.wait_heartbeat(timeout=20)
WANT = {'GF_ACTION': 3, 'EKF2_GPS_CTRL': 7, 'EKF2_NOAID_TOUT': 5000000}
def get(p):
    m.mav.param_request_read_send(1, 1, p.encode(), -1)
    r = m.recv_match(type='PARAM_VALUE', blocking=True, timeout=5)
    return struct.unpack('<i', struct.pack('<f', r.param_value))[0] if r else None
for p, v in WANT.items():
    if get(p) != v:
        m.mav.param_set_send(1, 1, p.encode(), struct.unpack('<f', struct.pack('<i', v))[0], mavutil.mavlink.MAV_PARAM_TYPE_INT32); time.sleep(0.5)
print('params', {p: get(p) for p in WANT})
P
}

# order: round 1 of every scenario, then round 2...
MAXR=0; for s in "${SCEN[@]}"; do r="${s##*|}"; [ "$r" -gt "$MAXR" ] && MAXR=$r; done
log "=== campaign $TAG: ${#SCEN[@]} scenarios, up to $MAXR repetitions"
for k in $(seq 1 "$MAXR"); do
  for s in "${SCEN[@]}"; do
    IFS='|' read -r NAME MODE RESP EXTRA REPS <<< "$s"
    [ "$k" -gt "$REPS" ] && continue
    RUN="${TAG}_${NAME}_r${k}"
    if ls -d "$G"/logs/2*_"$RUN" >/dev/null 2>&1; then log "already done: $RUN"; continue; fi
    log "--- $RUN: restarting the simulator"
    if ! restart_sim >> "$PROG" 2>&1; then log "ERROR: the SITL does not start, retrying"; restart_sim >> "$PROG" 2>&1 || { log "ERROR: $RUN skipped"; continue; }; fi
    log "--- $RUN: flight ($MODE, response $RESP $EXTRA)"
    if [ "$MODE" = "none" ]; then
      FULL=1 timeout 1500 bash run_attack_test.sh "$RUN" none no >> "$PROG" 2>&1
    else
      timeout 1500 bash run_attack_test.sh "$RUN" "$MODE" "$RESP" $EXTRA >> "$PROG" 2>&1
    fi
    D=$(ls -dt "$G"/logs/2*_"$RUN" 2>/dev/null | head -1)
    log "    end $RUN: alerts=$(( $(wc -l < "$D/alerts.csv" 2>/dev/null || echo 1) - 1 ))  $(tail -1 "$D/return.log" 2>/dev/null; tail -1 "$D/flight.log" 2>/dev/null | cut -c1-80)"
  done
done
pkill -f "[s]poof_relay.py"; pkill -9 -x px4; pkill -9 -f "[g]z sim"; pkill -f "[r]un_padova_spoof"; pkill -f "[s]leep infinity"
log "=== CAMPAIGN $TAG FINISHED"
