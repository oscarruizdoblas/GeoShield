#!/usr/bin/env bash
SRV=$(pgrep -f 'gz sim.*-s' | head -1)
echo "server pid=$SRV"
if [ -n "$SRV" ]; then
  echo "--- GZ / display env del servidor ---"
  tr '\0' '\n' < /proc/$SRV/environ | grep -iE 'GZ_|PX4_GZ|DISPLAY|WAYLAND|MESA|LIBGL|XDG_RUNTIME' | sort
fi
echo "--- comando completo del servidor ---"
if [ -n "$SRV" ]; then tr '\0' ' ' < /proc/$SRV/cmdline; echo; fi
echo "--- gz topic -l (conectamos al servidor?) ---"
timeout 6 gz topic -l 2>/dev/null | head -20
echo "--- version gz ---"
gz sim --version 2>/dev/null | head -1
