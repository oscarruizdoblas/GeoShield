#!/usr/bin/env python3
"""GeoShield - analyse tests produced by run_attack_test.sh: figures + summary table.

    python3 analyze_attack.py TEST_DIR [TEST_DIR ...]

Per test (in ~/geoshield/results/):
  <name>_map.png      REAL trajectory (Gazebo) vs forged GPS vs what the drone believes (EKF),
                      with the no-fly zones, attack start, detection and trusted point.
  <name>_signals.png  the detector signals over time: GPS-EKF divergence, EKF innovation
                      ratios, attack offset and real distance to Palazzo Bo.
For all tests together: results.csv (one row per test) and detection_delay.png.

Key metrics:
  delay_s              detection delay in SIMULATION time: first forged GPS sample -> first alert
  real_error_max_m     max distance between the EKF estimate and the real Gazebo position during
                       the attack (how far the drone is off without knowing it)
  min_dist_bo_m        minimum real distance to the centre of Palazzo Bo (radius 220 m)
  enters_bo / secs_inside_bo / penetration_bo_m   whether and how much the real drone entered it
"""
import sys, os, csv, math, bisect
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from zones import START, DEST, KEEPOUT
from planner import plan

OUT = os.path.expanduser('~/geoshield/results'); os.makedirs(OUT, exist_ok=True)
LAT0, LON0 = START
MLAT = 111194.93; MLON = MLAT * math.cos(math.radians(LAT0))
def en(lat, lon): return ((lon - LON0) * MLON, (lat - LAT0) * MLAT)   # lat/lon -> metres East/North of A
def rd(path):
    if not os.path.exists(path): return []
    with open(path) as f: return list(csv.DictReader(f))
ZON = [(en(z['lat'], z['lon']), z['r'], z['name'].split('(')[0].strip()) for z in KEEPOUT]
ROUTE = [en(la, lo) for la, lo in plan(START, DEST, KEEPOUT)[0]]
DET_LIM = {'dist_hard': 3.0, 'dist_warn': 1.5, 'innov': 0.5}     # same thresholds as detector.py

# Test folder names in Spanish (salto = jump, deriva = drift, sin respuesta = no response,
# corte = cut) -> names shown in the figures and tables.
LEGACY = {'normal': 'normal_flight', 'salto_sin_respuesta': 'jump_no_response', 'deriva_sin_respuesta': 'drift_no_response',
          'salto_respuesta': 'jump_hold_return', 'deriva_respuesta': 'drift_hold_return',
          'salto_corte_gps': 'jump_gps_cut', 'deriva_corte_gps': 'drift_gps_cut',
          'video_deriva_defensa': 'drift_full_defence', 'video_salto_defensa': 'jump_full_defence'}
# response argument of run_attack_test.sh -> readable name
RESP_NAME = {'no': 'none', 'si': 'hold_return', 'corte': 'hold_gps_cut_return'}

def field(info, *keys):
    """Value of key=value in test.txt (English keys, or the Spanish ones: modo, respuesta)."""
    for k in keys:
        if k + '=' in info: return info.split(k + '=')[1].split()[0]
    return '?'

def analyse(d):
    name = os.path.basename(d.rstrip('/')).split('_', 2)[-1]
    name = LEGACY.get(name, name)
    info = open(os.path.join(d, 'test.txt')).read().strip() if os.path.exists(os.path.join(d, 'test.txt')) else ''
    mode = field(info, 'mode', 'modo')
    resp = field(info, 'response', 'respuesta')
    resp = RESP_NAME.get(resp, resp)
    rel = rd(os.path.join(d, 'relay.csv')); sig = rd(os.path.join(d, 'signals.csv'))
    ale = rd(os.path.join(d, 'alerts.csv')); res = rd(os.path.join(d, 'response.csv'))
    if not rel: print("no relay.csv in", d); return None
    t = [float(r['t']) for r in rel]
    tru = [en(float(r['true_lat']), float(r['true_lon'])) for r in rel]     # real position
    spo = [en(float(r['spoof_lat']), float(r['spoof_lon'])) for r in rel]   # GPS sent to PX4
    off = [math.hypot(float(r['off_e']), float(r['off_n'])) for r in rel]   # attack offset
    att = [int(r['attack']) for r in rel]
    alt = [float(r['alt']) for r in rel]
    air = [i for i in range(len(rel)) if alt[i] - alt[0] > 5.0]          # samples while airborne
    t_att = next((t[i] for i in range(len(t)) if att[i]), None)          # attack start
    t_end = next((t[i] for i in range(len(t)) if t_att and t[i] > t_att and not att[i]), None)   # attack end
    t_det = float(ale[0]['t']) if ale else None                          # first alert
    rule = ale[0]['regla'] if ale else ''
    r = {'name': name, 'mode': mode, 'response': resp, 'n_alerts': len(ale), 'first_rule': rule}
    # delay in SIMULATION time (if Gazebo stalls for a moment, wall-clock time would inflate it)
    tsim = [float(x['t_sim']) for x in rel]
    def sim_at(tt): return tsim[min(range(len(t)), key=lambda k: abs(t[k] - tt))]
    r['delay_s'] = max(0.0, sim_at(t_det) - sim_at(t_att)) if (t_att and t_det and t_det >= t_att) else None
    r['false_alarm'] = bool(t_det and (t_att is None or t_det < t_att))
    r['offset_max_m'] = max(off) if off else 0.0
    r['offset_at_detection_m'] = next((off[i] for i in range(len(t)) if t_det and t[i] >= t_det), None) if t_att else None
    # REAL position error (Gazebo vs EKF) while the attack lasts: how far off the drone is without knowing it
    r['real_error_max_m'] = None
    if sig and t_att:
        emax = 0.0
        for s in sig:
            ts_ = float(s['t'])
            if ts_ < t_att or (t_end and ts_ > t_end) or float(s['rel_alt']) < 5: continue
            i = min(len(t) - 1, bisect.bisect_left(t, ts_)); e = en(float(s['ekf_lat']), float(s['ekf_lon']))
            emax = max(emax, math.hypot(e[0] - tru[i][0], e[1] - tru[i][1]))
        r['real_error_max_m'] = emax
    if t_end: air = [i for i in air if t[i] <= t_end + 5.0]            # the later flight home does not count
    for (c, rad, nm) in ZON:
        dmin = min(math.hypot(tru[i][0] - c[0], tru[i][1] - c[1]) for i in air) if air else float('nan')
        key = 'bo' if 'Bo' in nm else 'liviano'
        r['min_dist_%s_m' % key] = dmin
        r['enters_%s' % key] = dmin < rad
        if key == 'bo':
            ins = [i for i in air if math.hypot(tru[i][0] - c[0], tru[i][1] - c[1]) < rad]
            r['secs_inside_bo'] = (len(ins) / 30.0) if ins else 0.0     # the relay logs at ~30 Hz
            r['penetration_bo_m'] = (rad - dmin) if dmin < rad else 0.0
    r['actions'] = [(x['accion'], float(x['t'])) for x in res]

    # ---------- map ----------
    fig, ax = plt.subplots(figsize=(11, 8))
    for (c, rad, nm) in ZON:
        ax.add_patch(Circle(c, rad, facecolor='#ff0000', edgecolor='#7a0000', alpha=0.25, lw=2, hatch='xx'))
        ax.text(c[0], c[1], nm, ha='center', va='center', fontsize=9, color='#7a0000', fontweight='bold')
    ax.plot([p[0] for p in ROUTE], [p[1] for p in ROUTE], '--', color='gray', lw=1.5, label='planned route')
    t_cut = (t_end + 5.0) if t_end else float('inf')      # the map leaves out the flight home after the test
    ia = [i for i in air if t[i] <= t_cut]
    ax.plot([spo[i][0] for i in ia], [spo[i][1] for i in ia], '-', color='#1f77b4', lw=1.6, alpha=0.9, label='GPS received by the drone (forged)')
    if sig:
        ek = [en(float(s['ekf_lat']), float(s['ekf_lon'])) for s in sig if float(s['rel_alt']) > 5 and float(s['t']) <= t_cut]
        ax.plot([p[0] for p in ek], [p[1] for p in ek], ':', color='#ff7f0e', lw=2.2, label='position the drone believes (EKF)')
    ax.plot([tru[i][0] for i in ia], [tru[i][1] for i in ia], '-', color='black', lw=2.6, label='REAL trajectory (Gazebo)')
    def mark(tt, style, lab):
        if tt is None: return
        i = min(range(len(t)), key=lambda k: abs(t[k] - tt))
        ax.plot(tru[i][0], tru[i][1], style, ms=13, mec='black', label=lab, zorder=9)
    mark(t_att, 'r*', 'attack start')
    mark(t_det, 'yv', 'detection')
    for acc, ta in r['actions']:
        if acc == 'EN_PUNTO': mark(ta, 'gs', 'trusted point reached')
    a0 = en(*START); b0 = en(*DEST)
    ax.plot(a0[0], a0[1], 'o', color='lime', ms=12, mec='black'); ax.annotate('A', a0, xytext=(6, 6), textcoords='offset points', fontweight='bold')
    ax.plot(b0[0], b0[1], 's', color='yellow', ms=11, mec='black'); ax.annotate('B', b0, xytext=(6, 6), textcoords='offset points', fontweight='bold')
    ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.set_xlabel('East of A (m)'); ax.set_ylabel('North of A (m)')
    ax.set_xlim(-150, 1850); ax.set_ylim(-250, 1200)
    tit = "%s  (attack: %s, response: %s)\n" % (name, mode, resp)
    tit += "REAL min. distance to Palazzo Bo: %.0f m (radius 220) -> %s" % (r['min_dist_bo_m'], 'ENTERS the zone' if r['enters_bo'] else 'outside the zone')
    ax.set_title(tit); ax.legend(loc='upper left', fontsize=8, framealpha=0.95)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, name + '_map.png'), dpi=110); plt.close(fig)

    # ---------- signals ----------
    if sig:
        ref = t_att or float(sig[0]['t'])            # time axis: seconds since the attack started
        ts = [float(s['t']) - ref for s in sig]
        fig, axs = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True)
        axs[0].plot(ts, [float(s['d_gps_ekf']) for s in sig], color='#1f77b4')
        axs[0].axhline(DET_LIM['dist_hard'], color='red', ls='--', lw=1, label='threshold 3 m')
        axs[0].axhline(DET_LIM['dist_warn'], color='orange', ls='--', lw=1, label='threshold 1.5 m (sustained 3 s)')
        axs[0].set_ylabel('GPS-EKF divergence (m)'); axs[0].set_yscale('symlog', linthresh=1.0); axs[0].legend(fontsize=8, loc='upper right')
        axs[1].plot(ts, [float(s['innov_pos']) for s in sig], label='position', color='#2ca02c')
        axs[1].plot(ts, [float(s['innov_vel']) for s in sig], label='velocity', color='#9467bd')
        axs[1].axhline(DET_LIM['innov'], color='red', ls='--', lw=1, label='threshold 0.5')
        axs[1].set_ylabel('EKF innovation ratio'); axs[1].set_yscale('symlog', linthresh=0.1); axs[1].legend(fontsize=8, loc='upper right')
        axs[2].plot([x - ref for x in t], off, color='black', label='fake GPS offset')
        dbo = [math.hypot(p[0] - ZON[0][0][0], p[1] - ZON[0][0][1]) for p in tru]
        axs[2].plot([x - ref for x in t], dbo, color='#d62728', label='REAL distance to Palazzo Bo')
        axs[2].axhline(220, color='#d62728', ls=':', lw=1, label='zone radius (220 m)')
        axs[2].set_ylabel('metres'); axs[2].set_xlabel('time since attack start (s)' if t_att else 'time (s)'); axs[2].legend(fontsize=8, loc='upper right')
        for axx in axs:
            axx.grid(alpha=0.3)
            if t_att: axx.axvline(0, color='red', lw=1.2)
            if t_det: axx.axvline(t_det - ref, color='goldenrod', lw=1.6)
            if t_end: axx.axvline(t_end - ref, color='gray', lw=1, ls='-.')
        lo = -30 if t_att else ts[0]
        hi = ((t_end - ref + 20) if t_end else ts[-1])
        axs[2].set_xlim(lo, hi)
        s = "%s  -  red: attack start; yellow: detection" % name
        if r['delay_s'] is not None: s += " (delay %.2f s, rule %s)" % (r['delay_s'], rule)
        elif t_att: s += "  ->  NOT DETECTED"
        fig.suptitle(s); plt.tight_layout(); plt.savefig(os.path.join(OUT, name + '_signals.png'), dpi=110); plt.close(fig)
    return r

rows = [x for x in (analyse(d) for d in sys.argv[1:]) if x]
cols = ['name', 'mode', 'response', 'n_alerts', 'first_rule', 'delay_s', 'offset_at_detection_m', 'offset_max_m', 'real_error_max_m',
        'min_dist_bo_m', 'enters_bo', 'secs_inside_bo', 'penetration_bo_m', 'min_dist_liviano_m', 'enters_liviano', 'false_alarm']
with open(os.path.join(OUT, 'results.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(cols)
    for r in rows:
        w.writerow([("%.2f" % r[c]) if isinstance(r.get(c), float) else r.get(c) for c in cols])
det = [r for r in rows if r['delay_s'] is not None]
if det:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([r['name'] for r in det], [r['delay_s'] for r in det], color='#1f77b4')
    for i, r in enumerate(det): ax.text(i, r['delay_s'], "%.2f s" % r['delay_s'], ha='center', va='bottom')
    ax.set_ylabel('detection delay (s)'); ax.set_title('Delay between attack start and first alert'); ax.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=20, ha='right'); plt.tight_layout(); plt.savefig(os.path.join(OUT, 'detection_delay.png'), dpi=110); plt.close(fig)
for r in rows:
    print("%-22s mode=%-5s resp=%-5s alerts=%-3d rule=%-15s delay=%s  offset_det=%s  real_err_max=%s  Bo_min=%.0f m %s (%.0f s inside)" % (
        r['name'], r['mode'], r['response'], r['n_alerts'], r['first_rule'] or '-',
        ("%.2f s" % r['delay_s']) if r['delay_s'] is not None else ('FALSE ALARM' if r['false_alarm'] else 'NO'),
        ("%.1f m" % r['offset_at_detection_m']) if r['offset_at_detection_m'] is not None else '-',
        ("%.0f m" % r['real_error_max_m']) if r['real_error_max_m'] is not None else '-',
        r['min_dist_bo_m'], 'ENTERS' if r['enters_bo'] else 'outside', r['secs_inside_bo']))
print("figures and results.csv in", OUT)
