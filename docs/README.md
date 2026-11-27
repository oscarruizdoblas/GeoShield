# GeoShield experiments

| Folder | Experiment | Content |
|---|---|---|
| [experiment-01](experiment-01/README.md) | Normal flight | Baseline A→B→A without attack; 0 detector alerts. |
| [experiment-02](experiment-02/README.md) | Gradual drift | Three variants: no response, HOLD/return and GPS cut. |
| [experiment-03](experiment-03/README.md) | Abrupt jump | The same three variants. |
| [experiment-04](experiment-04/README.md) | Drift with defence | The drift of 02 with the full GeoShield defence. |
| [experiment-05](experiment-05/README.md) | Jump with defence | The jump of 03 with the full GeoShield defence. |
| [campaign](campaign/README.md) | 27-flight campaign | Means, spread, false alarms, missed detections and the slowest detectable drift. |

Summary of the seven reference flights: [global-results.md](global-results.md) ([CSV](global-results.csv)). How to reproduce everything: [getting-started.md](getting-started.md).

## Videos

| Video | Content | Where |
|---|---|---|
| 1 | Normal flight A→B→A | [experiment-01](experiment-01/README.md) |
| 2 | Gradual drift, no defence | [experiment-02](experiment-02/README.md) |
| 3 | Abrupt jump, no defence | [experiment-03](experiment-03/README.md) |
| 4 | Gradual drift with defence | [experiment-04](experiment-04/README.md) |
| 5 | Abrupt jump with defence | [experiment-05](experiment-05/README.md) |

## Detection rules and response steps

The rule and action identifiers appear in the figures, the CSV files and the telemetry exactly as below.

| Rule | Meaning | Threshold |
|---|---|---|
| `salto_GPS` | GPS jump: the raw GPS fix moves faster than physically possible | > 15 m/s between samples |
| `salto_EKF` | EKF jump: the same check on the EKF position | > 15 m/s |
| `div_GPS_EKF` | GPS/EKF divergence: raw GPS and EKF estimate disagree | > 3 m |
| `deriva_gradual` | Gradual drift: moderate divergence that persists | > 1.5 m for 3 s |
| `innov_pos`, `innov_vel` | The EKF position/velocity innovation ratio is high | > 0.5 |
| `innov_sostenida` | Sustained velocity innovation: the start of a drift with consistent velocity | > 0.15 for 1 s |

| Response step | Meaning |
|---|---|
| `HOLD` | Mission aborted; the drone holds at its estimated position. |
| `AVISO` | Warning: a STATUSTEXT message is sent to QGroundControl. |
| `CORTE_GPS` | GPS cut: `EKF2_GPS_CTRL=0`, the EKF stops fusing GPS and navigates on inertial sensors. |
| `RETORNO` | Return to the last trusted point (the EKF position 5 s before the anomaly). |
| `EN_PUNTO` | Trusted point reached; the drone holds there. |

In `run_attack_test.sh` the response argument is `no` (detect only), `si` (HOLD + return) or `corte` (HOLD + GPS cut + return); in the result tables they are called `none`, `hold_return` and `hold_gps_cut_return`.

## Telemetry

Each `experiment-0X/evidence/telemetry/` folder has one `.zip` per flight with the CSV files of the relay (true and forged GPS), the detector (signals, alerts, response) and the flight. The campaign has all its flights in `campaign/evidence/telemetry/campaign.zip`. The PX4 ULog files are not included because of their size. Inside the zips the log messages and test names are in Spanish (`salto` = jump, `deriva` = drift, `corte` = cut); the CSV columns and identifiers are the same as in the code.

Everything is PX4 SITL + Gazebo. Keep apart four things: the reported GPS, the EKF estimate, the real position in the simulator and the detector output. The PX4 geofence is evaluated on the estimated position, so the QGC map alone does not prove containment against a manipulated GPS.
