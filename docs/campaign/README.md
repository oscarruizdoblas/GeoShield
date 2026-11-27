# Repetition campaign — 27 flights

## Goal

Check that the results of Experiments 01–05 repeat and do not come from a single lucky run. We measure:

- the false-alarm rate without an attack;
- the mean detection delay and its spread;
- the missed detections (false negatives);
- the slowest drift the detector can still see.

## Setup

- Same scenario and route as the experiments: A → B → A in Padova, with Palazzo Bo (r = 220 m) and Palazzo Liviano (r = 150 m) as no-fly zones.
- The attack starts 400 m from A and moves the GPS up to 180 m (E 90, N −156) towards Palazzo Bo.
- Every attack flight runs the full defence: HOLD → warning → GPS cut → return to the trusted point.
- Every flight starts from a freshly restarted simulator. The parameters are set before each flight:

  | Parameter | Value |
  |---|---|
  | `GF_ACTION` | 3 |
  | `EKF2_GPS_CTRL` | 7 |
  | `EKF2_NOAID_TOUT` | 5 s |

- Scenarios are interleaved by rounds, so none benefits from the order.

| Scenario | Flights | Attack |
|---|---:|---|
| Normal flight | 5 | none |
| Jump 180 m | 5 | instantaneous jump |
| Drift 3 m/s | 5 | drift with consistent GPS velocity, 4 s ramp |
| Drift 2 m/s | 3 | same, at 2 m/s |
| Drift 1 m/s | 3 | same, at 1 m/s |
| Drift 0.5 m/s | 3 | same, at 0.5 m/s |
| Drift 1 m/s, no velocity | 3 | only the position moves; the GPS velocity stays the true one |

The delay is measured in simulation time, from the first forged GPS sample to the first alert. Only alerts raised while the attack is active count. When the attacker stops, the GPS snaps back to the true position and `salto_GPS` fires, but that detects the end of the attack, not the attack.

To reproduce the campaign and its evaluation:

```bash
bash ~/geoshield/run_campaign.sh campaign
python3 ~/geoshield/evaluate_campaign.py campaign
```

The full campaign took 3 h 25 min of unattended simulation.

## Results

| Scenario | n | False alarms | Detected | Mean delay ± std | Range | GPS offset at detection | First rule | Enters Palazzo Bo |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| Normal flight | 5 | 0 (0 alerts in 54 min) | — | — | — | — | — | 0/5 |
| Jump 180 m | 5 | 0 | 5/5 | 0.12 ± 0.05 s | 0.06–0.17 s | 180 m | `salto_GPS` ×4, `innov_pos` ×1 | 0/5 |
| Drift 3 m/s | 5 | 0 | 5/5 | 2.21 ± 0.13 s | 2.03–2.34 s | 1.9 m | `innov_sostenida` ×5 | 0/5 |
| Drift 2 m/s | 3 | 0 | 3/3 | 2.97 ± 0.19 s | 2.77–3.14 s | 2.3 m | `innov_sostenida` ×3 | 0/3 |
| Drift 1 m/s | 3 | 0 | **0/3** | — | — | — | — | **3/3** |
| Drift 0.5 m/s | 3 | 0 | **0/3** | — | — | — | — | 0/3 |
| Drift 1 m/s, no velocity | 3 | 0 | 3/3 | 7.70 ± 0.06 s | 7.66–7.77 s | 5.8 m | `deriva_gradual` ×3 | 0/3 |

In total there were 27 flights:
- 0 false alarms in the 5 normal flights;
- 19 of 22 attacks detected while active;
- 6 missed detections, all coherent drifts at ≤ 1 m/s.

| Scenario | Max. real error (EKF − real) | Minimum distance to the centre of Palazzo Bo |
|---|---:|---:|
| Jump | 4.0–6.1 m | 583–584 m |
| Drift 3 m/s | 67–92 m | 569–572 m |
| Drift 2 m/s | 79–97 m | 564–566 m |
| Drift 1 m/s, no velocity | 9.5–11.7 m | ≈ 537 m |
| Drift 1 m/s (not detected) | 180 m | 202.8–202.9 m: the real drone enters the zone by about 17 m |
| Drift 0.5 m/s (not detected) | 113 m | 246.6–246.7 m: the offset is not enough to push it in before the leg ends |

Every detected flight completed the defence sequence and landed 1.0–1.1 m from A.

## Discussion

- **No false alarms:** 54 min of normal flight without a single alert. The thresholds do not fire on normal GPS or EKF noise.
- **The jump is always detected, almost instantly** (≈ 0.1 s). The GPS cut arrives before the EKF accepts the fake position, so the real error stays at about 5 m.
- **A coherent drift is detected through the EKF velocity innovation at its start** (`innov_sostenida`). The slower the drift, the longer it takes: 2.2 s at 3 m/s and 3.0 s at 2 m/s. In both cases the GPS has moved only about 2 m when it is detected.
- **Even so, detection comes late for the drift.** In those 2–3 s the EKF has already absorbed part of the fake velocity, and the maximum real error is still 70–95 m, although the drone does not enter the zone.
- **Detector limit: a coherent drift at 1 m/s or less is not detected.** With a 4 s ramp the fake acceleration is 0.25 m/s² or less, and the EKF follows the GPS without disagreeing. At 1 m/s the attacker takes the real drone about 17 m into Palazzo Bo in all three repetitions, and PX4 does not notice. The system only reacts when the attacker stops and the GPS snaps back.

  Lowering the thresholds does not fix it. During these attacks the signals stay below the peaks of a normal flight:

  | Signal (maximum) | Drift 1 m/s | Drift 0.5 m/s | Normal flight | Threshold |
  |---|---:|---:|---:|---:|
  | Velocity innovation | 0.10 | 0.06 | 0.11–0.12 | 0.15 |
  | GPS–EKF divergence | 0.86 m | 0.83 m | 0.84–0.90 m | 3 m (1.5 m sustained) |

  With these signals the attack is indistinguishable from normal noise.
- **If the attacker does not also forge the velocity, the slow drift is visible:** the `deriva_gradual` rule detects it at 1 m/s in 7.7 s, with a 5.8 m offset. The attacker therefore has to forge position and velocity consistently, and also go slowly.
- **Reproducibility:** the standard deviations are 0.05–0.19 s. The means match the single runs of Experiments 02–05: jump 0.03–0.14 s and drift 2.1–2.4 s.

**Conclusion:** the defence works against jumps and fast drifts. Against a slow, coherent drift (below about 1–2 m/s) an independent position source is needed, such as visual odometry, optical flow, airspeed or a second antenna. Comparing the GPS with the EKF itself is not enough, because the EKF is fed by the GPS.

## Evidence

- [Delay per scenario](evidence/images/delay_by_scenario.png): one dot per flight; undetected scenarios in red.
- [Detection versus drift speed](evidence/images/detection_vs_drift_speed.png).
- [`flights.csv`](evidence/data/flights.csv): one row per flight. [`summary.csv`](evidence/data/summary.csv): one row per scenario.
- `evidence/telemetry/campaign.zip`: the raw CSV files and logs of the 27 flights, one folder per flight (`<scenario>_r<repetition>`).

Notes on `flights.csv`:
- `flight_min`: in attack flights, it counts only until 5 s after the attack ends.
- `alert_when_attack_stopped`: the rule that fired when the GPS returned to the true position, in the undetected flights.
