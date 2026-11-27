#!/usr/bin/env bash
# GeoShield - Gazebo camera presets (the view follows the drone with a fixed offset).
#   bash cam.sh oblique  -> from the south-west, diagonal: drone in front, Palazzo Bo behind
#   bash cam.sh top      -> bird's-eye view at map scale, like QGroundControl
#   bash cam.sh close    -> right next to the drone
#   bash cam.sh demo     -> medium distance, meant for the enlarged drone (DEMO_SCALE=40); used in the videos
# In the window: wheel = zoom, left button = rotate, middle button = pan.
case "${1:-oblique}" in
  top)   OFF="x: -10, y: -90, z: 480" ;;
  close) OFF="x: -25, y: -25, z: 18" ;;
  demo)  OFF="x: -10, y: -40, z: 22" ;;
  *)     OFF="x: -60, y: -260, z: 340" ;;
esac
gz service -s /gui/follow --reqtype gz.msgs.StringMsg --reptype gz.msgs.Boolean --timeout 3000 --req 'data: "x500_0"' >/dev/null
gz service -s /gui/follow/offset --reqtype gz.msgs.Vector3d --reptype gz.msgs.Boolean --timeout 3000 --req "$OFF" >/dev/null && echo "camera ${1:-oblique}"
