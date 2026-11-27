# GeoShield Python programs

All `.py` files are in the same folder so they can import each other. `zones.py` is the single source of coordinates and radii. Every file starts with a docstring that explains what it does and how.

| Program | Role |
|---|---|
| `zones.py` | Coordinates of A/HOME, B and the no-fly zones (Palazzo Bo, Palazzo Liviano). |
| `planner.py` | Shortest route around the no-fly zones (visibility graph + Dijkstra). |
| `plan_and_fly.py` | Flies the mission A→B→A in PX4 SITL and records telemetry. |
| `make_qgc_plan.py` | Generates the QGroundControl `.plan` from `zones.py`. |
| `upload_fence.py` | Uploads and verifies the geofence in PX4 over MAVLink. |
| `build_world.py`, `make_texture.py` | Generate the Padova SDF world and the ground texture (OSM tiles). |
| `logger.py` | Records MAVLink telemetry to CSV. |
| `analyze.py` | Signal statistics of the normal flight; the detector thresholds come from here. |
| `spoof_relay.py` | **Attack.** Relay of the simulated Gazebo GPS: passes the true GPS or forges it (jump or drift). Simulation only. |
| `detector.py` | **Detector and defence.** Rules on GPS, EKF and innovations; with `--respond --cut-gps`: HOLD → warning → GPS cut → return. |
| `return_home.py` | Return along the reversed outbound route, joining it at the most convenient point without crossing zones. |
| `offboard_breach_test.py` | Checks whether the PX4 geofence stops a stream of OFFBOARD commands towards a no-fly zone. |
| `analyze_attack.py` | Maps and signal plots of an attack flight, plus the results table. |
| `evaluate_campaign.py` | Campaign statistics: mean/std delay, false alarms, missed detections and figures. |

They run from `~/geoshield` in WSL (`bash code/sync_wsl.sh` copies them). `spoof_relay.py` uses the system Python (`/usr/bin/python3`, for gz-transport); the rest need a Python with `pymavlink`.

## Launchers (`launchers/`)

- `install_px4_mavlink.sh`: adds the MAVLink link 14541 used by the detector to PX4 (once).
- `run_padova_spoof.sh`: starts the SITL with the Gazebo GPS redirected to the relay.
- `run_attack_test.sh NAME none|jump|drift [no|si|corte] [relay args]`: one complete test (relay, detector, flight, end of attack, flight home). The response values mean: `no` = detect only, `si` = HOLD + return, `corte` = HOLD + GPS cut + return.
- `run_campaign.sh [TAG]`: unattended campaign of repeated flights; then `evaluate_campaign.py TAG`.

The tools used only to record the videos are in [`../demo/`](../demo/README.md).
