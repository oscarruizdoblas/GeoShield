#!/usr/bin/env python3
"""GeoShield - generate the QGroundControl plan file (code/qground/geoshield_padova.plan).

The .plan (QGC JSON format) contains:
  - the geofence: the keep-in circle and the keep-out circles from zones.py,
  - the normal mission: take-off at A and the planner's waypoints from A to B around the zones.
It lets the scenario be inspected and flown from QGroundControl (Plan -> Open).
Set GEOSHIELD_PLAN_OUTPUT to write it somewhere else.
"""
import json, os
from pathlib import Path
from zones import HOME, KEEPOUT, KEEPIN, START, DEST
from planner import plan

ALT = 40.0   # m above HOME

circles = []
circles.append({"inclusion": True, "version": 1,
                "circle": {"center": [KEEPIN['lat'], KEEPIN['lon']], "radius": KEEPIN['r']}})
for z in KEEPOUT:
    circles.append({"inclusion": False, "version": 1,
                    "circle": {"center": [z['lat'], z['lon']], "radius": z['r']}})

# normal A->B route avoiding the zones -> QGC mission items
wps, L, crossed = plan(START, DEST, KEEPOUT)
items = []
jid = 1
# take-off at A (MAV_CMD_NAV_TAKEOFF = 22; frame 3 = global, relative altitude)
items.append({"type": "SimpleItem", "command": 22, "frame": 3, "autoContinue": True,
              "doJumpId": jid, "AMSLAltAboveTerrain": None, "Altitude": ALT, "AltitudeMode": 1,
              "params": [0, 0, 0, None, START[0], START[1], ALT]})
# intermediate waypoints + destination (MAV_CMD_NAV_WAYPOINT = 16)
for (la, lo) in wps[1:]:
    jid += 1
    items.append({"type": "SimpleItem", "command": 16, "frame": 3, "autoContinue": True,
                  "doJumpId": jid, "AMSLAltAboveTerrain": None, "Altitude": ALT, "AltitudeMode": 1,
                  "params": [0, 0, 0, None, la, lo, ALT]})

plan_obj = {
    "fileType": "Plan",
    "version": 1,
    "groundStation": "QGroundControl",
    "geoFence": {"circles": circles, "polygons": [], "version": 2},
    "mission": {
        "version": 2,
        "firmwareType": 12,      # PX4
        "vehicleType": 2,        # multirotor
        "cruiseSpeed": 15,
        "hoverSpeed": 5,
        "globalPlanAltitudeMode": 1,
        "items": items,
        "plannedHomePosition": [START[0], START[1], 12.0]
    },
    "rallyPoints": {"points": [], "version": 2}
}

out = Path(os.environ.get("GEOSHIELD_PLAN_OUTPUT") or Path(__file__).resolve().parents[1] / "qground" / "geoshield_padova.plan").expanduser()
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(plan_obj, f, indent=4)
print("written:", out)
print("circles:", len(circles), "(1 keep-in + %d keep-out)" % len(KEEPOUT))
print("mission: %d items (take-off + %d waypoints). Route %.0f m; the straight line crosses: %s" % (len(items), len(wps)-1, L, ", ".join(crossed) or "nothing"))
