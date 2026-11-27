# Demo tools

Used only to record the videos; they play no part in the measurements.

| File | Role |
|---|---|
| `prepare_demo.sh [SCALE]` | Opens everything ready to record: SITL with interceptable GPS, relay, Gazebo with only the 3D view, QGC, geofence and the detector panel. It does not start a flight. |
| `detector_panel.py` | Live panel with the detector state (NORMAL/ALERT, signals against thresholds, defence steps). |
| `real_pos_qgc.py` | Sends the real Gazebo position to QGC as vehicle 2, so both where the drone thinks it is and where it really is are visible. |
| `scale_drone.py` | Draws the X500 bigger in Gazebo (`DEMO_SCALE=40`); physics and sensors are unchanged. |
| `cam.sh demo\|oblique\|top\|close` | Gazebo camera positions. |
| `run_gui_video.sh`, `gui_video.config` | Gazebo window without side panels. |

Usage, after `bash code/sync_wsl.sh`:

```bash
bash ~/geoshield/prepare_demo.sh
SHOW=1 bash ~/geoshield/run_attack_test.sh video_drift drift no --verbose   # in a visible terminal
```

`real_pos_qgc.py` and `scale_drone.py` use the system Python (gz-transport).
