"""GeoShield - SINGLE definition of the scenario.

Imported by the route planner, the geofence uploader, the QGroundControl plan generator,
the Gazebo world builder, the attack relay, the detector's return logic and the analysis
scripts, so every component uses exactly the same coordinates.

Real coordinates in Padova (checked against OpenStreetMap / Nominatim).
Mission: take off at A (San Giuseppe, Riviera Paleocapa) and fly to B (Torre Archimede,
Department of Mathematics "Tullio Levi-Civita"). The straight line A->B crosses the
no-fly zone of Palazzo Bo (historic university building), so in a NORMAL flight the drone
must go around it along the shortest safe path.
"""

# Take-off point (A); it is also the simulator spawn point / PX4 HOME
START = (45.4021, 11.8670)        # San Giuseppe / Riviera Paleocapa (SW Padova)
HOME  = START

# Destination (B)
DEST  = (45.4113328, 11.8878209)  # Torre Archimede - Dept. of Mathematics "Tullio Levi-Civita"

# No-fly (keep-out) circles: centre (lat, lon) and radius r in metres
KEEPOUT = [
    {"name": "Palazzo Bo (Universita, centro)",   "lat": 45.4067383, "lon": 11.8773940, "r": 220},
    {"name": "Palazzo Liviano (Universita, centro)", "lat": 45.4079860, "lon": 11.8714491, "r": 150},
]

# Allowed operating area (keep-in circle) containing A, B and both zones
KEEPIN = {"name": "Area operativa Padova", "lat": 45.40672, "lon": 11.87741, "r": 1500}

# Human-readable names of A and B (maps and labels)
START_NAME = "A - Riviera Paleocapa (San Giuseppe)"
DEST_NAME  = "B - Torre Archimede (Mathematics)"
