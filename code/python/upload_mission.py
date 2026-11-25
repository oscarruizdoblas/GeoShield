#!/usr/bin/env python3
"""Upload and read back the normal Padova mission from the QGC .plan file.
This script transfers mission items only; it never arms or starts the vehicle.
"""
import json
import math
import sys
import time
from pathlib import Path
from pymavlink import mavutil
from zones import START

MISSION = mavutil.mavlink.MAV_MISSION_TYPE_MISSION
FRAME_TO_INT = {
    mavutil.mavlink.MAV_FRAME_GLOBAL: mavutil.mavlink.MAV_FRAME_GLOBAL_INT,
    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT: mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
    mavutil.mavlink.MAV_FRAME_GLOBAL_TERRAIN_ALT: mavutil.mavlink.MAV_FRAME_GLOBAL_TERRAIN_ALT_INT,
}


def is_px4_heartbeat(msg):
    return msg is not None and msg.get_type() == "HEARTBEAT" and msg.autopilot == mavutil.mavlink.MAV_AUTOPILOT_PX4


def wait_for(link, types, predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msg = link.recv_match(type=types, blocking=True, timeout=min(1.0, deadline - time.monotonic()))
        if msg is not None and predicate(msg):
            return msg
    return None


def item_frame(item):
    frame = int(item["frame"])
    if frame not in FRAME_TO_INT:
        raise RuntimeError("Frame de misión no admitido: %s" % frame)
    return FRAME_TO_INT[frame]


def to_mission_items(plan_path):
    data = json.loads(plan_path.read_text(encoding="utf-8"))
    home = data["mission"]["plannedHomePosition"]
    if abs(float(home[0]) - START[0]) > 1e-7 or abs(float(home[1]) - START[1]) > 1e-7:
        raise RuntimeError("El HOME del plan no coincide con zones.py")
    items = data["mission"]["items"]
    if not items:
        raise RuntimeError("El plan QGC no contiene misión")
    for item in items:
        if item.get("type") != "SimpleItem":
            raise RuntimeError("El plan contiene un elemento no compatible con SimpleItem")
    return items


def main():
    default_plan = Path(__file__).resolve().parents[1] / "qground" / "geoshield_padova.plan"
    plan_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else default_plan
    items = to_mission_items(plan_path)
    link = mavutil.mavlink_connection("udpin:0.0.0.0:14540")
    print("Esperando heartbeat de PX4 en UDP 14540...", flush=True)
    deadline = time.monotonic() + 30
    heartbeat = None
    while time.monotonic() < deadline:
        candidate = link.recv_match(type="HEARTBEAT", blocking=True,
                                    timeout=min(1.0, deadline - time.monotonic()))
        if is_px4_heartbeat(candidate):
            heartbeat = candidate
            break
    if heartbeat is None:
        raise RuntimeError("No llegó heartbeat PX4 en 30 s")
    system, component = heartbeat.get_srcSystem(), heartbeat.get_srcComponent()
    print("PX4 conectado: sys=%d comp=%d; GCS ignoradas" % (system, component), flush=True)

    link.mav.mission_count_send(system, component, len(items), MISSION)
    deadline = time.monotonic() + 30
    accepted = False
    while time.monotonic() < deadline:
        msg = link.recv_match(type=["MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK"],
                              blocking=True, timeout=min(1.0, deadline - time.monotonic()))
        if msg is None or getattr(msg, "mission_type", MISSION) != MISSION:
            continue
        kind = msg.get_type()
        if kind == "MISSION_ACK":
            if msg.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
                raise RuntimeError("PX4 rechazó la misión: MISSION_ACK type=%d" % msg.type)
            accepted = True
            break
        seq = int(msg.seq)
        if seq < 0 or seq >= len(items):
            raise RuntimeError("PX4 pidió índice fuera de rango: %d" % seq)
        item = items[seq]
        params = list(item.get("params", []))
        if len(params) != 7:
            raise RuntimeError("MISSION item %d debe tener 7 params" % seq)
        p1, p2, p3, p4, lat, lon, alt = params
        pvals = [float(v) if v is not None else float("nan") for v in (p1, p2, p3, p4)]
        cmd = int(item["command"])
        frame = item_frame(item)
        if kind == "MISSION_REQUEST_INT":
            link.mav.mission_item_int_send(
                system, component, seq, frame, cmd, 0, 1,
                *pvals, int(round(float(lat) * 1e7)), int(round(float(lon) * 1e7)),
                float(alt), MISSION)
        else:
            legacy_frame = int(item["frame"])
            link.mav.mission_item_send(
                system, component, seq, legacy_frame, cmd, 0, 1,
                *pvals, float(lat), float(lon), float(alt), MISSION)
        print("Misión %d/%d: cmd=%d %.7f, %.7f alt=%.1f" %
              (seq + 1, len(items), cmd, float(lat), float(lon), float(alt)), flush=True)
    if not accepted:
        raise RuntimeError("No llegó MISSION_ACK de aceptación")
    print("PX4 aceptó %d elementos de misión." % len(items), flush=True)

    # Read the uploaded mission back so the normal route is verified in PX4.
    link.mav.mission_request_list_send(system, component, MISSION)
    count = wait_for(link, "MISSION_COUNT",
                     lambda m: getattr(m, "mission_type", MISSION) == MISSION, timeout=8)
    if count is None or int(count.count) != len(items):
        raise RuntimeError("Read-back count incorrecto: esperado %d, recibido %s" %
                           (len(items), getattr(count, "count", None)))
    for seq, expected in enumerate(items):
        link.mav.mission_request_int_send(system, component, seq, MISSION)
        got = wait_for(link, ["MISSION_ITEM_INT", "MISSION_ITEM"],
                       lambda m: int(m.seq) == seq and getattr(m, "mission_type", MISSION) == MISSION,
                       timeout=8)
        if got is None or int(got.command) != int(expected["command"]):
            raise RuntimeError("Read-back falló para el elemento %d" % seq)
        params = expected["params"]
        exp_lat, exp_lon = float(params[4]), float(params[5])
        if got.get_type() == "MISSION_ITEM_INT":
            got_lat, got_lon = got.x / 1e7, got.y / 1e7
        else:
            got_lat, got_lon = float(got.x), float(got.y)
        if abs(got_lat - exp_lat) > 2e-7 or abs(got_lon - exp_lon) > 2e-7:
            raise RuntimeError("Coordenadas leídas no coinciden en item %d: %.7f, %.7f" %
                               (seq, got_lat, got_lon))
    link.mav.mission_ack_send(system, component, mavutil.mavlink.MAV_MISSION_ACCEPTED, MISSION)
    print("READBACK OK: %d items; misión cargada pero vehículo sin armar." % len(items), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR: %s" % exc, file=sys.stderr, flush=True)
        sys.exit(1)
