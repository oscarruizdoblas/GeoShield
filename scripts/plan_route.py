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
sys.path.insert(0, '/home/oruiz/geoshield')
from zones import START, DEST, KEEPOUT, START_NAME, DEST_NAME

# Puntos origen/destino: por defecto A->B de zones.py; o cualquier C->D por argumentos:
#   python3 plan_route.py  Clat Clon Dlat Dlon  [tag]
_a = sys.argv[1:]
TAG = 'scenario'
if len(_a) >= 4:
    START = (float(_a[0]), float(_a[1])); DEST = (float(_a[2]), float(_a[3]))
    START_NAME = 'C - origen'; DEST_NAME = 'D - destino'
    TAG = _a[4] if len(_a) >= 5 else 'demo_CD'

MARGIN = 75.0      # m de seguridad alrededor de cada zona
NRING  = 48        # puntos por circulo
lat0 = (START[0] + DEST[0]) / 2.0
MPLAT, MPLON = 110540.0, 111320.0 * math.cos(math.radians(lat0))
lon0 = (START[1] + DEST[1]) / 2.0
def en(lat, lon): return ((lon - lon0) * MPLON, (lat - lat0) * MPLAT)
def ll(e, n):     return (lat0 + n / MPLAT, lon0 + e / MPLON)

A = en(*START); B = en(*DEST)
ZON = [(en(z['lat'], z['lon']), z['r'], z['name']) for z in KEEPOUT]

def seg_hits_disc(p, q, c, r):
    # distancia minima del segmento pq al centro c < r  -> lo atraviesa
    px, py = p; qx, qy = q; cx, cy = c
    dx, dy = qx - px, qy - py
    L2 = dx*dx + dy*dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((cx-px)*dx + (cy-py)*dy)/L2))
    hx, hy = px + t*dx, py + t*dy
    return math.hypot(cx-hx, cy-hy) < r - 1e-6

def blocked(p, q):
    return any(seg_hits_disc(p, q, c, r) for (c, r, _) in ZON)

# ---- nodos: A, B, anillos alrededor de cada zona ----
nodes = [A, B]
for (c, r, _) in ZON:
    for k in range(NRING):
        a = 2*math.pi*k/NRING
        nodes.append((c[0] + (r+MARGIN)*math.cos(a), c[1] + (r+MARGIN)*math.sin(a)))
N = len(nodes)

# ---- aristas visibles ----
adj = [[] for _ in range(N)]
for i in range(N):
    for j in range(i+1, N):
        if not blocked(nodes[i], nodes[j]):
            d = math.hypot(nodes[i][0]-nodes[j][0], nodes[i][1]-nodes[j][1])
            adj[i].append((j, d)); adj[j].append((i, d))

# ---- Dijkstra A(0) -> B(1) ----
INF = float('inf'); dist = [INF]*N; prev = [-1]*N; dist[0] = 0
pq = [(0.0, 0)]
while pq:
    d, u = heapq.heappop(pq)
    if d > dist[u]: continue
    if u == 1: break
    for v, w in adj[u]:
        nd = d + w
        if nd < dist[v]:
            dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
path = []
u = 1
while u != -1:
    path.append(nodes[u]); u = prev[u]
path.reverse()

d_direct = math.hypot(B[0]-A[0], B[1]-A[1])
d_route  = dist[1]
crossed = [nm for (c, r, nm) in ZON if seg_hits_disc(A, B, c, r)]
print("recta directa A->B: %.0f m  (cruza: %s)" % (d_direct, ", ".join(crossed) or "ninguna"), flush=True)
print("ruta esquivando  : %.0f m  (%d waypoints)  +%.0f m (%.0f%%)" % (d_route, len(path), d_route-d_direct, 100*(d_route-d_direct)/d_direct), flush=True)

# guardar waypoints de la mision normal
mi = os.path.expanduser('~/geoshield/mission_%s.csv' % TAG)
with open(mi, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['idx', 'lat', 'lon'])
    for i, p in enumerate(path):
        la, lo = ll(*p); w.writerow([i, "%.7f" % la, "%.7f" % lo])
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
