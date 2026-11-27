#!/usr/bin/python3
"""GeoShield - show the drone's REAL position (from Gazebo) in QGroundControl as a second vehicle.

QGC can only draw what the drone reports, and under GPS spoofing the drone reports its FALSE
position: in QGC the route looks correct even while the real drone is inside the no-fly zone.
This script reads the true GPS of the Gazebo sensor (/geoshield/navsat_true, before the spoofing
relay) and sends it to QGC as vehicle 2, so both trajectories appear on the same map:
    vehicle 1 = what the drone believes (PX4)      vehicle 2 = where it really is (Gazebo)
It is a simulator visualisation tool only: a real drone does not have this information.

    /usr/bin/python3 real_pos_qgc.py        (needs the SITL started with run_padova_spoof.sh)
Uses the system Python (gz-transport); pymavlink is taken from the conda environment if missing.
"""
import os, sys, time, math, threading, glob
try:
    from pymavlink import mavutil
except ImportError:
    for p in [os.path.expanduser('~/geoshield/pylib')] + glob.glob(os.path.expanduser('~/yes/lib/python3*/site-packages')):
        sys.path.append(p)
    from pymavlink import mavutil
from gz.transport13 import Node
from gz.msgs10.navsat_pb2 import NavSat

HOME_ALT = float(os.environ.get('PX4_HOME_ALT', '12'))
SYSID = 2          # MAVLink system id of the fake 'real position' vehicle
m = mavutil.mavlink_connection('udpout:127.0.0.1:14550', source_system=SYSID, source_component=1)
st = {'msg': None}
lock = threading.Lock()

def cb(msg):
    with lock: st['msg'] = msg

node = Node()
if not node.subscribe(NavSat, '/geoshield/navsat_true', cb):
    sys.exit("cannot subscribe to /geoshield/navsat_true (start the SITL with run_padova_spoof.sh)")
print("[real_pos_qgc] REAL Gazebo position -> QGC as vehicle %d" % SYSID, flush=True)

t0 = time.time(); last_hb = 0.0; said = False
while True:
    now = time.time()
    if now - last_hb > 1.0:
        m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_QUADROTOR, mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
                             mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, 0, mavutil.mavlink.MAV_STATE_ACTIVE)
        last_hb = now
        if not said and now - t0 > 3:
            m.mav.statustext_send(mavutil.mavlink.MAV_SEVERITY_NOTICE, b'GEOSHIELD: vehicle 2 = REAL position (Gazebo)'); said = True
    # QGC asks every new vehicle for its parameters and mission: answer that there is nothing
    while True:
        r = m.recv_match(blocking=False)
        if r is None: break
        ty = r.get_type()
        if ty == 'PARAM_REQUEST_LIST':
            m.mav.param_value_send(b'GEOSHIELD_REAL', 1.0, mavutil.mavlink.MAV_PARAM_TYPE_INT32, 1, 0)
        elif ty == 'MISSION_REQUEST_LIST':
            m.mav.mission_count_send(r.get_srcSystem(), r.get_srcComponent(), 0, getattr(r, 'mission_type', 0))
    with lock: g = st['msg']
    if g is not None:
        # report the true fix as position, GPS and attitude (heading from the velocity vector)
        ve, vn, vu = g.velocity_east, g.velocity_north, g.velocity_up
        hdg = (math.degrees(math.atan2(ve, vn)) % 360.0) if math.hypot(ve, vn) > 0.5 else 0.0
        tb = int((now - t0) * 1000)
        m.mav.global_position_int_send(tb, int(g.latitude_deg * 1e7), int(g.longitude_deg * 1e7), int(g.altitude * 1000),
                                       int((g.altitude - HOME_ALT) * 1000), int(vn * 100), int(ve * 100), int(-vu * 100), int(hdg * 100))
        m.mav.gps_raw_int_send(tb * 1000, 3, int(g.latitude_deg * 1e7), int(g.longitude_deg * 1e7), int(g.altitude * 1000),
                               70, 100, int(math.hypot(ve, vn) * 100), int(hdg * 100), 12)
        m.mav.attitude_send(tb, 0.0, 0.0, math.radians(hdg if hdg <= 180 else hdg - 360), 0.0, 0.0, 0.0)
    time.sleep(0.1)
