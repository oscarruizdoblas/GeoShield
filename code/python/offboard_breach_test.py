#!/usr/bin/env python3
"""GeoShield - TEST of the PX4 geofence against OFFBOARD velocity setpoints (simulation only).

Question: with the geofence loaded and GF_ACTION=3 (RTL), does PX4 stop a stream of OFFBOARD
velocity commands from pushing the drone into Palazzo Bo? (i.e. does the fence protect against
malicious *commands*, as opposed to a malicious *GPS*?)

Procedure: take off, fly to a point 110 m outside the zone, switch to OFFBOARD and push towards
the zone centre at 5 m/s for 45 s. Prints the flight-mode changes, PX4 messages and the maximum
penetration. CSV (offboard.csv) in the log folder.
Result in our runs: PX4 brakes ~8 m before the zone edge, so the fence does stop commands;
the GPS attack defeats it because the fence is evaluated on the (forged) estimate.
"""
import sys, os, time, math, csv, threading
from datetime import datetime
from pymavlink import mavutil
from zones import HOME, KEEPOUT

BO = KEEPOUT[0]          # Palazzo Bo
MLAT = 111194.93; MLON = MLAT * math.cos(math.radians(HOME[0]))
def hav(a, b, c, d):
    """Haversine distance in metres."""
    R = 6371000.0; p1, p2 = math.radians(a), math.radians(c)
    x = math.sin(math.radians(c-a)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(d-b)/2)**2
    return 2*R*math.asin(math.sqrt(x))
# unit vector (East, North) from HOME towards the centre of Palazzo Bo
dE = (BO['lon'] - HOME[1]) * MLON; dN = (BO['lat'] - HOME[0]) * MLAT
D = math.hypot(dE, dN); uE, uN = dE / D, dN / D
START_D = BO['r'] + 110.0                                  # starting point: 110 m outside the zone
P0 = (BO['lat'] - uN * START_D / MLAT, BO['lon'] - uE * START_D / MLON)
VEL = 5.0                                                  # push speed (m/s)

LOGDIR = os.environ.get('GEOSHIELD_LOGDIR') or os.path.expanduser('~/geoshield/logs/' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_offboard_geofence')
os.makedirs(LOGDIR, exist_ok=True)
f = open(os.path.join(LOGDIR, 'offboard.csv'), 'w', newline=''); w = csv.writer(f)
w.writerow(['t', 'lat', 'lon', 'rel_alt', 'dist_bo_centre', 'main_mode', 'sub_mode', 'phase'])

m = mavutil.mavlink_connection('udpin:0.0.0.0:14540')
if m.wait_heartbeat(timeout=20) is None:
    print("NO HEARTBEAT", flush=True); sys.exit(1)
state = {'stop': False, 'offboard': False}
def beat():
    """Heartbeat thread; in OFFBOARD it also streams the velocity setpoint at 10 Hz
    (PX4 leaves OFFBOARD if setpoints stop arriving)."""
    while not state['stop']:
        m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        if state['offboard']:
            for _ in range(5):
                # type_mask 3527 = use only the velocity fields (vx = North, vy = East in NED)
                m.mav.set_position_target_local_ned_send(0, 1, 1, mavutil.mavlink.MAV_FRAME_LOCAL_NED, 3527,
                                                         0, 0, 0, uN * VEL, uE * VEL, 0, 0, 0, 0, 0, 0)
                time.sleep(0.1)
        else:
            time.sleep(0.5)
threading.Thread(target=beat, daemon=True).start()
def cmd(c, *p):
    a = list(p) + [0.0] * (7 - len(p)); m.mav.command_long_send(1, 1, c, 0, *a)

mode = {'main': -1, 'sub': -1}
res = {'dmin': 1e9, 'rtl_at': None}
def pump(secs, fase, until=None):
    """Process telemetry for `secs` seconds in phase `fase`; stop early when until(msg, d) is true."""
    t0 = time.time(); lp = 0
    while time.time() - t0 < secs:
        msg = m.recv_match(type=['GLOBAL_POSITION_INT', 'STATUSTEXT', 'HEARTBEAT'], blocking=True, timeout=1)
        if msg is None: continue
        ty = msg.get_type()
        if ty == 'STATUSTEXT':
            print("   PX4: %s" % msg.text, flush=True)
        elif ty == 'HEARTBEAT' and msg.get_srcSystem() == 1 and msg.get_srcComponent() == 1:
            # PX4 encodes its flight mode in custom_mode: main mode in byte 2, sub mode in byte 3
            mm, ss = (msg.custom_mode >> 16) & 0xFF, (msg.custom_mode >> 24) & 0xFF
            if (mm, ss) != (mode['main'], mode['sub']):
                print("   mode -> main=%d sub=%d %s" % (mm, ss, {(6, 0): '(OFFBOARD)', (4, 5): '(AUTO.RTL)', (4, 3): '(AUTO.LOITER)', (4, 2): '(AUTO.TAKEOFF)'}.get((mm, ss), '')), flush=True)
                mode['main'], mode['sub'] = mm, ss
        elif ty == 'GLOBAL_POSITION_INT':
            la, lo = msg.lat/1e7, msg.lon/1e7
            d = hav(la, lo, BO['lat'], BO['lon'])
            w.writerow(["%.3f" % time.time(), "%.7f" % la, "%.7f" % lo, "%.2f" % (msg.relative_alt/1000.0), "%.1f" % d, mode['main'], mode['sub'], fase])
            if fase == 'offboard':
                res['dmin'] = min(res['dmin'], d)
                if res['rtl_at'] is None and (mode['main'], mode['sub']) == (4, 5): res['rtl_at'] = d
            if time.time() - lp > 3:
                print("[%s] rel_alt=%.1f  dist_Bo_centre=%.0f m (%s)" % (fase, msg.relative_alt/1000.0, d, 'INSIDE' if d < BO['r'] else 'outside'), flush=True); lp = time.time()
            if until and until(msg, d): return True
    return False

g = None
while g is None: g = m.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=5)
to = g.alt/1000.0 + 40.0
print("ARM + TAKE OFF", flush=True)
cmd(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1); time.sleep(1.5)
cmd(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, float('nan'), float('nan'), float('nan'), to)
pump(25, 'climb', lambda msg, d: msg.relative_alt/1000.0 > 37)
print("flying to the start point, %.0f m from the centre of Palazzo Bo (110 m outside the zone)" % START_D, flush=True)
m.mav.command_int_send(1, 1, mavutil.mavlink.MAV_FRAME_GLOBAL_INT, mavutil.mavlink.MAV_CMD_DO_REPOSITION, 0, 0,
                       7.0, 1.0, 0.0, float('nan'), int(P0[0]*1e7), int(P0[1]*1e7), to)
pump(200, 'approach', lambda msg, d: hav(msg.lat/1e7, msg.lon/1e7, P0[0], P0[1]) < 10)
print(">>> OFFBOARD: %.0f m/s velocity setpoints towards the zone centre" % VEL, flush=True)
state['offboard'] = True; time.sleep(1.5)      # PX4 needs setpoints streaming before it accepts OFFBOARD
cmd(mavutil.mavlink.MAV_CMD_DO_SET_MODE, 1, 6, 0)   # custom main mode 6 = OFFBOARD
pump(45, 'offboard')
state['offboard'] = False
f.flush()
pen = BO['r'] - res['dmin']
print("RESULT: minimum distance to the centre = %.0f m -> %s" % (res['dmin'], ("ENTERED the zone by %.0f m" % pen) if pen > 0 else "did NOT enter"), flush=True)
print("RESULT: geofence RTL %s" % (("triggered %.0f m from the centre" % res['rtl_at']) if res['rtl_at'] else "NOT triggered during the OFFBOARD push"), flush=True)
state['stop'] = True; f.close()
print("END-OFFBOARD  CSV in %s" % LOGDIR, flush=True)
