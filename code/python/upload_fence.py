#!/usr/bin/env python3
"""GeoShield - upload the geofence to PX4 over MAVLink (port 14540) and set the fence parameters.

Fence items (MAVLink mission protocol, mission type FENCE), all taken from zones.py:
  - a return point at HOME,
  - one inclusion circle (KEEPIN: the allowed operating area),
  - one exclusion circle per no-fly zone (KEEPOUT: Palazzo Bo and Palazzo Liviano).
Parameters: GF_ACTION=3 (Return-to-Launch on breach) and the simple max-distance/max-altitude
fences disabled, so only the zones above are enforced.

Note: PX4 evaluates the geofence on its ESTIMATED position. With a spoofed GPS the estimate
is wrong, so the fence cannot protect the real drone; this is one of the project's findings.
"""
import sys, time, struct
from pymavlink import mavutil
from zones import HOME, KEEPOUT, KEEPIN

TS, TC = 1, 1
FENCE = mavutil.mavlink.MAV_MISSION_TYPE_FENCE

m = mavutil.mavlink_connection('udpin:0.0.0.0:14540')
print("waiting for heartbeat...", flush=True)
if m.wait_heartbeat(timeout=20) is None:
    print("NO HEARTBEAT", flush=True); sys.exit(1)
print("link OK", flush=True)

# (tag, command, p1=radius, p2, p3, p4, lat, lon, z)
items = []
items.append(("RETURN", mavutil.mavlink.MAV_CMD_NAV_FENCE_RETURN_POINT, 0,0,0,0, HOME[0], HOME[1], 30.0))
items.append(("KEEPIN", mavutil.mavlink.MAV_CMD_NAV_FENCE_CIRCLE_INCLUSION, KEEPIN['r'],0,0,0, KEEPIN['lat'], KEEPIN['lon'], 0.0))
for z in KEEPOUT:
    items.append(("KEEPOUT:"+z['name'], mavutil.mavlink.MAV_CMD_NAV_FENCE_CIRCLE_EXCLUSION, z['r'],0,0,0, z['lat'], z['lon'], 0.0))

# Mission upload handshake: send the count, then answer every item request, then wait for the ACK
N = len(items)
print("uploading %d fence items..." % N, flush=True)
m.mav.mission_count_send(TS, TC, N, FENCE)

done = False; t0 = time.time()
while time.time()-t0 < 25 and not done:
    msg = m.recv_match(type=['MISSION_REQUEST_INT','MISSION_REQUEST','MISSION_ACK'], blocking=True, timeout=3)
    if msg is None:
        continue
    tp = msg.get_type()
    if tp in ('MISSION_REQUEST_INT','MISSION_REQUEST'):
        if getattr(msg, 'mission_type', 0) != FENCE:
            continue
        seq = msg.seq
        tag, cmd, p1, p2, p3, p4, lat, lon, z = items[seq]
        m.mav.mission_item_int_send(TS, TC, seq, mavutil.mavlink.MAV_FRAME_GLOBAL, cmd, 0, 1,
                                    float(p1), float(p2), float(p3), float(p4),
                                    int(lat*1e7), int(lon*1e7), float(z), FENCE)
        print("  item %d -> %s" % (seq, tag), flush=True)
    elif tp == 'MISSION_ACK':
        if getattr(msg, 'mission_type', 0) == FENCE:
            print("fence ACK type=%d (0=ACCEPTED)" % msg.type, flush=True)
            done = True
if not done:
    print("WARNING: no fence ACK", flush=True)

# Scenario parameters: RTL on breach, simple distance fences disabled
INT32 = mavutil.mavlink.MAV_PARAM_TYPE_INT32
def set_param(name, val, ptype):
    # PX4 copies the param_value field BYTE BY BYTE: an integer must be sent with its bytes
    # packed inside the float (sending float(3) left GF_ACTION=1077936128 instead of 3).
    v = struct.unpack('<f', struct.pack('<i', int(val)))[0] if ptype == INT32 else float(val)
    m.mav.param_set_send(TS, TC, name, v, ptype)
    time.sleep(0.3)
def decode(pm):
    return struct.unpack('<i', struct.pack('<f', pm.param_value))[0] if pm.param_type == INT32 else pm.param_value
set_param(b'GF_ACTION', 3, mavutil.mavlink.MAV_PARAM_TYPE_INT32)          # 3 = Return-to-Launch
set_param(b'GF_MAX_HOR_DIST', 0.0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)  # 0 = radial fence disabled
set_param(b'GF_MAX_VER_DIST', 0.0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)  # 0 = altitude fence disabled
time.sleep(1)

# Read the parameters back to verify them
for name in [b'GF_ACTION', b'GF_MAX_HOR_DIST', b'GF_MAX_VER_DIST']:
    m.mav.param_request_read_send(TS, TC, name, -1)
    t1 = time.time()
    while time.time()-t1 < 3:
        pm = m.recv_match(type='PARAM_VALUE', blocking=True, timeout=2)
        if pm and pm.param_id.strip('\x00') == name.decode():
            print("  %s = %g" % (name.decode(), decode(pm)), flush=True); break
print("END-FENCE", flush=True)
