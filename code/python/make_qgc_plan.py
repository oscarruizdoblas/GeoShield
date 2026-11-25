import json, os, shutil
from datetime import datetime
from pathlib import Path
from zones import HOME, KEEPOUT, KEEPIN, START, DEST
from planner import plan

ALT = 40.0

circles = []
circles.append({"inclusion": True, "version": 1,
                "circle": {"center": [KEEPIN['lat'], KEEPIN['lon']], "radius": KEEPIN['r']}})
for z in KEEPOUT:
    circles.append({"inclusion": False, "version": 1,
                    "circle": {"center": [z['lat'], z['lon']], "radius": z['r']}})

# ruta normal A->B esquivando las zonas -> items de mision para QGC
wps, L, crossed = plan(START, DEST, KEEPOUT)
items = []
jid = 1
# despegue en A
items.append({"type": "SimpleItem", "command": 22, "frame": 3, "autoContinue": True,
              "doJumpId": jid, "AMSLAltAboveTerrain": None, "Altitude": ALT, "AltitudeMode": 1,
              "params": [0, 0, 0, None, START[0], START[1], ALT]})
# waypoints intermedios + destino
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

default_plan = Path(__file__).resolve().parents[1] / "qground" / "geoshield_padova.plan"
out = Path(os.environ.get("GEOSHIELD_PLAN_OUTPUT") or default_plan).expanduser()
out.parent.mkdir(parents=True, exist_ok=True)
if out.exists():
    backup_root = Path(os.environ.get("GEOSHIELD_BACKUP_DIR", Path.home() / ".local/share/geoshield/backups")) / ("plan-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out, backup_root / out.name)
    print("copia de seguridad:", backup_root / out.name)
with open(out, "w", encoding="utf-8") as f:
    json.dump(plan_obj, f, indent=4)
print("escrito:", out)
print("circulos:", len(circles), "(1 keep-in + %d keep-out)" % len(KEEPOUT))
print("mision: %d items (despegue + %d waypoints). Ruta %.0f m; recta cruza: %s" % (len(items), len(wps)-1, L, ", ".join(crossed) or "nada"))
