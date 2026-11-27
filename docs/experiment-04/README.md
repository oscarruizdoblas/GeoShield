# Experiment 04 — Gradual drift with the GeoShield defence

## Setup

The same attack as Experiment 02: a 3 m/s GPS drift with consistent velocity, up to 180 m towards Palazzo Bo, starting 400 m from A. This time the full GeoShield response is active. In order:

1. HOLD.
2. Warning to the ground station.
3. Cut GPS fusion in the EKF.
4. Return to the last trusted point (the EKF position 5 s before the alert).
5. Landing at A with the GPS restored.

```bash
SHOW=1 bash ~/geoshield/run_attack_test.sh drift_full_defence drift corte --verbose
```

## Result

| Detection | Defence sequence | Max. real error | Palazzo Bo |
|---:|---|---:|---|
| 2.40 s (`innov_sostenida`) | HOLD, warning and GPS cut on detection; return after 2 s; at the trusted point after 15 s | 95.93 m | Outside; minimum 569 m from the centre |

The drone lands 1.1 m from A.

- **Zone avoided:** without the defence the same attack takes the real drone 106 m into Palazzo Bo (Experiment 02).
- **Real error:** by the time the drift is detected, the EKF has already absorbed part of the fake velocity. The inertial error keeps growing, although the attacker no longer steers the drone.
- **Cost of the cut:** without GPS, inertial navigation lasts about 10 s before PX4 switches to a blind landing.

## Evidence

- **Video 4:** [open in Google Drive](https://drive.google.com/file/d/1aO4El03Wdpys6EX93IGjGctQm_RgIEWy/view?usp=drive_link). The screen shows:
  - the terminal with the attack and the defence steps;
  - Gazebo;
  - QGC with two vehicles: 1 = what the drone believes, 2 = its real position;
  - the detector panel.
- [Trajectory](evidence/images/drift_full_defence_map.png) · [signals](evidence/images/drift_full_defence_signals.png)
- Telemetry: `evidence/telemetry/drift_full_defence.zip`.

Repeated in the [campaign](../campaign/README.md), where every 3 m/s drift flight ran this defence: 5/5 detected in 2.21 ± 0.13 s, all outside Palazzo Bo and landed at A.
