#!/usr/bin/env python3
# GeoShield - textura OSM para el suelo 3D de Gazebo.
# Centrada en el PUNTO MEDIO de la ruta A<->B para cubrir TODO el escenario
# (salida, zonas del centro y destino Torre Archimede).
import math, io, os, sys
import requests
from PIL import Image
sys.path.insert(0, '/home/oruiz/geoshield')
from zones import START, DEST

HALF = 1000.0           # medio lado en metros -> plano de 2000 m
Z = 15
latm = (START[0] + DEST[0]) / 2.0    # centro = punto medio A-B
lonm = (START[1] + DEST[1]) / 2.0
OUTDIR = "/home/oruiz/PX4-Autopilot/Tools/simulation/gz/models/padova_ground"
os.makedirs(OUTDIR, exist_ok=True)

dlat = HALF / 110540.0
dlon = HALF / (111320.0 * math.cos(math.radians(latm)))
lat_min, lat_max = latm - dlat, latm + dlat
lon_min, lon_max = lonm - dlon, lonm + dlon

def deg2num(lat, lon, z):
    n = 2**z
    return (lon+180.0)/360.0*n, (1.0-math.asinh(math.tan(math.radians(lat)))/math.pi)/2.0*n

fx_l, fy_t = deg2num(lat_max, lon_min, Z)
fx_r, fy_b = deg2num(lat_min, lon_max, Z)
x0, y0 = int(math.floor(fx_l)), int(math.floor(fy_t))
x1, y1 = int(math.floor(fx_r)), int(math.floor(fy_b))
nt = (x1-x0+1)*(y1-y0+1)
print("centro=%.5f,%.5f  teselas:%d" % (latm, lonm, nt), flush=True); assert nt <= 36

TS = 256
mosaic = Image.new('RGB', ((x1-x0+1)*TS, (y1-y0+1)*TS), (235, 235, 235))
hd = {'User-Agent': 'GeoShield-student-project/1.0 (cyberphysical security course)'}
ok = 0
for xi in range(x0, x1+1):
    for yi in range(y0, y1+1):
        for att in range(4):
            try:
                r = requests.get("https://tile.openstreetmap.org/%d/%d/%d.png" % (Z, xi, yi), headers=hd, timeout=25)
                r.raise_for_status()
                mosaic.paste(Image.open(io.BytesIO(r.content)).convert('RGB'), ((xi-x0)*TS, (yi-y0)*TS)); ok += 1; break
            except Exception as e:
                if att == 3: print("  fallo %d/%d: %s" % (xi, yi, e), flush=True)
                import time; time.sleep(1.5)
print("teselas OK %d/%d" % (ok, nt), flush=True)

left   = int(round((fx_l - x0)*TS)); right  = int(round((fx_r - x0)*TS))
top    = int(round((fy_t - y0)*TS)); bottom = int(round((fy_b - y0)*TS))
crop = mosaic.crop((left, top, right, bottom))
crop.save(os.path.join(OUTDIR, "padova_texture.png"))
print("textura:", os.path.join(OUTDIR, "padova_texture.png"), crop.size, flush=True)
print("PLANE_HALF_M=%.1f  CENTER=%.6f,%.6f" % (HALF, latm, lonm), flush=True)
