#!/usr/bin/env python3
"""GeoShield - OpenStreetMap texture for the Gazebo ground plane.

Downloads the OSM tiles (zoom 15) covering a 2 km x 2 km square centred on the MIDPOINT of
the A<->B route, so the whole scenario (take-off, the city-centre zones and the Torre
Archimede destination) is visible, stitches them and crops the mosaic to the exact square.
The result is models/padova_ground/padova_texture.png, used by the world from build_world.py.
"""
import math, io, os, time
from pathlib import Path
import requests
from PIL import Image
from zones import START, DEST

HALF = 1000.0           # half side in metres -> 2000 m plane
Z = 15                  # OSM zoom level
latm = (START[0] + DEST[0]) / 2.0    # centre = A-B midpoint
lonm = (START[1] + DEST[1]) / 2.0
PX4_DIR = Path(os.environ.get("PX4_DIR", Path.home() / "PX4-Autopilot")).expanduser()
MODELS_DIR = Path(os.environ.get("PX4_GZ_MODELS", PX4_DIR / "Tools/simulation/gz/models")).expanduser()
OUTDIR = MODELS_DIR / "padova_ground"
OUTDIR.mkdir(parents=True, exist_ok=True)

# lat/lon bounds of the square
dlat = HALF / 110540.0
dlon = HALF / (111320.0 * math.cos(math.radians(latm)))
lat_min, lat_max = latm - dlat, latm + dlat
lon_min, lon_max = lonm - dlon, lonm + dlon

def deg2num(lat, lon, z):
    """Fractional OSM (slippy map) tile coordinates of a point."""
    n = 2**z
    return (lon+180.0)/360.0*n, (1.0-math.asinh(math.tan(math.radians(lat)))/math.pi)/2.0*n

fx_l, fy_t = deg2num(lat_max, lon_min, Z)
fx_r, fy_b = deg2num(lat_min, lon_max, Z)
x0, y0 = int(math.floor(fx_l)), int(math.floor(fy_t))
x1, y1 = int(math.floor(fx_r)), int(math.floor(fy_b))
nt = (x1-x0+1)*(y1-y0+1)
print("centre=%.5f,%.5f  tiles:%d" % (latm, lonm, nt), flush=True); assert nt <= 36

TS = 256   # tile size in pixels
mosaic = Image.new('RGB', ((x1-x0+1)*TS, (y1-y0+1)*TS), (235, 235, 235))
hd = {'User-Agent': 'GeoShield-student-project/1.0 (cyberphysical security course)'}
ok = 0
for xi in range(x0, x1+1):
    for yi in range(y0, y1+1):
        for att in range(4):          # up to 4 attempts per tile
            try:
                r = requests.get("https://tile.openstreetmap.org/%d/%d/%d.png" % (Z, xi, yi), headers=hd, timeout=25)
                r.raise_for_status()
                mosaic.paste(Image.open(io.BytesIO(r.content)).convert('RGB'), ((xi-x0)*TS, (yi-y0)*TS)); ok += 1; break
            except Exception as e:
                if att == 3: print("  failed %d/%d: %s" % (xi, yi, e), flush=True)
                time.sleep(1.5)
print("tiles OK %d/%d" % (ok, nt), flush=True)

# crop the mosaic to the exact square
left   = int(round((fx_l - x0)*TS)); right  = int(round((fx_r - x0)*TS))
top    = int(round((fy_t - y0)*TS)); bottom = int(round((fy_b - y0)*TS))
crop = mosaic.crop((left, top, right, bottom))
texture_path = OUTDIR / "padova_texture.png"
crop.save(texture_path)
print("texture:", texture_path, crop.size, flush=True)
print("PLANE_HALF_M=%.1f  CENTER=%.6f,%.6f" % (HALF, latm, lonm), flush=True)
