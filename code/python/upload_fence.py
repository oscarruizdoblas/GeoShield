#!/usr/bin/env python3
"""Upload the Padova PX4 geofence without weakening other PX4 limits."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from pymavlink import mavutil
from zones import HOME, KEEPOUT, KEEPIN

FENCE = mavutil.mavlink.MAV_MISSION_TYPE_FENCE
PARAM_TIMEOUT = 5.0


def param_name(value):
    if isinstance(value, bytes):
        return value.decode("ascii", "ignore").rstrip("\x00")
    return str(value).rstrip("\x00")


def read_param(link, system, component, name, timeout=PARAM_TIMEOUT):
    encoded = name.encode("ascii")
    link.mav.param_request_read_send(system, component, encoded, -1)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msg = link.recv_match(type="PARAM_VALUE", blocking=True,
                              timeout=min(1.0, deadline - time.monotonic()))
        if msg is not None and param_name(msg.param_id) == name:
            return float(msg.param_value)
    raise RuntimeError("PX4 no devolvió el parámetro %s" % name)


def set_param_verified(link, system, component, name, value, param_type):
    link.mav.param_set_send(system, component, name.encode("ascii"), float(value), param_type)
    actual = read_param(link, system, component, name)
    if abs(actual - value) > 1e-4:
        raise RuntimeError("%s quedó en %g; se solicitó %g" % (name, actual, value))
    return actual


def main():
    items = [("RETURN", mavutil.mavlink.MAV_CMD_NAV_FENCE_RETURN_POINT,
              0, 0, 0, 0, HOME[0], HOME[1], 30.0),
             ("KEEPIN", mavutil.mavlink.MAV_CMD_NAV_FENCE_CIRCLE_INCLUSION,
              KEEPIN["r"], 0, 0, 0, KEEPIN["lat"], KEEPIN["lon"], 0.0)]
    for zone in KEEPOUT:
        items.append(("KEEPOUT:" + zone["name"],
                      mavutil.mavlink.MAV_CMD_NAV_FENCE_CIRCLE_EXCLUSION,
                      zone["r"], 0, 0, 0, zone["lat"], zone["lon"], 0.0))

    link = mavutil.mavlink_connection("udpin:0.0.0.0:14540")
    print("Esperando heartbeat PX4 en UDP 14540...", flush=True)
    deadline = time.monotonic() + 30
    heartbeat = None
    while time.monotonic() < deadline:
        candidate = link.recv_match(type="HEARTBEAT", blocking=True,
                                    timeout=min(1.0, deadline - time.monotonic()))
        if candidate is not None and candidate.autopilot == mavutil.mavlink.MAV_AUTOPILOT_PX4:
            heartbeat = candidate
            break
    if heartbeat is None:
        raise RuntimeError("No llegó heartbeat de PX4 en 30 s")
    system, component = heartbeat.get_srcSystem(), heartbeat.get_srcComponent()
    print("PX4 conectado: sys=%d comp=%d (GCS ignoradas)" % (system, component), flush=True)

    # Preserve and report the PX4 horizontal/vertical limits before uploading.
    old_action = read_param(link, system, component, "GF_ACTION")
    old_hor = read_param(link, system, component, "GF_MAX_HOR_DIST")
    old_ver = read_param(link, system, component, "GF_MAX_VER_DIST")
    backup_dir = Path.home() / ".local/share/geoshield/backups" / ("px4-geofence-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup_dir.mkdir(parents=True, exist_ok=False)
    state = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "target_system": system,
        "target_component": component,
        "GF_ACTION_before": old_action,
        "GF_MAX_HOR_DIST_preserved": old_hor,
        "GF_MAX_VER_DIST_preserved": old_ver,
    }
    (backup_dir / "px4_geofence_params_before.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print("copia de parámetros PX4:", backup_dir / "px4_geofence_params_before.json", flush=True)
    print("Límites PX4 existentes (sin cambios): GF_MAX_HOR_DIST=%g, GF_MAX_VER_DIST=%g" %
          (old_hor, old_ver), flush=True)

    link.mav.mission_count_send(system, component, len(items), FENCE)
    deadline = time.monotonic() + 30
    accepted = False
    while time.monotonic() < deadline:
        msg = link.recv_match(type=["MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK"],
                              blocking=True, timeout=min(2.0, deadline - time.monotonic()))
        if msg is None:
            continue
        kind = msg.get_type()
        mission_type = getattr(msg, "mission_type", FENCE)
        if mission_type != FENCE:
            continue
        if kind in ("MISSION_REQUEST_INT", "MISSION_REQUEST"):
            seq = int(msg.seq)
            if seq < 0 or seq >= len(items):
                raise RuntimeError("PX4 pidió índice de fence fuera de rango: %d" % seq)
            tag, command, p1, p2, p3, p4, lat, lon, altitude = items[seq]
            if kind == "MISSION_REQUEST_INT":
                link.mav.mission_item_int_send(
                    system, component, seq, mavutil.mavlink.MAV_FRAME_GLOBAL_INT,
                    command, 0, 1, float(p1), float(p2), float(p3), float(p4),
                    int(round(lat * 1e7)), int(round(lon * 1e7)), float(altitude), FENCE)
            else:
                link.mav.mission_item_send(
                    system, component, seq, mavutil.mavlink.MAV_FRAME_GLOBAL,
                    command, 0, 1, float(p1), float(p2), float(p3), float(p4),
                    float(lat), float(lon), float(altitude), FENCE)
            print("Fence %d/%d: %s" % (seq + 1, len(items), tag), flush=True)
        else:
            if msg.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
                raise RuntimeError("PX4 rechazó el geofence: MISSION_ACK type=%d" % msg.type)
            accepted = True
            break
    if not accepted:
        raise RuntimeError("No llegó MISSION_ACK de aceptación para el geofence")
    print("PX4 aceptó los %d elementos de geofence." % len(items), flush=True)

    # Enforce an RTL response and retain any stricter user limits. If PX4 has
    # its default disabled limits (0), enable broad SITL-safe caps that still
    # contain the complete Padova route: 2.5 km horizontal and 120 m vertical.
    action = set_param_verified(link, system, component, "GF_ACTION", 3,
                                mavutil.mavlink.MAV_PARAM_TYPE_INT32)
    target_hor = old_hor if old_hor > 0 else 2500.0
    target_ver = old_ver if old_ver > 0 else 120.0
    if old_hor <= 0:
        set_param_verified(link, system, component, "GF_MAX_HOR_DIST", target_hor,
                           mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    if old_ver <= 0:
        set_param_verified(link, system, component, "GF_MAX_VER_DIST", target_ver,
                           mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    hor = read_param(link, system, component, "GF_MAX_HOR_DIST")
    ver = read_param(link, system, component, "GF_MAX_VER_DIST")
    if abs(hor - target_hor) > 1e-4 or abs(ver - target_ver) > 1e-4:
        raise RuntimeError("Los límites GF_MAX_* no coinciden con los valores de seguridad esperados")
    print("GF_ACTION=%g (RTL); límites activos: GF_MAX_HOR_DIST=%g m, GF_MAX_VER_DIST=%g m" %
          (action, hor, ver), flush=True)
    print("FIN-FENCE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR: %s" % exc, file=sys.stderr, flush=True)
        sys.exit(1)
