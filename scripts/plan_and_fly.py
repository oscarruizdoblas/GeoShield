#!/usr/bin/env python3
# GeoShield - PLANIFICA la ruta optima C->D que evita las zonas prohibidas y la VUELA.
# Demuestra autonomia: dado cualquier par de puntos, el dron va solo por el camino mas corto
# esquivando las zonas. Graba la telemetria a CSV (para el analisis/detector).
#
# Uso:
#   python3 plan_and_fly.py                      -> vuela A->B (de zones.py)
#   python3 plan_and_fly.py Clat Clon Dlat Dlon  -> vuela C->D
#   ... --dry                                    -> solo planifica e imprime (no vuela)
import sys, os, time, csv, math, threading
from datetime import datetime
from pymavlink import mavutil
sys.path.insert(0, '/home/oruiz/geoshield')
from zones import START, DEST, KEEPOUT, HOME
from planner import plan

REL_ALT = 40.0
SPEED   = 7.0

args = [a for a in sys.argv[1:] if not a.startswith('--')]
DRY  = '--dry' in sys.argv
C = (float(args[0]), float(args[1])) if len(args) >= 2 else START
D = (float(args[2]), float(args[3])) if len(args) >= 4 else DEST

wps, L, crossed = plan(C, D, KEEPOUT)
if wps is None:
    print("No hay ruta posible (las zonas bloquean el paso).", flush=True); sys.exit(2)
d_direct = 0.0
la1, lo1 = C
import math as _m
def hav(a,b,c,d):
    R=6371000.0;p1,p2=_m.radians(a),_m.radians(c);dp=_m.radians(c-a);dl=_m.radians(d-b)
    x=_m.sin(dp/2)**2+_m.cos(p1)*_m.cos(p2)*_m.sin(dl/2)**2;return 2*R*_m.asin(_m.sqrt(x))
d_direct = hav(C[0], C[1], D[0], D[1])
print("PLAN  C=%.5f,%.5f -> D=%.5f,%.5f" % (C[0], C[1], D[0], D[1]), flush=True)
print("  recta directa : %.0f m  (cruza: %s)" % (d_direct, ", ".join(crossed) or "ninguna zona"), flush=True)
print("  ruta esquivando: %.0f m  (%d waypoints, +%.0f m)" % (L, len(wps), L - d_direct), flush=True)
for i, (la, lo) in enumerate(wps):
    print("    wp%d  %.7f, %.7f" % (i, la, lo), flush=True)
if DRY:
    print("(dry-run: no se vuela)", flush=True); sys.exit(0)

# ---------- VUELO ----------
TS, TC = 1, 1
LOGDIR = os.path.expanduser('~/geoshield/logs/' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_planfly')
os.makedirs(LOGDIR, exist_ok=True)
files, writers = {}, {}
def mkcsv(name, header):
    f = open(os.path.join(LOGDIR, name + '.csv'), 'w', newline=''); w = csv.writer(f); w.writerow(header)
    files[name] = f; writers[name] = w
mkcsv('gps_raw',    ['t','lat','lon','alt_m','eph','epv','vel_cms','cog','fix','sats'])
mkcsv('global_pos', ['t','lat','lon','alt_m','rel_alt_m','vx','vy','vz','hdg'])
mkcsv('est_status', ['t','mag_ratio','vel_ratio','pos_h_ratio','pos_v_ratio','tas_ratio','hagl_ratio','flags'])
def logmsg(msg):
    t = time.time(); ty = msg.get_type()
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
print("esperando heartbeat en 14540...", flush=True)
if m.wait_heartbeat(timeout=20) is None:
    print("SIN HEARTBEAT", flush=True); sys.exit(1)
print("enlace OK -> logs en %s" % LOGDIR, flush=True)
stop = False
def beat():
    while not stop:
        m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0); time.sleep(1.0)
threading.Thread(target=beat, daemon=True).start()
def cmd_long(cmd, *p):
    a = list(p) + [0.0]*(7-len(p)); m.mav.command_long_send(TS, TC, cmd, 0, *a)
def ack(cmd, s=4):
    t = time.time()
    while time.time()-t < s:
        a = m.recv_match(type='COMMAND_ACK', blocking=True, timeout=2)
        if a and a.command == cmd:
            print("  ACK cmd=%d result=%d" % (a.command, a.result), flush=True); return a.result
    return None
for mid, us in [(24,200000),(33,100000),(230,200000)]:
    cmd_long(mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, float(mid), float(us)); time.sleep(0.12)

cur_amsl = HOME[2] if len(HOME) > 2 else 12.0
t0 = time.time()
while time.time()-t0 < 6:
    g = m.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2)
    if g: cur_amsl = g.alt/1000.0; logmsg(g); break
to_amsl = cur_amsl + REL_ALT

def fly(lat, lon, tag, timeout=120, reach=18.0):
    m.mav.command_int_send(TS, TC, mavutil.mavlink.MAV_FRAME_GLOBAL_INT,
                           mavutil.mavlink.MAV_CMD_DO_REPOSITION, 0, 0,
                           SPEED, 1.0, 0.0, float('nan'), int(lat*1e7), int(lon*1e7), to_amsl)
    ack(192)
    t0 = time.time(); lp = 0
    while time.time()-t0 < timeout:
        msg = m.recv_match(blocking=True, timeout=1)
        if msg is None: continue
        logmsg(msg)
        if msg.get_type() == 'GLOBAL_POSITION_INT':
            d = hav(lat, lon, msg.lat/1e7, msg.lon/1e7)
            if time.time()-lp > 2:
                print("[%s] rel_alt=%.1f dist_wp=%.0f" % (tag, msg.relative_alt/1000.0, d), flush=True); lp = time.time()
            if d < reach:
                print("[%s] waypoint alcanzado" % tag, flush=True); return

print("ARMAR + DESPEGAR a %.0f m..." % REL_ALT, flush=True)
cmd_long(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1); ack(400); time.sleep(1)
cmd_long(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, float('nan'), float('nan'), float('nan'), to_amsl); ack(22)
t0 = time.time()
while time.time()-t0 < 18:
    msg = m.recv_match(blocking=True, timeout=1)
    if msg is None: continue
    logmsg(msg)
    if msg.get_type() == 'GLOBAL_POSITION_INT' and msg.relative_alt/1000.0 > REL_ALT-3:
        print("[subida] %.1f m" % (msg.relative_alt/1000.0), flush=True); break

for i, (wlat, wlon) in enumerate(wps[1:], 1):   # wps[0] = origen (donde ya estamos)
    fly(wlat, wlon, "wp%d" % i)

print("RTL ...", flush=True)
cmd_long(mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH); ack(20)
t0 = time.time()
while time.time()-t0 < 60:
    msg = m.recv_match(blocking=True, timeout=1)
    if msg is None: continue
    logmsg(msg)
    if msg.get_type() == 'GLOBAL_POSITION_INT' and msg.relative_alt/1000.0 < 1.0:
        print("[rtl] en el suelo", flush=True); break
stop = True
for f in files.values(): f.close()
print("FIN. Ruta volada (%d waypoints). CSV en %s" % (len(wps)-1, LOGDIR), flush=True)
