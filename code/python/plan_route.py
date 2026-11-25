#!/usr/bin/env python3
# GeoShield - planifica la ruta NORMAL mas corta de A a B esquivando las zonas prohibidas.
# Metodo: grafo de visibilidad (A, B y puntos alrededor de cada circulo keep-out) + Dijkstra.
# Dibuja el mapa del escenario: recta directa (cruza zona, en rojo) vs ruta esquivando (verde).
# Guarda scenario_map.png y mission_normal.csv (waypoints lat/lon).
import os, math, io, heapq, csv, time
import numpy as np, requests
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import sys
from zones import START, DEST, KEEPOUT, START_NAME, DEST_NAME
from planner import plan

# Puntos origen/destino: por defecto A->B de zones.py; o cualquier C->D por argumentos:
#   python3 plan_route.py  Clat Clon Dlat Dlon  [tag]
_a = sys.argv[1:]
TAG = 'scenario'
if len(_a) >= 4:
    START = (float(_a[0]), float(_a[1])); DEST = (float(_a[2]), float(_a[3]))
    START_NAME = 'C - origen'; DEST_NAME = 'D - destino'
    TAG = _a[4] if len(_a) >= 5 else 'demo_CD'

MARGIN = 75.0      # m de seguridad alrededor de cada zona (igual que el planificador)
lat0 = (START[0] + DEST[0]) / 2.0
MPLAT, MPLON = 110540.0, 111320.0 * math.cos(math.radians(lat0))
lon0 = (START[1] + DEST[1]) / 2.0
def en(lat, lon): return ((lon - lon0) * MPLON, (lat - lat0) * MPLAT)
def ll(e, n):     return (lat0 + n / MPLAT, lon0 + e / MPLON)

A = en(*START); B = en(*DEST)
ZON = [(en(z['lat'], z['lon']), z['r'], z['name']) for z in KEEPOUT]

# Ruta con el planificador UNICO (planner.plan) -> IDENTICA a la que vuela el dron
# (plan_and_fly.py) y a la mision del .plan de QGC (make_qgc_plan.py). Sin logica
# duplicada aqui: una sola fuente de verdad para que mapa, QGC y vuelo coincidan.
waypoints, d_route, crossed = plan(START, DEST, KEEPOUT, margin=MARGIN)
path = [en(la, lo) for (la, lo) in waypoints]
d_direct = math.hypot(B[0]-A[0], B[1]-A[1])
print("recta directa A->B: %.0f m  (cruza: %s)" % (d_direct, ", ".join(crossed) or "ninguna"), flush=True)
print("ruta esquivando  : %.0f m  (%d waypoints)  +%.0f m (%.0f%%)" % (d_route, len(path), d_route-d_direct, 100*(d_route-d_direct)/d_direct), flush=True)

# guardar waypoints de la mision normal
mi = os.path.expanduser('~/geoshield/mission_%s.csv' % TAG)
with open(mi, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['idx', 'lat', 'lon'])
    for i, (la, lo) in enumerate(waypoints):
        w.writerow([i, "%.7f" % la, "%.7f" % lo])
print("mision:", mi, flush=True)

# ---- mapa OSM ----
pts = [A, B] + [c for (c, r, _) in ZON]
emin = min(p[0] for p in pts) - 300; emax = max(p[0] for p in pts) + 300
nmin = min(p[1] for p in pts) - 300; nmax = max(p[1] for p in pts) + 300
half = max(emax-emin, nmax-nmin) / 2.0
ec = (emin+emax)/2.0; nc = (nmin+nmax)/2.0
clat, clon = ll(ec, nc)
Z = 15
dlat = half/MPLAT; dlon = half/MPLON
def d2n(lat, lon, z):
    n = 2**z; return (lon+180)/360*n, (1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n
fx_l, fy_t = d2n(clat+dlat, clon-dlon, Z); fx_r, fy_b = d2n(clat-dlat, clon+dlon, Z)
x0, y0, x1, y1 = int(fx_l), int(fy_t), int(fx_r), int(fy_b)
TS = 256
mos = Image.new('RGB', ((x1-x0+1)*TS, (y1-y0+1)*TS), (235,235,235))
hd = {'User-Agent': 'GeoShield-student-project/1.0 (cyberphysical security course)'}
for xi in range(x0, x1+1):
    for yi in range(y0, y1+1):
        for att in range(3):
            try:
                r = requests.get("https://tile.openstreetmap.org/%d/%d/%d.png" % (Z, xi, yi), headers=hd, timeout=20)
                r.raise_for_status()
                mos.paste(Image.open(io.BytesIO(r.content)).convert('RGB'), ((xi-x0)*TS, (yi-y0)*TS)); break
            except Exception as e:
                if att == 2: print("  tesela fallida:", e, flush=True)
                time.sleep(1.0)
crop = mos.crop((int(round((fx_l-x0)*TS)), int(round((fy_t-y0)*TS)), int(round((fx_r-x0)*TS)), int(round((fy_b-y0)*TS))))

fig, ax = plt.subplots(figsize=(12, 10))
ax.imshow(np.asarray(crop), extent=[ec-half, ec+half, nc-half, nc+half], origin='upper', zorder=0)
for (c, r, nm) in ZON:
    ax.add_patch(Circle(c, r, facecolor='#ff0000', edgecolor='#7a0000', alpha=0.40, lw=2.5, hatch='xx', zorder=3))
    ax.text(c[0], c[1], 'NO', color='white', fontsize=12, fontweight='bold', ha='center', va='center', zorder=4)
    ax.text(c[0], c[1]-r-25, nm.split('(')[0].strip(), color='#7a0000', fontsize=8, ha='center', va='top', zorder=4)
ax.plot([A[0], B[0]], [A[1], B[1]], '--', color='red', lw=2, alpha=0.8, zorder=5, label='recta directa (cruza zona)')
px = [p[0] for p in path]; py = [p[1] for p in path]
ax.plot(px, py, '-', color='#00a000', lw=3, zorder=6, label='ruta normal (esquiva, %.0f m)' % d_route)
ax.plot(px, py, 'o', color='#00a000', ms=4, zorder=6)
ax.plot(A[0], A[1], 'o', color='lime', ms=15, mec='black', zorder=7)
ax.plot(B[0], B[1], 's', color='yellow', ms=14, mec='black', zorder=7)
ax.annotate(START_NAME, A, textcoords='offset points', xytext=(8, -16), fontsize=9, fontweight='bold', zorder=8)
ax.annotate(DEST_NAME, B, textcoords='offset points', xytext=(8, 10), fontsize=9, fontweight='bold', zorder=8)
ax.set_xlim(ec-half, ec+half); ax.set_ylim(nc-half, nc+half); ax.set_aspect('equal')
ax.set_xlabel('Este (m)'); ax.set_ylabel('Norte (m)')
ax.set_title('GeoShield - escenario Padova: A -> B esquivando la universidad del centro\n(rojo=zonas prohibidas, verde=ruta normal mas corta)')
ax.legend(loc='lower right', framealpha=0.92)
out = os.path.expanduser('~/geoshield/plots/%s_map.png' % TAG)
plt.tight_layout(); plt.savefig(out, dpi=120)
print("mapa:", out, flush=True)
