#!/usr/bin/env python3
"""GeoShield - analysis of a BASELINE flight (no spoofing): characterises the signals the
detector will use, so its thresholds can be set just above normal behaviour.

Computes the raw GPS <-> EKF distance, the EKF innovation ratios and the position jump between
samples; prints statistics (mean/std/p50/p99/max), saves histograms and suggests thresholds
(baseline + margin). The detector thresholds in detector.py were chosen from these numbers.

Usage: python3 analyze.py [log_folder]   (default: the latest folder in ~/geoshield/logs)
Inputs: gps_raw.csv, global_pos.csv, est_status.csv (from logger.py or plan_and_fly.py).
"""
import sys, os, glob, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LOGS = os.path.expanduser('~/geoshield/logs')
d = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(os.path.join(LOGS, '*/')))[-1]
d = d.rstrip('/')
PLOTS = os.path.expanduser('~/geoshield/plots')
os.makedirs(PLOTS, exist_ok=True)
print("analysing:", d, flush=True)

def load(name):
    p = os.path.join(d, name + '.csv')
    return pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 0 else pd.DataFrame()

gps = load('gps_raw'); gp = load('global_pos'); est = load('est_status'); loc = load('local_ned')

def hav(lat1, lon1, lat2, lon2):
    """Vectorised haversine distance in metres."""
    R = 6371000.0
    p1 = np.radians(lat1); p2 = np.radians(lat2)
    dp = np.radians(lat2 - lat1); dl = np.radians(lon2 - lon1)
    a = np.sin(dp/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

def stats(x, unit=''):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) == 0: return None
    return dict(n=len(x), mean=np.mean(x), std=np.std(x), p50=np.percentile(x,50),
                p99=np.percentile(x,99), mx=np.max(x), unit=unit)
def show(name, s):
    if s is None: print("  %-26s (no data)" % name, flush=True); return
    print("  %-26s n=%-5d mean=%.3f  std=%.3f  p50=%.3f  p99=%.3f  max=%.3f %s"
          % (name, s['n'], s['mean'], s['std'], s['p50'], s['p99'], s['mx'], s['unit']), flush=True)

report = {}
print("\n=== 1) Raw GPS <-> fused EKF distance ===", flush=True)
dist = np.array([])
if not gps.empty and not gp.empty:
    # pair every GPS sample with the nearest EKF sample in time (within 0.3 s)
    g1 = gps[['t','lat','lon']].sort_values('t').rename(columns={'lat':'glat','lon':'glon'})
    g2 = gp[['t','lat','lon']].sort_values('t').rename(columns={'lat':'elat','lon':'elon'})
    merged = pd.merge_asof(g1, g2, on='t', direction='nearest', tolerance=0.3).dropna()
    dist = hav(merged['glat'], merged['glon'], merged['elat'], merged['elon']).values
    report['dist_gps_ekf'] = stats(dist, 'm'); show('dist_gps_ekf [m]', report['dist_gps_ekf'])

print("\n=== 2) EKF innovation ratios (ESTIMATOR_STATUS) ===", flush=True)
for col, lab in [('vel_ratio','vel'),('pos_h_ratio','pos_horiz'),('pos_v_ratio','pos_vert'),('mag_ratio','mag')]:
    if col in est.columns:
        report['innov_'+lab] = stats(est[col], ''); show('innov_'+lab, report['innov_'+lab])

print("\n=== 3) EKF position jump between samples (apparent speed) ===", flush=True)
jump = np.array([])
if not gp.empty:
    g = gp.sort_values('t').reset_index(drop=True)
    seg = hav(g['lat'][:-1].values, g['lon'][:-1].values, g['lat'][1:].values, g['lon'][1:].values)
    dt = np.diff(g['t'].values); dt[dt <= 0] = np.nan
    jump = seg; speed = seg/dt
    report['jump_m'] = stats(jump, 'm'); show('pos_jump [m/sample]', report['jump_m'])
    report['speed_aparente'] = stats(speed, 'm/s'); show('apparent_speed [m/s]', report['speed_aparente'])

# ---- histograms ----
fig, ax = plt.subplots(2, 2, figsize=(11, 8))
if dist.size:
    ax[0,0].hist(dist, bins=40, color='#1f77b4'); ax[0,0].set_title('GPS <-> EKF distance [m]')
    ax[0,0].axvline(np.percentile(dist,99), color='r', ls='--', label='p99'); ax[0,0].legend()
for col, a, t in [('pos_h_ratio', ax[0,1], 'Horizontal position innovation'),
                  ('vel_ratio', ax[1,0], 'Velocity innovation')]:
    if col in est.columns:
        v = est[col].dropna().values
        a.hist(v, bins=40, color='#ff7f0e'); a.set_title(t)
        a.axvline(np.percentile(v,99), color='r', ls='--', label='p99'); a.legend()
if jump.size:
    ax[1,1].hist(jump[np.isfinite(jump)], bins=40, color='#2ca02c'); ax[1,1].set_title('Position jump [m/sample]')
    ax[1,1].axvline(np.percentile(jump[np.isfinite(jump)],99), color='r', ls='--', label='p99'); ax[1,1].legend()
plt.suptitle('GeoShield - baseline flight (no spoofing): %s' % os.path.basename(d))
plt.tight_layout()
out = os.path.join(PLOTS, 'baseline_hist_%s.png' % os.path.basename(d))
plt.savefig(out, dpi=110); print("\nhistograms:", out, flush=True)

# ---- statistics table used to choose the thresholds ----
rows = ["signal,n,mean,std,p50,p99,max,unit"]
for k, s in report.items():
    if s: rows.append("%s,%d,%.4f,%.4f,%.4f,%.4f,%.4f,%s" % (k, s['n'], s['mean'], s['std'], s['p50'], s['p99'], s['mx'], s['unit']))
csvout = os.path.join(d, 'baseline_stats.csv')
open(csvout, 'w').write("\n".join(rows) + "\n")
print("statistics:", csvout, flush=True)
print("\nSUGGESTED THRESHOLDS (baseline + margin):", flush=True)
if report.get('dist_gps_ekf'): print("  dist_gps_ekf  > %.1f m  (p99=%.1f)" % (report['dist_gps_ekf']['p99']*1.5, report['dist_gps_ekf']['p99']), flush=True)
if report.get('innov_pos_horiz'): print("  innov_pos_h   > %.2f    (p99=%.2f)" % (max(1.0, report['innov_pos_horiz']['p99']*1.5), report['innov_pos_horiz']['p99']), flush=True)
if report.get('jump_m'): print("  pos_jump      > %.1f m  (p99=%.1f)" % (report['jump_m']['p99']*2.0, report['jump_m']['p99']), flush=True)
print("END-ANALYSIS", flush=True)
