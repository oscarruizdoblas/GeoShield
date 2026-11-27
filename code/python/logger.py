#!/usr/bin/env python3
"""GeoShield - GPS/EKF telemetry logger to CSV (pymavlink, port 14540).

Usage: python3 logger.py [seconds]   (no argument: until Ctrl-C)

Records the raw GPS fix next to the EKF estimate and the EKF innovation ratios: the baseline
data used by analyze.py to characterise a clean flight and calibrate the detector thresholds.
Note: only one process can own port 14540. Use this logger for flights flown from
QGroundControl (which uses 14550); scripted flights (plan_and_fly.py) log by themselves.
"""
import sys, os, time, csv, math
from datetime import datetime
from pymavlink import mavutil

DUR = float(sys.argv[1]) if len(sys.argv) > 1 else None

LOGDIR = os.path.expanduser('~/geoshield/logs/' + datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(LOGDIR, exist_ok=True)
files, writers = {}, {}
def mkcsv(name, header):
    f = open(os.path.join(LOGDIR, name + '.csv'), 'w', newline='')
    w = csv.writer(f); w.writerow(header); files[name] = f; writers[name] = w
mkcsv('gps_raw',    ['t', 'lat', 'lon', 'alt_m', 'eph', 'epv', 'vel_cms', 'cog', 'fix', 'sats'])   # GPS_RAW_INT
mkcsv('global_pos', ['t', 'lat', 'lon', 'alt_m', 'rel_alt_m', 'vx', 'vy', 'vz', 'hdg'])           # EKF global position
mkcsv('local_ned',  ['t', 'x', 'y', 'z', 'vx', 'vy', 'vz'])                                       # EKF local position
mkcsv('est_status', ['t', 'mag_ratio', 'vel_ratio', 'pos_h_ratio', 'pos_v_ratio', 'tas_ratio', 'hagl_ratio', 'flags'])  # innovation ratios
counts = {k: 0 for k in writers}

def logmsg(msg):
    t = time.time(); ty = msg.get_type()
    try:
        if ty == 'GPS_RAW_INT':
            writers['gps_raw'].writerow([t, msg.lat/1e7, msg.lon/1e7, msg.alt/1000.0, msg.eph, msg.epv, msg.vel, msg.cog, msg.fix_type, msg.satellites_visible]); counts['gps_raw'] += 1
        elif ty == 'GLOBAL_POSITION_INT':
            writers['global_pos'].writerow([t, msg.lat/1e7, msg.lon/1e7, msg.alt/1000.0, msg.relative_alt/1000.0, msg.vx, msg.vy, msg.vz, msg.hdg]); counts['global_pos'] += 1
        elif ty == 'LOCAL_POSITION_NED':
            writers['local_ned'].writerow([t, msg.x, msg.y, msg.z, msg.vx, msg.vy, msg.vz]); counts['local_ned'] += 1
        elif ty == 'ESTIMATOR_STATUS':
            writers['est_status'].writerow([t, msg.mag_ratio, msg.vel_ratio, msg.pos_horiz_ratio, msg.pos_vert_ratio, msg.tas_ratio, msg.hagl_ratio, msg.flags]); counts['est_status'] += 1
    except Exception as e:
        print("  (log error %s: %s)" % (ty, e), flush=True)

m = mavutil.mavlink_connection('udpin:0.0.0.0:14540')
print("waiting for heartbeat on 14540...", flush=True)
if m.wait_heartbeat(timeout=20) is None:
    print("NO HEARTBEAT (is another program using the link, or is PX4 off?)", flush=True); sys.exit(1)
print("link OK -> logs in %s" % LOGDIR, flush=True)
# request faster streams: GPS_RAW_INT 5 Hz, GLOBAL_POSITION_INT 10 Hz, LOCAL_POSITION_NED 10 Hz, ESTIMATOR_STATUS 5 Hz
for mid, us in [(24, 200000), (33, 100000), (32, 100000), (230, 200000)]:
    m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, float(mid), float(us), 0, 0, 0, 0, 0); time.sleep(0.15)

print("recording%s ... (Ctrl-C to stop)" % ((" %.0fs" % DUR) if DUR else ""), flush=True)
t0 = time.time(); lp = 0
try:
    while DUR is None or time.time() - t0 < DUR:
        msg = m.recv_match(blocking=True, timeout=1)
        if msg: logmsg(msg)
        if time.time() - lp > 5:
            print("  rows:", counts, flush=True); lp = time.time()
except KeyboardInterrupt:
    print("\nstopping...", flush=True)
finally:
    for f in files.values(): f.close()
    print("END. Rows recorded:", counts, flush=True)
    print("CSV in:", LOGDIR, flush=True)
