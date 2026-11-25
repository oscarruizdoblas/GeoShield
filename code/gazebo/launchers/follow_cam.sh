#!/usr/bin/env bash
# GeoShield - camara de Gazebo siguiendo al dron, vista picada (dron + mapa).
MODEL="${1:-x500_0}"
echo "--- follow sobre $MODEL ---"
gz service -s /gui/follow \
  --reqtype gz.msgs.StringMsg --reptype gz.msgs.Boolean --timeout 3000 \
  --req "data: \"$MODEL\""
echo "--- offset (picado: mira hacia abajo, el borde superior cae cerca) ---"
gz service -s /gui/follow/offset \
  --reqtype gz.msgs.Vector3d --reptype gz.msgs.Boolean --timeout 3000 \
  --req "x: -45, y: -45, z: 130"
echo "listo"
