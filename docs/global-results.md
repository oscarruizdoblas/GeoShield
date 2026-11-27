# Global results — seven SITL reference flights

Summary of [`global-results.csv`](global-results.csv): one normal flight, three gradual-drift variants and three abrupt-jump variants. All tests were run in PX4 SITL + Gazebo. Each row is a single run; the [campaign](campaign/README.md) gives means over repeated runs.

| Test | Detection | Max. real error | Palazzo Bo |
|---|---:|---:|---|
| Normal | No alerts | — | minimum 292 m from the centre; outside |
| Jump, no response | 0.13 s | 180.34 m | 105 m inside for 58.47 s |
| Drift, no response | 2.36 s | 180.76 m | 106 m inside for 61.47 s |
| Jump, HOLD/return | 0.06 s | 180.13 m | outside; minimum 583 m from the centre |
| Drift, HOLD/return | 2.10 s | 81.66 m | outside; minimum 569 m from the centre |
| Jump, GPS cut | 0.03 s | 17.81 m | outside; minimum 584 m from the centre |
| Drift, GPS cut | 2.30 s | 82.57 m | outside; minimum 569 m from the centre |

CSV columns:
- `delay_s`: detection delay in simulation time.
- `offset_at_detection_m`: GPS offset when the first alert fired.
- `real_error_max_m`: maximum distance between the EKF estimate and the real position.
- `min_dist_bo_m`, `enters_bo`, `secs_inside_bo`, `penetration_bo_m`: the real drone relative to Palazzo Bo.

## Interpretation

- **Geofence:** on its own it did not stop the incursions, because PX4 was navigating on an estimate that stayed outside the zone.
- **Detection:** the detector flagged the jumps almost immediately and the drift in about 2.1–2.4 s.
- **HOLD/return:** it kept all the defended variants outside, but with the GPS still altered the real error could keep growing.
- **GPS cut:** cutting GPS fusion reduced the attacker's influence on PX4, at the cost of relying on inertial navigation and on the limits of operating without GPS.

Figures are in the experiment folders: [gradual drift](experiment-02/README.md), [abrupt jump](experiment-03/README.md), [drift with defence](experiment-04/README.md), [jump with defence](experiment-05/README.md).

## Limits

- **Single runs:** the table above has one run per configuration. The [27-flight campaign](campaign/README.md) repeats them:

  | Repeated configuration | Detected | Mean delay ± std |
  |---|---:|---:|
  | Normal flight (5 flights) | 0 false alarms | — |
  | Jump | 5/5 | 0.12 ± 0.05 s |
  | Drift 3 m/s | 5/5 | 2.21 ± 0.13 s |
  | Drift 2 m/s | 3/3 | 2.97 ± 0.19 s |

- **Slow drift:** a drift with consistent velocity at 1 m/s or 0.5 m/s is not detected (0/3 and 0/3). Its signals stay below the peaks of a normal flight, and at 1 m/s the real drone enters Palazzo Bo by about 17 m. If the attacker does not forge the velocity, the 1 m/s drift is detected (3/3, 7.7 s).
- **Inertial navigation:** without GPS it is only temporary; the tests rely on the contingency modes configured in PX4.
- **Telemetry:** the raw CSV telemetry of every flight is in `experiment-0X/evidence/telemetry/` and `campaign/evidence/telemetry/`; the PX4 ULog files stay in WSL because of their size.
