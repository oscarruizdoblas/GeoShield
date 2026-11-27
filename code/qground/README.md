# QGroundControl mission

Open [`geoshield_padova.plan`](geoshield_padova.plan) in QGroundControl with **Plan → Open**. It contains the geofence (the keep-in circle and the two no-fly circles) and the normal mission from A to B around Palazzo Bo.

The coordinates come from [`../python/zones.py`](../python/zones.py). To regenerate the plan, run `python3 code/python/make_qgc_plan.py` from the repository root and check the result visually before loading it.
