import sys, time
from pymavlink import mavutil
sys.path.insert(0, '/home/oruiz/geoshield')
from zones import HOME, KEEPOUT, KEEPIN

TS, TC = 1, 1
FENCE = mavutil.mavlink.MAV_MISSION_TYPE_FENCE

m = mavutil.mavlink_connection('udpin:0.0.0.0:14540')
print("esperando heartbeat...", flush=True)
if m.wait_heartbeat(timeout=20) is None:
    print("SIN HEARTBEAT", flush=True); sys.exit(1)
print("enlace OK", flush=True)

# (tag, cmd, p1=radio, p2, p3, p4, lat, lon, z)
items = []
items.append(("RETURN", mavutil.mavlink.MAV_CMD_NAV_FENCE_RETURN_POINT, 0,0,0,0, HOME[0], HOME[1], 30.0))
items.append(("KEEPIN", mavutil.mavlink.MAV_CMD_NAV_FENCE_CIRCLE_INCLUSION, KEEPIN['r'],0,0,0, KEEPIN['lat'], KEEPIN['lon'], 0.0))
for z in KEEPOUT:
    items.append(("KEEPOUT:"+z['name'], mavutil.mavlink.MAV_CMD_NAV_FENCE_CIRCLE_EXCLUSION, z['r'],0,0,0, z['lat'], z['lon'], 0.0))

N = len(items)
print("subiendo %d items de fence..." % N, flush=True)
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
            print("ACK fence type=%d (0=ACEPTADO)" % msg.type, flush=True)
            done = True
if not done:
    print("AVISO: sin ACK de fence", flush=True)

# Parametros del escenario: RTL al violar, desactivar las vallas simples de distancia
def set_param(name, val, ptype):
    m.mav.param_set_send(TS, TC, name, float(val), ptype)
    time.sleep(0.3)
set_param(b'GF_ACTION', 3, mavutil.mavlink.MAV_PARAM_TYPE_INT32)       # RTL
set_param(b'GF_MAX_HOR_DIST', 0.0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)  # desactivar valla radial
set_param(b'GF_MAX_VER_DIST', 0.0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
time.sleep(1)

# leer de vuelta
for name in [b'GF_ACTION', b'GF_MAX_HOR_DIST', b'GF_MAX_VER_DIST']:
    m.mav.param_request_read_send(TS, TC, name, -1)
    t1 = time.time()
    while time.time()-t1 < 3:
        pm = m.recv_match(type='PARAM_VALUE', blocking=True, timeout=2)
        if pm and pm.param_id.strip('\x00') == name.decode():
            print("  %s = %g" % (name.decode(), pm.param_value), flush=True); break
print("FIN-FENCE", flush=True)
