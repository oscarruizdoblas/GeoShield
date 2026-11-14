# Experiment 01 — Normal Autonomous Flight

This folder contains the reviewable evidence and short run notes for GeoShield's normal Padova baseline flight.

## Run summary

- **Vehicle:** PX4 SITL X500 in Gazebo Harmonic / Sim 8.
- **Home / start:** A, Riviera Paleocapa (`45.4021, 11.8670`).
- **Destination:** B, Torre Archimede (`45.4113328, 11.8878209`).
- **Route:** planner-generated path around Palazzo Bo and Palazzo Liviano; 7 route nodes counting A, 6 commanded waypoints each direction.
- **Outcome:** takeoff, A→B, reverse route, RTL, and landing at A. No GPS attack was run.
- **Telemetry:** 4,010 m sampled round trip over 601.1 s; minimum sampled clearances were 72.1 m beyond Bo's boundary and 395.9 m beyond Liviano's boundary. These are calculated from CSV samples, not continuous geofence enforcement measurements.

## Folder contents

- [`evidence/README.md`](evidence/README.md) — Drive link to the video; the MP4 itself is not stored in Git.
- The CSV files and PX4 ULog remain in the WSL locations listed in the main [Experiment 01 report](../../../docs/experiments/EXP-01_NORMAL_AUTONOMOUS_FLIGHT.md); they were not copied into this folder.

The recording shows QGroundControl and Gazebo Sim together. In a reviewed frame at 05:00, QGC shows the Padova mission map, but the X500 is not clearly identifiable in Gazebo's 3D viewport. The video therefore does not prove continuous 3D tracking or exact GPS/EKF synchronization. The Gazebo runtime `FOLLOW` topic was separately confirmed for `x500_0`.

## Reproduce

From WSL, after starting PX4/Gazebo Padova and confirming QGC connection and PX4 preflight:

```bash
cd ~/geoshield
python3 plan_and_fly.py
```

The script plans around the keep-out zones defined in [`scripts/zones.py`](../../../scripts/zones.py), flies the route out and back, and writes CSV telemetry under `~/geoshield/logs/`. Do not run another consumer of UDP 14540 at the same time.

## Validation still pending

- Verify PX4 geofence parameters and breach/event state from the successful run's ULog.
- Analyze the raw GPS, EKF, and estimator-status CSVs with the offline analysis workflow.
- Re-record with the X500 clearly visible in Gazebo for the whole flight.
- Verify that the Drive link is available to the intended collaborators; the large MP4 is hosted externally.

See the [full technical report](../../../docs/experiments/EXP-01_NORMAL_AUTONOMOUS_FLIGHT.md) for architecture, measured metrics, evidence limits, and experiment roadmap.
