#!/usr/bin/env python3
"""GeoShield - bring the drone back to A (HOME in zones.py) from wherever it is, and land (port 14540).

  - In flight: fly back along the SAME route used on the way out (reversed), joining it at the
    most convenient waypoint; if no waypoint can be reached without crossing a zone, plan a new
    route; if that also fails, fly straight home.
  - On the ground far from A (e.g. after PX4's emergency landing without GPS): arm, take off
    and come back.
  - --gps-on: first re-enable GPS fusion (EKF2_GPS_CTRL=7), in case the response cut it.
Used by run_attack_test.sh at the end of every test, once the attack has been stopped.
"""
import sys, os, time, math, struct
from pymavlink import mavutil
from zones import HOME, KEEPOUT, START, DEST
from planner import plan

REL_ALT, SPEED = 40.0, 7.0     # flight altitude above HOME (m) and cruise speed (m/s)
def hav(a, b, c, d):
    """Haversine distance in metres."""
    R = 6371000.0; p1, p2 = math.radians(a), math.radians(c)
    x = math.sin(math.radians(c-a)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(d-b)/2)**2
    return 2*R*math.asin(math.sqrt(x))

m = mavutil.mavlink_connection('udpin:0.0.0.0:14540')
if m.wait_heartbeat(timeout=20) is None:
    print("NO HEARTBEAT", flush=True); sys.exit(1)
_lb = [0.0]
def beat():
    """Send a GCS heartbeat at most once per second (PX4 needs a GCS link to accept commands)."""
    if time.time() - _lb[0] > 1.0:
        m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0); _lb[0] = time.time()
def set_int(name, val):
    """Set an INT32 PX4 parameter (PX4 copies param_value byte by byte: pack the integer's bytes in the float)."""
    m.mav.param_set_send(1, 1, name, struct.unpack('<f', struct.pack('<i', int(val)))[0], mavutil.mavlink.MAV_PARAM_TYPE_INT32)
def cmd(c, *p):
    a = list(p) + [0.0] * (7 - len(p)); m.mav.command_long_send(1, 1, c, 0, *a)
def spin(secs):
    """Keep reading messages (and sending heartbeats) for `secs` seconds."""
    t0 = time.time()
    while time.time() - t0 < secs:
        m.recv_match(blocking=True, timeout=1); beat()
def pos(timeout=10):
    """Latest GLOBAL_POSITION_INT (EKF estimate) or None."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        g = m.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2); beat()
        if g: return g
    return None
def armed(timeout=5):
    """True/False from the autopilot heartbeat, None if no heartbeat arrives."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        hb = m.recv_match(type='HEARTBEAT', blocking=True, timeout=2); beat()
        if hb and hb.get_srcSystem() == 1 and hb.get_srcComponent() == 1:
            return bool(hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
    return None

if '--gps-on' in sys.argv:
    # undo the GPS cut of the response (7 = default PX4 GPS fusion: position + velocity + altitude)
    set_int(b'EKF2_GPS_CTRL', 7); time.sleep(0.3); set_int(b'EKF2_GPS_CTRL', 7); time.sleep(0.3); set_int(b'EKF2_NOAID_TOUT', 5000000)
    print("EKF2_GPS_CTRL=7 (GPS fusion restored); 25 s for the EKF to converge", flush=True)
    spin(25)

g = pos()
if g is None:
    print("no position", flush=True); sys.exit(1)
lat, lon = g.lat/1e7, g.lon/1e7
dh = hav(lat, lon, HOME[0], HOME[1]); rel = g.relative_alt/1000.0
print("estimated position: %.6f, %.6f  rel_alt=%.1f  (%.0f m from A)" % (lat, lon, rel, dh), flush=True)

if armed() is False:
    if dh < 15:
        print("ON THE GROUND and disarmed, %.1f m from A" % dh, flush=True); sys.exit(0)
    print("on the ground far from A: arming and taking off to come back", flush=True)
    to = g.alt/1000.0 + REL_ALT
    for intento in range(6):          # PX4 may refuse to arm while the EKF re-converges: retry
        cmd(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1); spin(1.5)
        if armed(): break
        spin(5)
    cmd(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, float('nan'), float('nan'), float('nan'), to)
    t0 = time.time()
    while time.time() - t0 < 30:
        gg = pos(3)
        if gg and gg.relative_alt/1000.0 > REL_ALT - 3: break
    g = pos(); lat, lon = g.lat/1e7, g.lon/1e7

alt = g.alt/1000.0

def ruta_de_vuelta(lat, lon):
    """Return route ("ruta de vuelta"): the SAME planned A->B route flown backwards, as in plan_and_fly.py.
    It is joined at the waypoint that gives the shortest total path to A without crossing any
    zone (with a clearance similar to the planner's). Returns (waypoints, length) or None."""
    ida, _, _ = plan(START, DEST, KEEPOUT)            # outbound route A ... B
    if not ida: return None
    vuelta = list(reversed(ida))                       # B ... A
    M = 111194.93; mlon = M * math.cos(math.radians(HOME[0]))
    def en(p): return ((p[1] - HOME[1]) * mlon, (p[0] - HOME[0]) * M)
    def libre(p, q, margen=60.0):
        """True if segment p-q stays at least `margen` m outside every zone ("free")."""
        (px, py), (qx, qy) = en(p), en(q); dx, dy = qx - px, qy - py; L2 = dx*dx + dy*dy
        for z in KEEPOUT:
            cx, cy = en((z['lat'], z['lon']))
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((cx-px)*dx + (cy-py)*dy) / L2))
            if math.hypot(cx - (px + t*dx), cy - (py + t*dy)) < z['r'] + margen: return False
        return True
    resto = [0.0] * len(vuelta)                       # metres from vuelta[j] to A along the route
    for j in range(len(vuelta) - 2, -1, -1):
        resto[j] = resto[j+1] + hav(*vuelta[j], *vuelta[j+1])
    mejor = None                                      # best (cost, index) so far
    for j in range(len(vuelta)):
        if libre((lat, lon), vuelta[j]):
            c = hav(lat, lon, *vuelta[j]) + resto[j]
            if mejor is None or c < mejor[0]: mejor = (c, j)
    if mejor is None: return None
    return [(lat, lon)] + vuelta[mejor[1]:], mejor[0]

wps = None
if not any(hav(lat, lon, z['lat'], z['lon']) < z['r'] for z in KEEPOUT):
    rv = ruta_de_vuelta(lat, lon)
    if rv is not None:
        wps, L = rv
    else:
        wps, L, _ = plan((lat, lon), (HOME[0], HOME[1]), KEEPOUT)
        if wps is not None and not math.isfinite(L): wps = None
if wps is None:
    print("no route avoiding the zones (or already inside one): flying straight to A", flush=True)
    wps = [(lat, lon), (HOME[0], HOME[1])]
else:
    print("return route: %.0f m, %d waypoints" % (L, len(wps)), flush=True)
for i, (wlat, wlon) in enumerate(wps[1:], 1):
    m.mav.command_int_send(1, 1, mavutil.mavlink.MAV_FRAME_GLOBAL_INT, mavutil.mavlink.MAV_CMD_DO_REPOSITION, 0, 0,
                           SPEED, 1.0, 0.0, float('nan'), int(wlat*1e7), int(wlon*1e7), alt)
    t0 = time.time(); d0 = None
    while True:
        gg = pos(3)
        if gg is None: continue
        d = hav(wlat, wlon, gg.lat/1e7, gg.lon/1e7)
        if d0 is None: d0 = d
        # intermediate waypoints: 18 m acceptance radius; last one (A): 3 m
        if d < (18 if i < len(wps) - 1 else 3): print("  return wp%d reached" % i, flush=True); break
        if time.time() - t0 > 2.0 * d0 / SPEED + 60: print("  return wp%d NOT reached (timeout)" % i, flush=True); break
cmd(mavutil.mavlink.MAV_CMD_NAV_LAND, 0, 0, 0, float('nan'), float('nan'), float('nan'), 0)
print("LAND sent over A; waiting for touchdown...", flush=True)
t0 = time.time()
while time.time() - t0 < 300:
    if armed(3) is False:
        gg = pos(5)
        print("ON THE GROUND and disarmed, %.1f m from A" % (hav(gg.lat/1e7, gg.lon/1e7, HOME[0], HOME[1]) if gg else -1), flush=True); sys.exit(0)
print("WARNING: landing not confirmed within 300 s", flush=True); sys.exit(2)
