# Gazebo and PX4 SITL launchers

- `run_padova.sh`: starts PX4 SITL with HOME at A and the Padova world (GPS straight to PX4, no attack possible).
- `run_gui.sh`: opens the Gazebo window (software rendering, stable on WSLg).
- `gz_env.sh`: shows the Gazebo server process, its environment and topics.

The experiment launchers are in `code/python/launchers/` and the recording tools in `code/demo/`. All of them are copied to `~/geoshield` with `code/sync_wsl.sh`.
