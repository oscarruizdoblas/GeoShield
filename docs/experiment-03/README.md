# Experiment 03 — Abrupt GPS jump

## Setup

An instantaneous 180 m GPS jump (90 m east, 156 m south) towards Palazzo Bo, applied when the drone is 400 m from A. The same three variants as Experiment 02.

## Results

| Variant | Detection | Max. real error | Palazzo Bo |
|---|---:|---:|---|
| Detection only, no response | 0.13 s | 180.34 m | Enters by 105.43 m; 58.47 s inside. |
| HOLD and return | 0.06 s | 180.13 m | Outside; minimum 583.43 m from the centre. |
| HOLD, GPS cut and return | 0.03 s | 17.81 m | Outside; minimum 583.99 m from the centre. |

The first rule was `salto_GPS` (GPS jump) in all three.

- **HOLD/return:** the drone stays out of Palazzo Bo, but the EKF accepts the fake position and the real error remains at 180 m.
- **GPS cut:** the cut arrives before the EKF absorbs the fake position, so the error stays at a few metres.

## Evidence

- **Video 3** (jump, no defence): [open in Google Drive](https://drive.google.com/file/d/1QcZTyEa1f8kiXsY9Oqtt0Oej3qJi0Bpp/view?usp=drive_link). That flight gave 0.14 s detection and 105.38 m inside Palazzo Bo, the same as the table.
- No response: [trajectory](evidence/images/jump_no_response_map.png) · [signals](evidence/images/jump_no_response_signals.png)
- HOLD/return: [trajectory](evidence/images/jump_hold_return_map.png) · [signals](evidence/images/jump_hold_return_signals.png)
- GPS cut: [trajectory](evidence/images/jump_gps_cut_map.png) · [signals](evidence/images/jump_gps_cut_signals.png)
- Telemetry of the three variants in `evidence/telemetry/` (one `.zip` per flight).

Repeated in the [campaign](../campaign/README.md): 5/5 detected in 0.12 ± 0.05 s.
