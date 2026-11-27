#!/usr/bin/env python3
"""GeoShield - PLAN the shortest route that avoids the no-fly zones and FLY it in PX4 SITL.

Shows autonomy: given any pair of points, the drone flies the shortest path around the zones
by itself. It also records telemetry to CSV (for the analysis and to calibrate the detector).

Usage:
  python3 plan_and_fly.py                      -> fly A->B->A (points from zones.py)
  python3 plan_and_fly.py Clat Clon Dlat Dlon  -> fly C->D->C
  ... --dry                                    -> only plan and print (no flight)
  ... --oneway                                 -> outbound leg only (hold at D, no return, no RTL)

The mission is flown as a sequence of MAV_CMD_DO_REPOSITION commands (one per waypoint) at
40 m above HOME and 7 m/s. If the file ~/geoshield/run/ABORT appears (created by
detector.py --respond when spoofing is detected), it stops sending waypoints and leaves
control to the detector's response.

Outputs gps_raw.csv (raw GPS), global_pos.csv (EKF estimate) and est_status.csv (EKF
innovation ratios) in GEOSHIELD_LOGDIR (or ~/geoshield/logs/<date>_planfly).
"""
import sys, os, time, csv, math, threading
from datetime import datetime
from pymavlink import mavutil
from zones import START, DEST, KEEPOUT, HOME
from planner import plan

REL_ALT = 40.0    # m above HOME
SPEED   = 7.0     # m/s

args = [a for a in sys.argv[1:] if not a.startswith('--')]
DRY  = '--dry' in sys.argv
ONEWAY = '--oneway' in sys.argv
ABORT_FLAG = os.path.expanduser('~/geoshield/run/ABORT')
C =(float(args[0]), float(args[1])) if len(args) >= 2 else START
D = (float(args[2]), float(args[3])) if len(args) >= 4 else DEST

wps, L, crossed = plan(C, D, KEEPOUT)
if wps is None:
    print("No route possible (the zones block the way).", flush=True); sys.exit(2)
def hav(a, b, c, d):
    """Haversine distance in metres."""
    R = 6371000.0; p1, p2 = math.radians(a), math.radians(c); dp = math.radians(c-a); dl = math.radians(d-b)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2; return 2*R*math.asin(math.sqrt(x))
d_direct = hav(C[0], C[1], D[0], D[1])
print("PLAN  C=%.5f,%.5f -> D=%.5f,%.5f" % (C[0], C[1], D[0], D[1]), flush=True)
print("  straight line : %.0f m  (crosses: %s)" % (d_direct, ", ".join(crossed) or "no zone"), flush=True)
print("  avoiding route: %.0f m  (%d waypoints, +%.0f m)" % (L, len(wps), L - d_direct), flush=True)
for i, (la, lo) in enumerate(wps):
    print("    wp%d  %.7f, %.7f" % (i, la, lo), flush=True)
if DRY:
    print("(dry run: not flying)", flush=True); sys.exit(0)

# ---------- FLIGHT ----------
TS, TC = 1, 1     # target system / component (PX4 autopilot)
LOGDIR = os.environ.get('GEOSHIELD_LOGDIR') or os.path.expanduser('~/geoshield/logs/' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_planfly')
os.makedirs(LOGDIR, exist_ok=True)
files, writers = {}, {}
def mkcsv(name, header):
    f = open(os.path.join(LOGDIR, name + '.csv'), 'w', newline=''); w = csv.writer(f); w.writerow(header)
    files[name] = f; writers[name] = w
mkcsv('gps_raw',    ['t','lat','lon','alt_m','eph','epv','vel_cms','cog','fix','sats'])
mkcsv('global_pos', ['t','lat','lon','alt_m','rel_alt_m','vx','vy','vz','hdg'])
mkcsv('est_status', ['t','mag_ratio','vel_ratio','pos_h_ratio','pos_v_ratio','tas_ratio','hagl_ratio','flags'])
_last_flush = [0.0]
def logmsg(msg):
    """Append one MAVLink message to its CSV."""
    t = time.time(); ty = msg.get_type()
    if t - _last_flush[0] > 1.0:          # incremental flush: if the flight is interrupted the CSV is already on disk
        for f in files.values(): f.flush()
        _last_flush[0] = t
    try:
        if ty == 'GPS_RAW_INT':
            writers['gps_raw'].writerow([t, msg.lat/1e7, msg.lon/1e7, msg.alt/1000.0, msg.eph, msg.epv, msg.vel, msg.cog, msg.fix_type, msg.satellites_visible])
        elif ty == 'GLOBAL_POSITION_INT':
            writers['global_pos'].writerow([t, msg.lat/1e7, msg.lon/1e7, msg.alt/1000.0, msg.relative_alt/1000.0, msg.vx, msg.vy, msg.vz, msg.hdg])
        elif ty == 'ESTIMATOR_STATUS':
            writers['est_status'].writerow([t, msg.mag_ratio, msg.vel_ratio, msg.pos_horiz_ratio, msg.pos_vert_ratio, msg.tas_ratio, msg.hagl_ratio, msg.flags])
    except Exception:
        pass

m = mavutil.mavlink_connection('udpin:0.0.0.0:14540')
print("waiting for heartbeat on 14540...", flush=True)
if m.wait_heartbeat(timeout=20) is None:
    print("NO HEARTBEAT", flush=True); sys.exit(1)
print("link OK -> logs in %s" % LOGDIR, flush=True)
stop = False
def beat():
    """GCS heartbeat thread: PX4 refuses to arm without a ground station, so this script acts as one."""
    while not stop:
        m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0); time.sleep(1.0)
threading.Thread(target=beat, daemon=True).start()
def cmd_long(cmd, *p):
    a = list(p) + [0.0]*(7-len(p)); m.mav.command_long_send(TS, TC, cmd, 0, *a)
def ack(cmd, s=4):
    """Wait up to s seconds for the COMMAND_ACK of `cmd` and return its result code."""
    t = time.time()
    while time.time()-t < s:
        a = m.recv_match(type='COMMAND_ACK', blocking=True, timeout=2)
        if a and a.command == cmd:
            print("  ACK cmd=%d result=%d" % (a.command, a.result), flush=True); return a.result
    return None
# faster telemetry streams: GPS_RAW_INT 5 Hz, GLOBAL_POSITION_INT 10 Hz, ESTIMATOR_STATUS 5 Hz
for mid, us in [(24,200000),(33,100000),(230,200000)]:
    cmd_long(mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, float(mid), float(us)); time.sleep(0.12)

cur_amsl = HOME[2] if len(HOME) > 2 else 12.0
t0 = time.time()
while time.time()-t0 < 6:
    g = m.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2)
    if g: cur_amsl = g.alt/1000.0; logmsg(g); break
to_amsl = cur_amsl + REL_ALT        # flight altitude above mean sea level

aborted = [False]
def fly(lat, lon, tag, timeout=None, reach=18.0):
    """Send one reposition command and wait until the waypoint is within `reach` metres.
    timeout=None -> computed from the leg length: twice the nominal flight time plus 60 s."""
    m.mav.command_int_send(TS, TC, mavutil.mavlink.MAV_FRAME_GLOBAL_INT,
                           mavutil.mavlink.MAV_CMD_DO_REPOSITION, 0, 0,
                           SPEED, 1.0, 0.0, float('nan'), int(lat*1e7), int(lon*1e7), to_amsl)
    ack(192)
    t0 = time.time(); lp = 0
    while timeout is None or time.time()-t0 < timeout:
        if os.path.exists(ABORT_FLAG):
            aborted[0] = True
            print("[%s] ABORT: the detector has taken control, no more waypoints" % tag, flush=True); return False
        msg = m.recv_match(blocking=True, timeout=1)
        if msg is None:
            if timeout is None and time.time()-t0 > 30:
                print("[%s] WARNING: no telemetry for 30 s" % tag, flush=True); return False
            continue
        logmsg(msg)
        if msg.get_type() == 'GLOBAL_POSITION_INT':
            d = hav(lat, lon, msg.lat/1e7, msg.lon/1e7)
            if timeout is None:
                timeout = (time.time()-t0) + 2.0 * d / SPEED + 60.0
            if time.time()-lp > 2:
                print("[%s] rel_alt=%.1f dist_wp=%.0f" % (tag, msg.relative_alt/1000.0, d), flush=True); lp = time.time()
            if d < reach:
                print("[%s] waypoint reached" % tag, flush=True); return True
    print("[%s] WARNING: waypoint NOT reached (timeout), moving on to the next one" % tag, flush=True)
    return False

print("ARM + TAKE OFF to %.0f m..." % REL_ALT, flush=True)
cmd_long(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1); ack(400); time.sleep(1)
cmd_long(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, float('nan'), float('nan'), float('nan'), to_amsl); ack(22)
t0 = time.time()
while time.time()-t0 < 18:
    msg = m.recv_match(blocking=True, timeout=1)
    if msg is None: continue
    logmsg(msg)
    if msg.get_type() == 'GLOBAL_POSITION_INT' and msg.relative_alt/1000.0 > REL_ALT-3:
        print("[climb] %.1f m" % (msg.relative_alt/1000.0), flush=True); break

def finish(texto):
    global stop
    stop = True
    for f in files.values(): f.close()
    print("%s CSV in %s" % (texto, LOGDIR), flush=True)
    sys.exit(0)

for i, (wlat, wlon) in enumerate(wps[1:], 1):   # wps[0] = origin (where we already are)
    fly(wlat, wlon, "wp%d" % i)
    if aborted[0]: finish("END-ABORT (outbound leg interrupted by the detector).")
if ONEWAY:
    finish("END-OUTBOUND (--oneway: holding at the destination, no return).")

# ---------- RETURN: the same optimal route, reversed ----------
# The outbound waypoints are reused backwards (optimal and identical to the way out);
# a straight RTL would fly back across the zones, so it is not used for the return leg.
rwps = list(reversed(wps))
print("RETURN: same optimal route reversed, %.0f m, %d waypoints" % (L, len(rwps)), flush=True)
for i, (wlat, wlon) in enumerate(rwps[1:], 1):
    fly(wlat, wlon, "ret%d" % i)
    if aborted[0]: finish("END-ABORT (return leg interrupted by the detector).")

print("final RTL: landing at home...", flush=True)
cmd_long(mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH); ack(20)
t0 = time.time()
while time.time()-t0 < 90:
    msg = m.recv_match(blocking=True, timeout=1)
    if msg is None: continue
    logmsg(msg)
    if msg.get_type() == 'GLOBAL_POSITION_INT' and msg.relative_alt/1000.0 < 1.0:
        print("[rtl] on the ground", flush=True); break
stop = True
for f in files.values(): f.close()
print("END. Route flown (%d waypoints). CSV in %s" % (len(wps)-1, LOGDIR), flush=True)
