# Getting started

Everything runs in WSL2 (Ubuntu) with PX4-Autopilot and Gazebo installed. SITL only: no hardware or radio is used.

## QGroundControl

Use **Plan → Open** with `code/qground/geoshield_padova.plan`. The coordinates come from `code/python/zones.py`. If they change, regenerate the `.plan` (`make_qgc_plan.py`) and the world (`build_world.py`).

## Working folder in WSL

The experiment launchers work in `~/geoshield`, where `logs/`, `run/` and `results/` are written. From the repository root, inside WSL:

```bash
bash code/sync_wsl.sh                       # copies code/ to ~/geoshield, installs the world in PX4, checks it compiles
bash ~/geoshield/install_px4_mavlink.sh     # once: PX4 also sends to 14541 (detector); restart the SITL afterwards
```

Two Pythons are needed:
- one with `pymavlink`, for the flight, the detector and the analysis;
- the system one, `/usr/bin/python3`, with `python3-gz-transport13`, for the spoofing relay and the demo tools.

## Experiments

The SITL must be started with `run_padova_spoof.sh`, and the relay must be running (without it PX4 has no GPS):

```bash
sleep infinity | bash ~/geoshield/run_padova_spoof.sh > ~/sitl.log 2>&1 &
/usr/bin/python3 ~/geoshield/spoof_relay.py --mode none &
python3 ~/geoshield/upload_fence.py
bash ~/geoshield/run_attack_test.sh jump_gps_cut jump corte     # MODE none|jump|drift, RESPONSE no|si|corte
python3 ~/geoshield/analyze_attack.py ~/geoshield/logs/<test>  # maps and signal plots
```

Each test leaves its CSV files in `~/geoshield/logs/<date>_<name>/`.

## Demo and video

See [`code/demo/`](../code/demo/README.md).

## Repetition campaign

```bash
bash ~/geoshield/run_campaign.sh campaign      # 27 flights in a row, no windows (about 3.5 h)
python3 ~/geoshield/evaluate_campaign.py campaign  # tables and figures in ~/geoshield/results/campaign/
```
