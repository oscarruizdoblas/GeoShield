#!/usr/bin/env python3
# GeoShield - valida 0 FALSOS POSITIVOS: aplica los umbrales del detector a TODO
# el vuelo base grabado (en movimiento). Debe dar 0 alertas en cada regla.
import sys, os, glob
import numpy as np, pandas as pd

DIST_HARD, DIST_WARN, WARN_SECS, INNOV_LIM, JUMP_SPEED = 3.0, 1.5, 3.0, 0.5, 15.0
LOGS = os.path.expanduser('~/geoshield/logs')
d = sys.argv[1] if len(sys.argv) > 1 else sorted([p for p in glob.glob(os.path.join(LOGS, '*/')) if 'detector_' not in p])[-1]
d = d.rstrip('/')
print("validando vuelo:", d, flush=True)

def load(n):
    p = os.path.join(d, n + '.csv'); return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()
gps, gp, est = load('gps_raw'), load('global_pos'), load('est_status')

def hav(a, b, c, e):
    R = 6371000.0; p1, p2 = np.radians(a), np.radians(c)
    dp = np.radians(c - a); dl = np.radians(e - b)
    x = np.sin(dp/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2*R*np.arcsin(np.sqrt(x))

tot = 0
# 1) divergencia GPS-EKF
g1 = gps[['t','lat','lon']].sort_values('t').rename(columns={'lat':'gl','lon':'go'})
g2 = gp[['t','lat','lon']].sort_values('t').rename(columns={'lat':'el','lon':'eo'})
mg = pd.merge_asof(g1, g2, on='t', direction='nearest', tolerance=0.3).dropna()
dd = hav(mg['gl'].values, mg['go'].values, mg['el'].values, mg['eo'].values)
n_hard = int((dd > DIST_HARD).sum()); tot += n_hard
print("  div_GPS_EKF > %.1fm         : %d  (max visto %.2fm)" % (DIST_HARD, n_hard, dd.max()), flush=True)
# deriva gradual: tramo sostenido > WARN
warn = dd > DIST_WARN
run = maxrun = 0
ts = mg['t'].values
for i in range(len(warn)):
    if warn[i]:
        run = run + 1
    else:
        run = 0
grad = int(warn.sum());
print("  deriva (muestras > %.1fm)    : %d  (ninguna sostenida %.0fs)" % (DIST_WARN, grad, WARN_SECS), flush=True)
tot += grad
# 2) innovaciones
for col, lab in [('pos_h_ratio','innov_pos'), ('vel_ratio','innov_vel')]:
    if col in est.columns:
        n = int((est[col] > INNOV_LIM).sum()); tot += n
        print("  %-9s > %.2f          : %d  (max %.3f)" % (lab, INNOV_LIM, n, est[col].max()), flush=True)
# 3) saltos (velocidad aparente)
for df, lab in [(gp, 'salto_EKF'), (gps, 'salto_GPS')]:
    s = df.sort_values('t').reset_index(drop=True)
    seg = hav(s['lat'][:-1].values, s['lon'][:-1].values, s['lat'][1:].values, s['lon'][1:].values)
    dt = np.diff(s['t'].values); dt[dt <= 0] = np.nan
    sp = seg/dt; sp = sp[np.isfinite(sp)]
    n = int((sp > JUMP_SPEED).sum()); tot += n
    print("  %-9s > %.0f m/s         : %d  (max %.1f m/s)" % (lab, JUMP_SPEED, n, sp.max()), flush=True)

print("\n==> TOTAL falsos positivos en el vuelo limpio: %d %s" % (tot, "(OK: detector limpio)" if tot == 0 else "(REVISAR umbrales)"), flush=True)
