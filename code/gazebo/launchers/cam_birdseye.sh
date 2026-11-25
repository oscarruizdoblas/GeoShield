#!/usr/bin/env bash
# GeoShield - camara cenital (vista de pajaro) para congruencia visual con QGC.
MODEL="${1:-x500_0}"
for i in $(seq 1 60); do
  if gz service -l 2>/dev/null | grep -q "/gui/follow"; then
    echo "GUI-LISTA tras $((i*2))s"
    gz service -s /gui/follow --reqtype gz.msgs.StringMsg --reptype gz.msgs.Boolean --timeout 3000 --req "data: \"$MODEL\"" >/dev/null 2>&1
    gz service -s /gui/follow/offset --reqtype gz.msgs.Vector3d --reptype gz.msgs.Boolean --timeout 3000 --req "x: -10, y: -90, z: 480" >/dev/null 2>&1
    echo "CAMARA-CENITAL-FIJADA"
    exit 0
  fi
  sleep 2
done
echo "GUI-TIMEOUT"
