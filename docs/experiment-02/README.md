# Experiment 02 — Gradual GPS drift

## Setup

A synthetic GPS drift at 3 m/s, with consistent velocity and a smooth 4 s start, up to 180 m (90 m east, 156 m south) towards Palazzo Bo. It starts when the drone is 400 m from A. It is injected inside Gazebo; no radio or real hardware is used.

Three variants are compared: detection only, HOLD/return, and HOLD + GPS cut + return.

## Results

| Variant | Detection | Max. real error | Palazzo Bo |
|---|---:|---:|---|
| Detection only, no response | 2.36 s | 180.76 m | Enters by 105.67 m; 61.47 s inside. |
| HOLD and return | 2.10 s | 81.66 m | Outside; minimum 568.95 m from the centre. |
| HOLD, GPS cut and return | 2.30 s | 82.57 m | Outside; minimum 569.43 m from the centre. |

The first rule was always `innov_sostenida` (EKF velocity innovation). The GPS–EKF separation never exceeded 0.9 m during the drift: the EKF follows the fake GPS, so comparing the two does not reveal it. Cutting the GPS does not erase the error already accumulated in the 2 s before detection.

## Evidence

- **Video 2** (drift, no defence): [open in Google Drive](https://drive.google.com/file/d/1qGbja2jfa0HNdwdcPT4YCkKiQu5CYcXs/view?usp=drive_link). The screen shows:
  - the terminal with the attack;
  - Gazebo with the drone drawn 40 times bigger;
  - QGC with two vehicles: 1 = what the drone believes, 2 = its real position;
  - the detector panel.

  That flight gave 2.10 s detection and 105.67 m inside Palazzo Bo, the same as the table.
- No response: [trajectory](evidence/images/drift_no_response_map.png) · [signals](evidence/images/drift_no_response_signals.png)
- HOLD/return: [trajectory](evidence/images/drift_hold_return_map.png) · [signals](evidence/images/drift_hold_return_signals.png)
- GPS cut: [trajectory](evidence/images/drift_gps_cut_map.png) · [signals](evidence/images/drift_gps_cut_signals.png)
- Telemetry of the three variants in `evidence/telemetry/` (one `.zip` per flight).

Repeated in the [campaign](../campaign/README.md): 5/5 detected in 2.21 ± 0.13 s.
