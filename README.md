# GeoShield

Project for the **Cyberphysical and IoT Security** course (Università di Padova). We study GPS spoofing attacks against an autonomous drone and build a detector and a response that keep it out of no-fly zones.

Everything runs in **simulation** (PX4 SITL + Gazebo), with no hardware and no radio. The fake GPS is injected inside Gazebo; no real GPS signal is ever transmitted.

## Repository structure

```text
GeoShield/
├── code/
│   ├── python/         # attack, detector, response, flight, analysis + experiment launchers
│   ├── gazebo/         # Padova world, ground model and Gazebo launchers
│   ├── qground/        # QGroundControl mission and geofence
│   ├── demo/           # tools used only to record the videos
│   └── sync_wsl.sh     # copies the code to ~/geoshield (WSL) and checks it compiles
└── docs/
    ├── experiment-01/  # normal flight (baseline)
    ├── experiment-02/  # gradual GPS drift
    ├── experiment-03/  # abrupt GPS jump
    ├── experiment-04/  # gradual drift with the full GeoShield defence
    ├── experiment-05/  # abrupt jump with the full GeoShield defence
    ├── campaign/       # 27 repeated flights: means, false alarms, missed detections
    ├── global-results.md / .csv
    └── getting-started.md
```

Start with [`docs/README.md`](docs/README.md) and [`code/python/README.md`](code/python/README.md).

## Scenario (Padova, real coordinates)

- **A (take-off / HOME):** Riviera Paleocapa — `45.4021, 11.8670`
- **B (destination):** Torre Archimede — `45.4113328, 11.8878209`
- **No-fly zones:** Palazzo Bo (r = 220 m) and Palazzo Liviano (r = 150 m). The straight line A→B crosses Palazzo Bo; the planned route goes around it.
- Single source of coordinates and radii: [`code/python/zones.py`](code/python/zones.py).

## How it works

```text
Gazebo GPS sensor ──► spoof_relay.py (attack) ──► PX4 EKF2 ──► flight controller
                                                     │ MAVLink 14541
                                                     ▼
                                    detector.py (detection + response)
```

- **Attack** ([`spoof_relay.py`](code/python/spoof_relay.py)): sits between the simulated GPS sensor and PX4 and adds a false offset of 180 m towards Palazzo Bo. It can apply it instantly (*jump*) or gradually, with a consistent fake velocity (*drift*). PX4 believes the forged position and steers the *real* drone off its route.
- **Detector** ([`detector.py`](code/python/detector.py)): compares the raw GPS with the EKF estimate, watches the EKF innovation ratios and looks for position jumps. Thresholds were calibrated on clean flights for zero false alarms.
- **Response**: HOLD → warning to the ground station → stop fusing GPS in the EKF (inertial navigation) → return to the last trusted point.

## Experiments

- **01 — Normal flight:** A→B→A completed with no manipulated GPS and no detector alerts.
- **02 — Gradual drift (3 m/s):** without a response, the real drone enters Palazzo Bo by ~106 m while PX4 believes it is on its route. The detector sees it in ~2.1–2.4 s. Three responses are compared.
- **03 — Abrupt jump (180 m):** detected in 0.03–0.14 s; the same three responses.
- **04 — Drift with defence:** the attack of 02 with the full defence: detected in 2.40 s, the drone stays 569 m from the centre of Palazzo Bo.
- **05 — Jump with defence:** the attack of 03 with the full defence: detected in 0.07 s, real error only 10.5 m.
- **Campaign (27 flights):** 0 false alarms; jump detected 5/5 in 0.12 ± 0.05 s; 3 m/s drift 5/5 in 2.21 ± 0.13 s; 2 m/s drift 3/3 in 2.97 ± 0.19 s. A coherent drift at ≤ 1 m/s was not detected (0/6). See [`docs/campaign`](docs/campaign/README.md).

The five videos (normal flight, drift and jump without defence, drift and jump with defence) are linked in [`docs/README.md`](docs/README.md#videos). Results: [`docs/global-results.md`](docs/global-results.md). The raw telemetry of every flight is zipped in `docs/*/evidence/telemetry/`.

## Quick start (WSL)

```bash
bash code/sync_wsl.sh                                  # code -> ~/geoshield, world -> PX4
bash ~/geoshield/install_px4_mavlink.sh                # once: MAVLink link 14541 for the detector
bash ~/geoshield/prepare_demo.sh                       # SITL + Gazebo + QGC + panel, ready to fly
SHOW=1 bash ~/geoshield/run_attack_test.sh video_drift drift no --verbose   # flight with a drift attack
```

More detail in [`docs/getting-started.md`](docs/getting-started.md). To repeat each configuration and get means and false-positive/negative rates: `run_campaign.sh` + `evaluate_campaign.py`.

## Main findings

- **The PX4 geofence is blind to spoofing:** it is evaluated on the estimated position. With a forged GPS the real drone entered Palazzo Bo by more than 100 m and PX4 did not react.
- **A coherent drift is not visible when comparing GPS and EKF** (they never differ by more than 0.9 m). Only the EKF velocity innovation at the start of the drift reveals it (rule `innov_sostenida`).
- **Detector limit:** a slow drift (≤ 1 m/s) that forges position and velocity consistently is indistinguishable from normal noise for a detector that only compares GPS with the EKF. At 1 m/s it took the real drone 17 m into Palazzo Bo without a single alert. An independent position reference is needed (vision, optical flow, a second antenna).
- **Responding without isolating the GPS is not enough:** HOLD and return are executed on false coordinates. Cutting GPS fusion takes control away from the attacker, at the cost of ~10 s of inertial navigation and a blind landing.
- **The geofence does stop commands:** with `GF_ACTION=3`, PX4 rejects a reposition into a zone and brakes an OFFBOARD velocity stream 8 m before the edge (`offboard_breach_test.py`). PX4 integer parameters must be sent over MAVLink with their bytes packed in the float (sent as a plain float, `GF_ACTION` ends up as 1077936128).
