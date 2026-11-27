# Experiment 01 — Normal autonomous flight

## Goal

Establish the baseline without an attack. The X500 in PX4 SITL takes off from A (Riviera Paleocapa), flies to B (Torre Archimede) along the planned route around the no-fly zones, flies back and lands at A.

## Result

- Planned route: 2,010 m one way. The sampled round trip was 4,010 m in 601 s.
- Minimum distance to the centre of Palazzo Bo: 292 m (72 m outside its 220 m radius). To Palazzo Liviano: 546 m (396 m outside its 150 m radius).
- With the detector running and the GPS going through the relay in transparent mode: **0 alerts** during the whole flight, landing 1.1 m from A. This is the false-alarm baseline. The [campaign](../campaign/README.md) repeats it 5 times with the same result.

## Evidence

- **Video 1:** [open in Google Drive](https://drive.google.com/file/d/1tfNl-XtwFbwF7WvPxh80LVK_pFf5RQCq/view?usp=drive_link).
- [Trajectory](evidence/images/normal_flight_map.png) · [detector signals](evidence/images/normal_flight_signals.png).
- Telemetry: `evidence/telemetry/normal_flight.zip` (CSV files of the relay, the detector and the flight).
