#!/usr/bin/env python3
"""GeoShield - live GPS spoofing DETECTOR + resilient RESPONSE (pymavlink).

It listens on its OWN MAVLink link (UDP 14541, added by install_px4_mavlink.sh), so it runs
side by side with plan_and_fly.py, which flies the mission over UDP 14540.

Usage:  python3 detector.py [seconds] [--port 14541] [--respond] [--cut-gps] [--logdir DIR]

Monitored signals (thresholds calibrated on clean flights with analyze.py -> 0 false positives):
  1) d_gps_ekf : distance between the raw GPS fix (GPS_RAW_INT) and the EKF position
                 estimate (GLOBAL_POSITION_INT). A sudden spoof makes them disagree.
  2) innov_*   : EKF innovation test ratios (ESTIMATOR_STATUS): how surprised the EKF is by a
                 GPS measurement relative to its prediction; the EKF rejects data at 1.0.
                 A moderate but SUSTAINED velocity innovation reveals the start of a stealthy
                 drift whose position and velocity are consistent.
  3) jump      : apparent speed between consecutive samples (a "teleport" of the fix).

Detection rules (identifiers as they appear in alerts.csv):
  salto_GPS       raw GPS jumps faster than JUMP_SPEED                    ("GPS jump")
  salto_EKF       EKF position jumps faster than JUMP_SPEED               ("EKF jump")
  div_GPS_EKF     GPS-EKF distance > DIST_HARD                            ("GPS/EKF divergence")
  deriva_gradual  GPS-EKF distance > DIST_WARN for WARN_SECS              ("gradual drift")
  innov_pos       position innovation ratio > INNOV_LIM
  innov_vel       velocity innovation ratio > INNOV_LIM
  innov_sostenida velocity innovation > INNOV_SOFT for INNOV_SECS         ("sustained innovation")

Response (--respond), triggered by the FIRST alert (action names as in response.csv):
  HOLD       create ~/geoshield/run/ABORT (plan_and_fly.py stops sending waypoints) and order an
             immediate hold at the current estimated position
  AVISO      ("warning") STATUSTEXT to the ground station (shown by QGroundControl); also printed and logged
  CORTE_GPS  ("GPS cut", only with --cut-gps) tell PX4 to stop fusing GPS (EKF2_GPS_CTRL=0) so the
             estimate no longer follows the forged fix; the EKF dead-reckons on the IMU
  RETORNO    ("return") after the hold time, fly back to the LAST TRUSTED POINT: the EKF position
             TRUST_BACK seconds before the first anomaly
  EN_PUNTO   ("at point") trusted point reached; the drone waits there
Everything is logged to CSV: alerts.csv, signals.csv, response.csv.
"""
import sys, os, time, csv, math, argparse, signal, struct
from collections import deque
from datetime import datetime
from pymavlink import mavutil

# ---- THRESHOLDS (baseline = mean/p99/max over clean flights; margins chosen for 0 false positives) ----
DIST_HARD   = 3.0    # m   large GPS-EKF divergence                    (baseline max ~1.0)
DIST_WARN   = 1.5    # m   moderate divergence ...
WARN_SECS   = 3.0    # s   ... sustained this long -> GRADUAL drift      (baseline never above 1.0)
INNOV_LIM   = 0.5    #     position/velocity innovation ratio         (baseline max 0.02-0.11; EKF rejects at 1.0)
INNOV_SOFT  = 0.15   #     moderate velocity innovation ...          (baseline never above 0.12)
INNOV_SECS  = 1.0    # s   ... sustained this long -> start of a drift with coherent velocity
JUMP_SPEED  = 15.0   # m/s apparent speed between samples             (baseline max ~6.4)
COOLDOWN    = 2.0    # s   do not repeat the same alert in bursts
# ---- RESPONSE ----
HOLD_SECS   = 5.0    # s   time holding before returning to the trusted point
HOLD_SECS_CUT = 2.0  # s   same with --cut-gps (without GPS, inertial navigation is only valid for a few seconds)
TRUST_BACK  = 5.0    # s   the trusted point is the EKF position this long before the anomaly
REACH       = 15.0   # m   radius to consider the trusted point reached

ap = argparse.ArgumentParser(description='GeoShield GPS spoofing detector and response')
ap.add_argument('seconds', nargs='?', type=float, default=None, help='run time (default: until stopped)')
ap.add_argument('--port', type=int, default=14541)
ap.add_argument('--respond', action='store_true', help='enable the resilient response')
ap.add_argument('--cut-gps', action='store_true', help='(with --respond) stop fusing GPS when an attack is detected')
ap.add_argument('--logdir', default=None)
a = ap.parse_args()
DUR = a.seconds

def hav(a_, b, c, d):
    """Haversine distance in metres between (lat a_, lon b) and (lat c, lon d)."""
    R = 6371000.0; p1, p2 = math.radians(a_), math.radians(c)
    dp = math.radians(c - a_); dl = math.radians(d - b)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

RUN = os.path.expanduser('~/geoshield/run'); os.makedirs(RUN, exist_ok=True)
ABORT_FLAG = os.path.join(RUN, 'ABORT')       # tells plan_and_fly.py to abandon the mission
LOGDIR = a.logdir or os.path.expanduser('~/geoshield/logs/detector_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(LOGDIR, exist_ok=True)
# CSV column names are kept as in the recorded evidence: regla = rule, valor = value,
# umbral = threshold, detalle = detail, accion = action
af = open(os.path.join(LOGDIR, 'alerts.csv'), 'w', newline='')
aw = csv.writer(af); aw.writerow(['t', 'iso', 'regla', 'valor', 'umbral', 'detalle']); af.flush()
sf = open(os.path.join(LOGDIR, 'signals.csv'), 'w', newline='')
sw = csv.writer(sf); sw.writerow(['t', 'd_gps_ekf', 'innov_pos', 'innov_vel', 'gps_lat', 'gps_lon', 'ekf_lat', 'ekf_lon', 'rel_alt', 'n_alert'])
rf = open(os.path.join(LOGDIR, 'response.csv'), 'w', newline='')
rw = csv.writer(rf); rw.writerow(['t', 'iso', 'accion', 'lat', 'lon', 'detalle']); rf.flush()

def _term(*_): raise KeyboardInterrupt
signal.signal(signal.SIGTERM, _term)

last_cool = {}
n_alert = 0
first_alert = [None]   # (t, rule) of the first alert: it triggers the response
def alerta(regla, valor, umbral, detalle):
    """Raise an alert (rule, measured value, threshold, explanation), rate-limited per rule."""
    global n_alert
    now = time.time()
    if now - last_cool.get(regla, 0) < COOLDOWN:
        return
    last_cool[regla] = now; n_alert += 1
    if first_alert[0] is None: first_alert[0] = (now, regla)
    iso = datetime.now().strftime('%H:%M:%S')
    print("  ! [%s] ALERT %-15s value=%.3f (threshold %.3f)  %s" % (iso, regla, valor, umbral, detalle), flush=True)
    aw.writerow(["%.3f" % now, iso, regla, "%.4f" % valor, "%.4f" % umbral, detalle]); af.flush()

def accion(nombre, lat, lon, detalle):
    """Log one step of the response (name, position, explanation)."""
    now = time.time(); iso = datetime.now().strftime('%H:%M:%S')
    print("  >> [%s] RESPONSE %-18s %s" % (iso, nombre, detalle), flush=True)
    rw.writerow(["%.3f" % now, iso, nombre, "%.7f" % lat, "%.7f" % lon, detalle]); rf.flush()

m = mavutil.mavlink_connection('udpin:0.0.0.0:%d' % a.port, source_system=250, source_component=191)
print("GeoShield DETECTOR -> waiting for heartbeat on %d..." % a.port, flush=True)
if m.wait_heartbeat(timeout=30) is None:
    print("NO HEARTBEAT on %d (PX4 not running, or the link is missing: bash install_px4_mavlink.sh and restart the SITL)" % a.port, flush=True); sys.exit(1)
print("link OK. Monitoring%s. Log -> %s" % (" WITH RESPONSE" + (" + GPS cut" if a.cut_gps else "") if a.respond else "", LOGDIR), flush=True)
print("thresholds: dist_hard=%.1fm  dist_warn=%.1fm/%.0fs  innov=%.2f  innov_sustained=%.2f/%.0fs  jump=%.0fm/s" % (DIST_HARD, DIST_WARN, WARN_SECS, INNOV_LIM, INNOV_SOFT, INNOV_SECS, JUMP_SPEED), flush=True)
# Ask PX4 for faster streams: GPS_RAW_INT (24) at 5 Hz, GLOBAL_POSITION_INT (33) at 10 Hz,
# ESTIMATOR_STATUS (230) at 5 Hz
for mid, us in [(24, 200000), (33, 100000), (230, 200000)]:
    m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, float(mid), float(us), 0, 0, 0, 0, 0); time.sleep(0.1)

def reposition(lat, lon, alt_amsl):
    """Fly to (lat, lon, alt) and hold there (MAV_CMD_DO_REPOSITION, switches PX4 to Hold mode)."""
    m.mav.command_int_send(1, 1, mavutil.mavlink.MAV_FRAME_GLOBAL_INT, mavutil.mavlink.MAV_CMD_DO_REPOSITION, 0, 0,
                           -1.0, 1.0, 0.0, float('nan'), int(lat*1e7), int(lon*1e7), float(alt_amsl))
def set_int(name, val):
    """Set an INT32 PX4 parameter. PX4 copies param_value byte by byte, so the integer's bytes
    must be packed inside the float (sending float(val) would store a wrong integer)."""
    m.mav.param_set_send(1, 1, name, struct.unpack('<f', struct.pack('<i', int(val)))[0], mavutil.mavlink.MAV_PARAM_TYPE_INT32)
def aviso(texto):
    """Send a critical STATUSTEXT warning to the ground station (max 49 characters)."""
    m.mav.statustext_send(mavutil.mavlink.MAV_SEVERITY_CRITICAL, texto.encode()[:49])

last_gps = None   # (t_arrival, lat, lon, t_sample) of the latest raw GPS fix
last_gp  = None   # (t_arrival, lat, lon, alt_amsl, rel_alt, vn, ve, t_sample) of the latest EKF estimate
prev_gps = None
prev_gp  = None
warn_since = None           # start of a moderate GPS-EKF divergence
soft_since = None           # start of a moderate velocity innovation
anom_since = None           # first instant with any indicator outside its nominal range
hist = deque(maxlen=1200)   # (t, lat, lon, alt_amsl) EKF positions recorded while everything was nominal
cur = {'d': 0.0, 'ih': 0.0, 'iv': 0.0}    # current divergence and innovation ratios
resp = {'state': 'idle', 't': 0.0, 'trust': None, 'hold': None, 'resend': 0}   # response state machine
t0 = time.time(); lp = 0; lflush = 0; lhb = 0
try:
    while DUR is None or time.time() - t0 < DUR:
        msg = m.recv_match(type=['GPS_RAW_INT', 'GLOBAL_POSITION_INT', 'ESTIMATOR_STATUS'], blocking=True, timeout=1)
        now = time.time()
        if now - lhb > 1.0:
            # identify ourselves to PX4 as an onboard companion component
            m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0); lhb = now
        if msg is not None:
            ty = msg.get_type()
            if ty == 'GPS_RAW_INT':
                g = (now, msg.lat/1e7, msg.lon/1e7, msg.time_usec/1e6)
                if g[1] != 0.0:
                    if prev_gps:
                        dt = g[3] - prev_gps[3]          # time between SAMPLES, not message arrivals
                        if dt > 0.02:
                            sp = hav(prev_gps[1], prev_gps[2], g[1], g[2]) / dt
                            if sp > JUMP_SPEED:
                                alerta('salto_GPS', sp, JUMP_SPEED, 'raw GPS teleported (%.0f m/s)' % sp)
                    prev_gps = g; last_gps = g
            elif ty == 'GLOBAL_POSITION_INT':
                g = (now, msg.lat/1e7, msg.lon/1e7, msg.alt/1000.0, msg.relative_alt/1000.0, msg.vx/100.0, msg.vy/100.0, msg.time_boot_ms/1e3)
                if prev_gp:
                    dt = g[7] - prev_gp[7]
                    if dt > 0.02:
                        sp = hav(prev_gp[1], prev_gp[2], g[1], g[2]) / dt
                        if sp > JUMP_SPEED:
                            alerta('salto_EKF', sp, JUMP_SPEED, 'EKF position teleported (%.0f m/s)' % sp)
                prev_gp = g; last_gp = g
                if last_gps:
                    sw.writerow(["%.3f" % now, "%.3f" % cur['d'], "%.4f" % cur['ih'], "%.4f" % cur['iv'],
                                 "%.7f" % last_gps[1], "%.7f" % last_gps[2], "%.7f" % g[1], "%.7f" % g[2], "%.2f" % g[4], n_alert])
            elif ty == 'ESTIMATOR_STATUS':
                cur['ih'] = msg.pos_horiz_ratio; cur['iv'] = msg.vel_ratio
                if msg.pos_horiz_ratio > INNOV_LIM:
                    alerta('innov_pos', msg.pos_horiz_ratio, INNOV_LIM, 'the EKF distrusts the GPS position')
                if msg.vel_ratio > INNOV_LIM:
                    alerta('innov_vel', msg.vel_ratio, INNOV_LIM, 'the EKF distrusts the GPS velocity')
                if msg.vel_ratio > INNOV_SOFT:
                    if soft_since is None:
                        soft_since = now
                    elif now - soft_since >= INNOV_SECS:
                        alerta('innov_sostenida', msg.vel_ratio, INNOV_SOFT, 'velocity innovation high for %.1fs -> possible GPS drift' % (now - soft_since))
                else:
                    soft_since = None

        # GPS <-> EKF distance (sudden and gradual)
        if last_gps and last_gp and abs(last_gps[0] - last_gp[0]) < 1.0:
            # GPS and EKF samples are taken at different instants: propagate the EKF position to
            # the GPS sample time using its velocity (at 7 m/s, a 0.1 s offset already looks like
            # 0.7 m of divergence). Message time stamps are used, not arrival times (jittery).
            dtc = max(-0.5, min(0.5, last_gps[3] - last_gp[7]))
            elat = last_gp[1] + last_gp[5] * dtc / 111194.93
            elon = last_gp[2] + last_gp[6] * dtc / (111194.93 * math.cos(math.radians(last_gp[1])))
            d = hav(last_gps[1], last_gps[2], elat, elon); cur['d'] = d
            if d > DIST_HARD:
                alerta('div_GPS_EKF', d, DIST_HARD, 'GPS and EKF disagree by %.1f m' % d)
            if d > DIST_WARN:
                if warn_since is None:
                    warn_since = now
                elif now - warn_since >= WARN_SECS:
                    alerta('deriva_gradual', d, DIST_WARN, 'divergence sustained for %.1fs -> possible slow spoofing' % (now - warn_since))
            else:
                warn_since = None

        # History of "trusted" positions: recorded only while every indicator is nominal
        nominal = cur['d'] < 1.0 and cur['ih'] < INNOV_SOFT and cur['iv'] < INNOV_SOFT
        if nominal and n_alert == 0:
            anom_since = None
            if last_gp and (not hist or last_gp[0] != hist[-1][0]):
                hist.append(last_gp[:4])
        elif anom_since is None:
            anom_since = now

        # ---------------- RESPONSE (state machine: idle -> hold -> return -> done) ----------------
        if a.respond and last_gp:
            if resp['state'] == 'idle' and first_alert[0] is not None:
                # trusted point = last nominal EKF position at least TRUST_BACK s before the anomaly began
                t_ref = (anom_since or now) - TRUST_BACK
                trust = None
                for h in reversed(hist):
                    if h[0] <= t_ref: trust = h; break
                if trust is None and hist: trust = hist[0]
                resp.update(state='hold', t=now, trust=trust, hold=last_gp)
                with open(ABORT_FLAG, 'w') as f: f.write("%.3f %s\n" % (now, first_alert[0][1]))
                reposition(last_gp[1], last_gp[2], last_gp[3]); resp['resend'] = now
                accion('HOLD', last_gp[1], last_gp[2], 'mission aborted; holding at the estimated position (rule: %s)' % first_alert[0][1])
                aviso('GEOSHIELD: GPS SPOOFING DETECTED - HOLD')
                accion('AVISO', last_gp[1], last_gp[2], 'STATUSTEXT sent to the ground station')
                if a.cut_gps:
                    set_int(b'EKF2_NOAID_TOUT', 10000000)     # allow 10 s of inertial-only navigation (PX4 maximum)
                    set_int(b'EKF2_GPS_CTRL', 0); time.sleep(0.05); set_int(b'EKF2_GPS_CTRL', 0)   # sent twice in case of packet loss
                    accion('CORTE_GPS', last_gp[1], last_gp[2], 'EKF2_GPS_CTRL=0: the EKF stops fusing GPS and dead-reckons')
            elif resp['state'] == 'hold':
                if resp['resend'] and now - resp['resend'] > 1.0:      # resend once, in case plan_and_fly sent a waypoint just before
                    h = resp['hold']; reposition(h[1], h[2], h[3]); resp['resend'] = 0
                if now - resp['t'] >= (HOLD_SECS_CUT if a.cut_gps else HOLD_SECS):
                    tr = resp['trust']
                    if tr is None:
                        accion('SIN_PUNTO', last_gp[1], last_gp[2], 'no trusted point available: keeping the hold'); resp['state'] = 'done'
                    else:
                        reposition(tr[1], tr[2], tr[3])
                        accion('RETORNO', tr[1], tr[2], 'returning to the last trusted point (%.0f s before the alert, %.0f m away)' % (resp['t'] - tr[0], hav(tr[1], tr[2], last_gp[1], last_gp[2])))
                        aviso('GEOSHIELD: return to trusted point')
                        resp['state'] = 'return'
            elif resp['state'] == 'return':
                tr = resp['trust']
                if hav(tr[1], tr[2], last_gp[1], last_gp[2]) < REACH:
                    accion('EN_PUNTO', last_gp[1], last_gp[2], 'trusted point reached (according to the estimate); holding')
                    with open(os.path.join(RUN, 'RESPONSE_DONE'), 'w') as f: f.write("%.3f\n" % now)
                    resp['state'] = 'done'

        if now - lflush > 1.0:
            sf.flush(); lflush = now
        if now - lp > 3:
            estado = 'CLEAN' if n_alert == 0 else ('%d ALERTS' % n_alert)
            print("  [%s] state=%-10s d_gps_ekf=%.2fm  innov_pos=%.3f  innov_vel=%.3f%s" % (datetime.now().strftime('%H:%M:%S'), estado, cur['d'], cur['ih'], cur['iv'], ("  resp=" + resp['state']) if a.respond else ""), flush=True)
            lp = now
except KeyboardInterrupt:
    print("\nstopping detector...", flush=True)
finally:
    af.close(); sf.close(); rf.close()
    print("END. Total alerts: %d  (log: %s)" % (n_alert, LOGDIR), flush=True)
