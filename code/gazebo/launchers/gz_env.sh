#!/usr/bin/env bash
# GeoShield - diagnostics: show the running Gazebo server process, its environment and topics.
SRV=$(pgrep -f 'gz sim.*-s' | head -1)
echo "server pid=$SRV"
if [ -n "$SRV" ]; then
  echo "--- GZ / display environment of the server ---"
  tr '\0' '\n' < /proc/$SRV/environ | grep -iE 'GZ_|PX4_GZ|DISPLAY|WAYLAND|MESA|LIBGL|XDG_RUNTIME' | sort
fi
echo "--- full server command line ---"
if [ -n "$SRV" ]; then tr '\0' ' ' < /proc/$SRV/cmdline; echo; fi
echo "--- gz topic -l (can we reach the server?) ---"
timeout 6 gz topic -l 2>/dev/null | head -20
echo "--- gz version ---"
gz sim --version 2>/dev/null | head -1
