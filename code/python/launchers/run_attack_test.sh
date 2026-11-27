#!/usr/bin/env bash
# GeoShield - run ONE complete test and keep all its CSVs in ~/geoshield/logs/<date>_<name>/
#
#   run_attack_test.sh NAME MODE [RESPONSE] [extra args for spoof_relay.py]
#     MODE     = none | jump | drift
#     RESPONSE = no | si | corte   (no: detect only; si ("yes"): HOLD + return;
#                                   corte ("cut"): HOLD + stop fusing GPS + return)
#   FULL=1 run_attack_test.sh normal none                -> full normal flight A->B->A (no attack)
#   SHOW=1 run_attack_test.sh video drift no --verbose   -> also print the attack live in this terminal
#
# Requirement: SITL started with run_padova_spoof.sh (GPS goes through the relay).
# Steps: relay (attack armed) -> detector (port 14541) -> flight (port 14540) -> attack stopped -> return home.
NAME="${1:?name}"; MODE="${2:?mode}"; RESP="${3:-no}"; shift 3 2>/dev/null || shift $#
PY="${GEOSHIELD_PY:-python3}"   # interpreter with pymavlink (override with GEOSHIELD_PY)
$PY -c "import pymavlink" 2>/dev/null || { [ -x "$HOME/yes/bin/python3" ] && PY="$HOME/yes/bin/python3"; }   # fallback: conda Python
G="${GEOSHIELD_DIR:-$HOME/geoshield}"; RUN="$G/run"; mkdir -p "$RUN"
OUT="$G/logs/$(date +%Y%m%d_%H%M%S)_$NAME"; mkdir -p "$OUT"
rm -f "$RUN/ABORT" "$RUN/ATTACK_STOP" "$RUN/RESPONSE_DONE" "$RUN/attack_start"   # control files between the processes
cd "$G"
echo "[test] $NAME  mode=$MODE  response=$RESP  -> $OUT"
echo "name=$NAME mode=$MODE response=$RESP extra=$*" > "$OUT/test.txt"

# 1) attack relay (replaces the idle transparent relay); the attack waits for its trigger distance
pkill -f "[s]poof_relay.py"; sleep 1
/usr/bin/python3 spoof_relay.py --mode "$MODE" --logdir "$OUT" "$@" > "$OUT/relay.log" 2>&1 &
sleep 6                                   # the EKF recovers the GPS after the relay switch
# 2) detector, with the requested response
DARGS=""; [ "$RESP" = "si" ] && DARGS="--respond"; [ "$RESP" = "corte" ] && DARGS="--respond --cut-gps"
$PY detector.py --logdir "$OUT" $DARGS > "$OUT/detector.log" 2>&1 &
DET=$!
sleep 2
# SHOW=1: show live in this terminal what the attacker does and the detector alerts (demo)
if [ "$SHOW" = "1" ]; then
  echo "[test] spoofing relay: /usr/bin/python3 spoof_relay.py --mode $MODE $*"
  echo "[test] the relay sits between the Gazebo GPS sensor and PX4: every GPS message goes through it"
  tail -n +1 -f "$OUT/relay.log" | grep --line-buffered -E "ATTACK|armed|ARMED|target|STOPPED" &
  tail -n +1 -f "$OUT/detector.log" | grep --line-buffered -m 3 "ALERT" | sed -u 's/^ */[detector] /' &
  tail -n +1 -f "$OUT/detector.log" | grep --line-buffered "RESPONSE" | sed -u 's/^ *>> */[defence] /' &
  case "$RESP" in
    no)    echo "[test] defence: OFF (the detector only warns)";;
    si)    echo "[test] defence: HOLD + warning + return to the last trusted point";;
    corte) echo "[test] defence: HOLD + warning + GPS CUT (inertial navigation) + return to the trusted point";;
  esac
  echo "[test] taking off: flight A -> B along the route around Palazzo Bo"
fi

# 3) flight
if [ "$FULL" = "1" ]; then
  GEOSHIELD_LOGDIR="$OUT" $PY plan_and_fly.py > "$OUT/flight.log" 2>&1
  tail -2 "$OUT/flight.log"
else
  GEOSHIELD_LOGDIR="$OUT" $PY plan_and_fly.py --oneway > "$OUT/flight.log" 2>&1
  tail -2 "$OUT/flight.log"
  if [ "$RESP" != "no" ] && [ -f "$RUN/ABORT" ]; then
    echo "[test] response in progress: waiting for the trusted point (max 90 s)"
    for i in $(seq 1 90); do [ -f "$RUN/RESPONSE_DONE" ] && break; sleep 1; done
    sleep 15                              # observe the hold at the trusted point
  fi
  # 4) stop the attack and bring the drone home (restoring GPS fusion if it was cut)
  if [ "$MODE" != "none" ]; then
    touch "$RUN/ATTACK_STOP"; echo "[test] attack stopped; 25 s for the EKF to return to the true GPS"
    GPSON=""; [ "$RESP" = "corte" ] && GPSON="--gps-on"
    [ -z "$GPSON" ] && sleep 25
  fi
  $PY return_home.py $GPSON > "$OUT/return.log" 2>&1
  tail -2 "$OUT/return.log"
fi

# 5) clean up
kill -TERM $DET 2>/dev/null; sleep 2
pkill -f "[s]poof_relay.py"; sleep 1
pkill -f "tail -n \+1 -f $OUT/" 2>/dev/null
rm -f "$RUN/ABORT" "$RUN/ATTACK_STOP"
# transparent relay in its own session, so PX4 keeps getting GPS between tests
setsid -f /usr/bin/python3 spoof_relay.py --mode none --logdir "$G/logs/_relay_idle" > "$HOME/relay.log" 2>&1 < /dev/null
echo "[test] END $NAME -> $OUT"
