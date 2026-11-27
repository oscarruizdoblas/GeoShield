# Experiment 05 — Abrupt jump with the GeoShield defence

## Setup

The same attack as Experiment 03: an instantaneous 180 m GPS jump towards Palazzo Bo, applied 400 m from A. This time the full GeoShield response is active. In order:

1. HOLD.
2. Warning to the ground station.
3. Cut GPS fusion in the EKF.
4. Return to the last trusted point (the EKF position 5 s before the alert).
5. Landing at A with the GPS restored.

```bash
SHOW=1 bash ~/geoshield/run_attack_test.sh jump_full_defence jump corte --verbose
```

## Result

| Detection | Defence sequence | Max. real error | Palazzo Bo |
|---:|---|---:|---|
| 0.07 s (`salto_GPS`) | HOLD and warning on detection, GPS cut 1 s later; return after 2 s; at the trusted point after 11 s | 10.50 m | Outside; minimum 584 m from the centre |

The drone lands 1.1 m from A.

- **Zone avoided:** without the defence the same attack takes the real drone 105 m into Palazzo Bo (Experiment 03).
- **Small real error:** the GPS cut arrives before the EKF accepts the fake position, so the real error stays at about 10 m.

## Evidence

- **Video 5:** [open in Google Drive](https://drive.google.com/file/d/1U6xJTuMvLJtAozva9iR0o3s1v6ROpLYV/view?usp=drive_link). Same screen layout as video 4.
- [Trajectory](evidence/images/jump_full_defence_map.png) · [signals](evidence/images/jump_full_defence_signals.png)
- Telemetry: `evidence/telemetry/jump_full_defence.zip`.

Repeated in the [campaign](../campaign/README.md), where every jump flight ran this defence: 5/5 detected in 0.12 ± 0.05 s, all outside Palazzo Bo and landed at A.
