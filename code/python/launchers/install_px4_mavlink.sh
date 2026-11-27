#!/usr/bin/env bash
# GeoShield - add an extra MAVLink link to PX4 SITL for the DETECTOR (idempotent).
# PX4 will also send telemetry to UDP 14541, so detector.py (14541) and plan_and_fly.py (14540)
# can run at the same time. It takes effect the next time the SITL starts.
#
#   -u 14591 = PX4 local port      -o 14541 = port PX4 SENDS to (where the detector listens)
#   -f       = forwarding between links (the detector's warnings reach QGroundControl)
F="${PX4_DIR:-$HOME/PX4-Autopilot}/ROMFS/px4fmu_common/init.d-posix/px4-rc.mavlink"
if [ ! -f "$F" ]; then echo "ERROR: $F not found"; exit 1; fi
if grep -q "GeoShield" "$F"; then
  echo "[GeoShield] the 14541 link was already in px4-rc.mavlink"
else
  cat >> "$F" <<'EOT'

# GeoShield: extra link for the spoofing detector (PX4 sends to UDP 14541)
mavlink start -x -u 14591 -r 4000000 -f -m onboard -o 14541
EOT
  echo "[GeoShield] link 14541 added to px4-rc.mavlink (restart the SITL)"
fi
