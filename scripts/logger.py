#!/usr/bin/env python3
# GeoShield - logger de telemetria GPS/EKF a CSV (pymavlink, puerto 14540).
# Uso: python3 logger.py [segundos]   (sin argumento: hasta Ctrl-C)
# Graba GPS crudo vs EKF + ratios de innovacion => base para detectar spoofing.
# NOTA: solo un proceso puede usar el 14540. Para vuelos pilotados desde QGC,
#       lanza este logger (QGC va por 14550). Para volar con script, usa fly_and_log.py.
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
mkcsv('gps_raw',    ['t', 'lat', 'lon', 'alt_m', 'eph', 'epv', 'vel_cms', 'cog', 'fix', 'sats'])
mkcsv('global_pos', ['t', 'lat', 'lon', 'alt_m', 'rel_alt_m', 'vx', 'vy', 'vz', 'hdg'])
mkcsv('local_ned',  ['t', 'x', 'y', 'z', 'vx', 'vy', 'vz'])
mkcsv('est_status', ['t', 'mag_ratio', 'vel_ratio', 'pos_h_ratio', 'pos_v_ratio', 'tas_ratio', 'hagl_ratio', 'flags'])
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
        print("  (log err %s: %s)" % (ty, e), flush=True)

m = mavutil.mavlink_connection('udpin:0.0.0.0:14540')
print("esperando heartbeat en 14540...", flush=True)
if m.wait_heartbeat(timeout=20) is None:
    print("SIN HEARTBEAT (¿esta QGC ocupando el enlace o PX4 apagado?)", flush=True); sys.exit(1)
print("enlace OK -> logs en %s" % LOGDIR, flush=True)
for mid, us in [(24, 200000), (33, 100000), (32, 100000), (230, 200000)]:
    m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, float(mid), float(us), 0, 0, 0, 0, 0); time.sleep(0.15)

print("grabando%s ... (Ctrl-C para parar)" % ((" %.0fs" % DUR) if DUR else ""), flush=True)
t0 = time.time(); lp = 0
try:
    while DUR is None or time.time() - t0 < DUR:
        msg = m.recv_match(blocking=True, timeout=1)
        if msg: logmsg(msg)
        if time.time() - lp > 5:
            print("  filas:", counts, flush=True); lp = time.time()
except KeyboardInterrupt:
    print("\nparando...", flush=True)
finally:
    for f in files.values(): f.close()
    print("FIN. Filas grabadas:", counts, flush=True)
    print("CSV en:", LOGDIR, flush=True)
