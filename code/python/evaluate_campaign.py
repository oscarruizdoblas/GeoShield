#!/usr/bin/env python3
"""GeoShield - evaluate a campaign of repeated flights (run_campaign.sh) -> tables and figures.

    python3 evaluate_campaign.py [TAG]        (default: campaign)

Reads ~/geoshield/logs/2*_<TAG>_<scenario>_r<N>/ and writes to ~/geoshield/results/campaign/:
  flights.csv    one row per flight (delay, rule, false alarm, missed detection, real error...)
  summary.csv    one row per scenario (mean, standard deviation, min, max, rates)
  delay_by_scenario.png, detection_vs_drift_speed.png

Definitions:
  - delay: SIMULATION time between the first forged GPS sample and the first alert.
  - false alarm: any alert raised while no attack is active (before it starts).
  - detected: at least one alert while the GPS is being forged. Alerts raised after the attack
    stops do NOT count: when the attacker stops, the GPS snaps back to the true position and
    'salto_GPS' fires, but that detects the END of the attack, not the attack.
  - missed detection (false negative): an attack flight with no alert during the attack.
"""
import sys, os, csv, glob, math, bisect, statistics as st
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from zones import START, KEEPOUT

TAG = sys.argv[1] if len(sys.argv) > 1 else 'campaign'
OUT = os.path.expanduser('~/geoshield/results/campaign'); os.makedirs(OUT, exist_ok=True)
MLAT = 111194.93; MLON = MLAT * math.cos(math.radians(START[0]))
def en(lat, lon): return ((lon - START[1]) * MLON, (lat - START[0]) * MLAT)   # metres East/North of A
BO = next(z for z in KEEPOUT if 'Bo' in z['name']); BOC = en(BO['lat'], BO['lon'])
def rd(p):
    if not os.path.exists(p): return []
    with open(p) as f: return list(csv.DictReader(f))

# Scenario identifiers: Spanish folder names (salto = jump, deriva = drift, sinvel = no velocity)
# are mapped to the English identifiers used in the outputs; both spellings are accepted.
ALIAS = {'salto': 'jump', 'deriva3': 'drift3', 'deriva2': 'drift2', 'deriva1': 'drift1',
         'deriva05': 'drift05', 'deriva1_sinvel': 'drift1_novel'}
ORDER = ['normal', 'jump', 'drift3', 'drift2', 'drift1', 'drift05', 'drift1_novel']
LABEL = {'normal': 'Normal flight', 'jump': 'Jump 180 m', 'drift3': 'Drift 3 m/s', 'drift2': 'Drift 2 m/s',
         'drift1': 'Drift 1 m/s', 'drift05': 'Drift 0.5 m/s', 'drift1_novel': 'Drift 1 m/s, no velocity'}
SPEED = {'drift3': 3.0, 'drift2': 2.0, 'drift1': 1.0, 'drift05': 0.5}   # drifts with coherent velocity

def flight(d):
    """Metrics of one flight folder, or None if its CSVs are missing."""
    base = os.path.basename(d.rstrip('/')); rest = base.split('_', 2)[-1]            # e.g. campaign_drift1_r2
    esc, rep = rest[len(TAG) + 1:].rsplit('_r', 1)
    esc = ALIAS.get(esc, esc)
    rel = rd(os.path.join(d, 'relay.csv')); ale = rd(os.path.join(d, 'alerts.csv'))
    sig = rd(os.path.join(d, 'signals.csv')); res = rd(os.path.join(d, 'response.csv'))
    if not rel or not sig: return None
    t = [float(r['t']) for r in rel]; ts = [float(r['t_sim']) for r in rel]
    def sim(tt): return ts[min(range(len(t)), key=lambda k: abs(t[k] - tt))]     # wall time -> sim time
    att = [int(r['attack']) for r in rel]
    t_att = next((t[i] for i in range(len(t)) if att[i]), None)                      # attack start
    t_end = next((t[i] for i in range(len(t)) if t_att and t[i] > t_att and not att[i]), None)   # attack end
    pre = [a for a in ale if t_att is None or float(a['t']) < t_att]               # alerts with no attack
    # only alerts WHILE the GPS is forged count as detections (see the module docstring)
    post = [a for a in ale if t_att is not None and float(a['t']) >= t_att and (t_end is None or float(a['t']) < t_end)]
    after = [a for a in ale if t_end is not None and float(a['t']) >= t_end]
    tru = [en(float(r['true_lat']), float(r['true_lon'])) for r in rel]
    off = [math.hypot(float(r['off_e']), float(r['off_n'])) for r in rel]
    alt0 = float(rel[0]['alt'])
    fin = (t_end + 5.0) if t_end else t[-1]
    air = [i for i in range(len(t)) if float(rel[i]['alt']) - alt0 > 5.0 and t[i] <= fin]   # airborne, until 5 s after the attack
    dbo = min((math.hypot(tru[i][0] - BOC[0], tru[i][1] - BOC[1]) for i in air), default=float('nan'))
    t_flight = (t[air[-1]] - t[air[0]]) / 60.0 if air else 0.0
    r = {'scenario': esc, 'rep': int(rep), 'folder': '%s_r%s' % (esc, rep), 'attack': t_att is not None,
         'flight_min': t_flight, 'alerts_without_attack': len(pre), 'alerts_during_attack': len(post),
         'false_alarm': len(pre) > 0, 'detected': (len(post) > 0) if t_att else None,
         'first_rule': (post[0]['regla'] if post else (pre[0]['regla'] if pre else '')),
         'delay_s': (max(0.0, sim(float(post[0]['t'])) - sim(t_att)) if post else None),
         'offset_at_detection_m': None, 'real_error_max_m': None, 'min_dist_bo_m': dbo, 'enters_bo': dbo < BO['r'],
         'response_completed': any(x['accion'] == 'EN_PUNTO' for x in res),
         'alert_when_attack_stopped': (after[0]['regla'] if (after and not post) else ''),
         'attack_duration_s': ((sim(t_end) if t_end else ts[-1]) - sim(t_att)) if t_att else None}
    if post:
        td = float(post[0]['t']); r['offset_at_detection_m'] = next((off[i] for i in range(len(t)) if t[i] >= td), off[-1])
    if t_att:
        # real error = distance between the EKF estimate and the true Gazebo position during the attack
        emax = 0.0
        for s in sig:
            x = float(s['t'])
            if x < t_att or (t_end and x > t_end) or float(s['rel_alt']) < 5: continue
            i = min(len(t) - 1, bisect.bisect_left(t, x)); e = en(float(s['ekf_lat']), float(s['ekf_lon']))
            emax = max(emax, math.hypot(e[0] - tru[i][0], e[1] - tru[i][1]))
        r['real_error_max_m'] = emax
    return r

dirs = sorted(glob.glob(os.path.expanduser('~/geoshield/logs/2*_%s_*_r*' % TAG)))
V = [x for x in (flight(d) for d in dirs) if x]
V.sort(key=lambda r: (ORDER.index(r['scenario']) if r['scenario'] in ORDER else 99, r['rep']))
if not V: sys.exit("no flights for campaign %s" % TAG)
def fmt(v): return ('%.3f' % v) if isinstance(v, float) else ('' if v is None else v)
cols = list(V[0].keys())
with open(os.path.join(OUT, 'flights.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(cols); [w.writerow([fmt(r[c]) for c in cols]) for r in V]

# ---- per-scenario summary ----
R = []
for esc in [e for e in ORDER if any(r['scenario'] == e for r in V)]:
    vs = [r for r in V if r['scenario'] == esc]
    ret = [r['delay_s'] for r in vs if r['delay_s'] is not None]
    ata = vs[0]['attack']
    s = {'scenario': esc, 'label': LABEL.get(esc, esc), 'flights': len(vs), 'total_flight_min': sum(r['flight_min'] for r in vs),
         'flights_with_false_alarm': sum(r['false_alarm'] for r in vs), 'alerts_without_attack': sum(r['alerts_without_attack'] for r in vs),
         'detected': sum(1 for r in vs if r['detected']) if ata else None,
         'missed': sum(1 for r in vs if r['detected'] is False) if ata else None,
         'delay_mean_s': st.mean(ret) if ret else None, 'delay_std_s': st.stdev(ret) if len(ret) > 1 else (0.0 if ret else None),
         'delay_min_s': min(ret) if ret else None, 'delay_max_s': max(ret) if ret else None,
         'offset_at_detection_mean_m': st.mean([r['offset_at_detection_m'] for r in vs if r['offset_at_detection_m'] is not None]) if ret else None,
         'first_rules': '; '.join('%s x%d' % kv for kv in Counter(r['first_rule'] for r in vs if r['first_rule']).most_common()),
         'enter_bo': sum(1 for r in vs if r['enters_bo']), 'response_completed': sum(1 for r in vs if r['response_completed'])}
    R.append(s)
cols = list(R[0].keys())
with open(os.path.join(OUT, 'summary.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(cols); [w.writerow([fmt(s[c]) for c in cols]) for s in R]

# ---- figure 1: detection delay per scenario (one dot per flight) ----
A = [s for s in R if s['detected'] is not None]
fig, ax = plt.subplots(figsize=(10, 5.2))
for k, s in enumerate(A):
    vs = [r for r in V if r['scenario'] == s['scenario']]
    ys = [r['delay_s'] for r in vs if r['delay_s'] is not None]
    ax.scatter([k + (j - (len(ys) - 1) / 2) * 0.06 for j in range(len(ys))], ys, color='#1f5fa8', zorder=3, s=36)
    if ys: ax.hlines(st.mean(ys), k - 0.25, k + 0.25, color='black', lw=2, zorder=4)
    fn = s['missed']
    ax.text(k, -0.12, '%d/%d detected' % (s['detected'], s['flights']), ha='center', va='top', fontsize=8,
            color='#c62828' if fn else '#333333', transform=ax.get_xaxis_transform())
ax.set_xticks(range(len(A))); ax.set_xticklabels([s['label'] for s in A], rotation=15, fontsize=9)
ax.set_ylabel('detection delay (s, simulation time)'); ax.set_yscale('symlog', linthresh=0.5)
ymax = max([r['delay_s'] for r in V if r['delay_s'] is not None] or [1.0]); ax.set_ylim(0, ymax * 2)
ax.grid(alpha=0.3, axis='y'); ax.set_title('Detection delay per scenario (dot = one flight, bar = mean)')
plt.tight_layout(); plt.savefig(os.path.join(OUT, 'delay_by_scenario.png'), dpi=120); plt.close(fig)

# ---- figure 2: drifts with coherent velocity: delay and GPS offset at detection vs drift speed ----
D = [s for s in R if s['scenario'] in SPEED]
if D:
    fig, ax1 = plt.subplots(figsize=(8, 4.8)); ax2 = ax1.twinx()
    for s in D:
        vs = [r for r in V if r['scenario'] == s['scenario']]
        x = SPEED[s['scenario']]
        for r in vs:
            if r['delay_s'] is not None: ax1.scatter(x, r['delay_s'], color='#1f5fa8', s=34, zorder=3)
            else: ax1.scatter(x, 0, marker='x', color='#c62828', s=60, zorder=3)
            if r['offset_at_detection_m'] is not None: ax2.scatter(x + 0.05, r['offset_at_detection_m'], color='#e07b00', marker='s', s=26)
    ax1.set_xlabel('drift speed (m/s)'); ax1.set_ylabel('detection delay (s)', color='#1f5fa8')
    ax2.set_ylabel('GPS offset at detection (m)', color='#e07b00'); ax1.set_ylim(bottom=-0.2); ax2.set_ylim(bottom=0)
    ax1.set_title('Coherent drift: time to detect and GPS offset at detection\n(red x = not detected)')
    ax1.grid(alpha=0.3); plt.tight_layout(); plt.savefig(os.path.join(OUT, 'detection_vs_drift_speed.png'), dpi=120); plt.close(fig)

for s in R:
    line = "%-28s n=%d  FA=%d flights (%d alerts)" % (s['label'], s['flights'], s['flights_with_false_alarm'], s['alerts_without_attack'])
    if s['detected'] is not None:
        line += "  detected=%d/%d" % (s['detected'], s['flights'])
        if s['delay_mean_s'] is not None:
            line += "  delay=%.2f+-%.2f s [%.2f-%.2f]  offset=%.1f m" % (s['delay_mean_s'], s['delay_std_s'], s['delay_min_s'], s['delay_max_s'], s['offset_at_detection_mean_m'])
        line += "  rules: %s  enter_bo=%d" % (s['first_rules'], s['enter_bo'])
    print(line)
print("-> %s" % OUT)
