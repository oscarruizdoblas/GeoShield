#!/usr/bin/env python3
"""GeoShield - generate the Gazebo 3D world (padova.sdf) and the ground model.

  - Ground: a 2 km x 2 km textured quad (OSM texture from make_texture.py) centred on the A-B
    midpoint. The quad is POSED at the midpoint offset so that the drone, which spawns at
    HOME = (0, 0), appears at the right place on the map.
  - Red translucent cylinders: the no-fly zones (Palazzo Bo, Palazzo Liviano), 70 m tall.
  - Grey boxes: simplified buildings around the zones (visual only, no collisions).
  - Markers: green cylinder at A, yellow cylinder at B.
  - <spherical_coordinates>: the world origin is HOME, so the simulated GPS reports real
    Padova coordinates.
All positions come from zones.py, converted to local East/North metres.
"""
import math, os
from pathlib import Path
from zones import HOME, DEST, KEEPOUT

lat0, lon0 = HOME[0], HOME[1]
HALF = 1000.0          # half side of the ground plane (m)
MPLAT = 110540.0
MPLON = 111320.0 * math.cos(math.radians(lat0))
def enu(lat, lon):   # lat/lon -> local (East, North) metres from HOME
    return ((lon-lon0)*MPLON, (lat-lat0)*MPLAT)

latm = (HOME[0]+DEST[0])/2.0; lonm = (HOME[1]+DEST[1])/2.0
em, nm = enu(latm, lonm)          # map centre (A-B midpoint offset)
be, bn = enu(DEST[0], DEST[1])    # destination B

PX4_DIR = Path(os.environ.get("PX4_DIR", Path.home() / "PX4-Autopilot")).expanduser()
MODELS_DIR = Path(os.environ.get("PX4_GZ_MODELS", PX4_DIR / "Tools/simulation/gz/models")).expanduser()
WORLDS_DIR = Path(os.environ.get("PX4_GZ_WORLDS", PX4_DIR / "Tools/simulation/gz/worlds")).expanduser()
MODELDIR = MODELS_DIR / "padova_ground"
WORLD = WORLDS_DIR / "padova.sdf"
MODELDIR.mkdir(parents=True, exist_ok=True)
WORLDS_DIR.mkdir(parents=True, exist_ok=True)

# ---- textured ground (quad of side 2*HALF, UVs: north = +y) ----
obj = """mtllib padova_ground.mtl
v -%d -%d 0
v %d -%d 0
v %d %d 0
v -%d %d 0
vt 0 1
vt 1 1
vt 1 0
vt 0 0
vn 0 0 1
usemtl padova
f 1/1/1 2/2/1 3/3/1
f 1/1/1 3/3/1 4/4/1
""" % (HALF, HALF, HALF, HALF, HALF, HALF, HALF, HALF)
open(os.path.join(MODELDIR, "padova_ground.obj"), "w").write(obj)
open(os.path.join(MODELDIR, "padova_ground.mtl"), "w").write(
    "newmtl padova\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nd 1\nillum 1\nmap_Kd padova_texture.png\n")
Path(MODELDIR, "model.config").write_text("""<?xml version="1.0"?>
<model>
  <name>GeoShield Padova Ground</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>GeoShield</name><email></email></author>
  <description>Textured Padova orthomosaic ground mesh for the GeoShield SITL world.</description>
</model>
""", encoding="utf-8")
Path(MODELDIR, "model.sdf").write_text("""<?xml version="1.0"?>
<sdf version="1.9">
  <model name="padova_ground">
    <static>true</static>
    <link name="link">
      <visual name="visual">
        <geometry><mesh><uri>padova_ground.obj</uri></mesh></geometry>
      </visual>
    </link>
  </model>
</sdf>
""", encoding="utf-8")

# ---- red cylinders (keep-out zones) ----
H = 70.0               # cylinder height (m)
cyl = ""
for i, z in enumerate(KEEPOUT):
    e, n = enu(z['lat'], z['lon'])
    cyl += """
    <model name="keepout_%d"><static>true</static>
      <pose>%.1f %.1f %.1f 0 0 0</pose>
      <link name="link"><visual name="v">
        <geometry><cylinder><radius>%.1f</radius><length>%.1f</length></cylinder></geometry>
        <transparency>0.55</transparency>
        <material><ambient>1 0 0 1</ambient><diffuse>1 0 0 1</diffuse><emissive>0.45 0 0 1</emissive></material>
      </visual></link>
    </model>""" % (i, e, n, H/2.0, z['r'], H)

# ---- markers A (green) and B (yellow) ----
def marker(name, e, n, col):
    return """
    <model name="%s"><static>true</static>
      <pose>%.1f %.1f 30 0 0 0</pose>
      <link name="link"><visual name="v">
        <geometry><cylinder><radius>8</radius><length>60</length></cylinder></geometry>
        <material><ambient>%s</ambient><diffuse>%s</diffuse><emissive>%s</emissive></material>
      </visual></link>
    </model>""" % (name, e, n, col, col, col)
markers = marker("start_A", 0.0, 0.0, "0 1 0 1") + marker("dest_B", be, bn, "1 1 0 1")

# ---- grey buildings around the city-centre zones ----
blds = ""
def cluster(cx, cy, specs, tag):
    # specs: (dx, dy, size_x, size_y, height) of each box relative to the zone centre
    s = ""
    for j, (dx, dy, sx, sy, h) in enumerate(specs):
        s += """
    <model name="bld_%s_%d"><static>true</static>
      <pose>%.1f %.1f %.1f 0 0 0</pose>
      <link name="link"><visual name="v">
        <geometry><box><size>%.1f %.1f %.1f</size></box></geometry>
        <material><ambient>0.55 0.55 0.58 1</ambient><diffuse>0.62 0.62 0.66 1</diffuse></material>
      </visual></link>
    </model>""" % (tag, j, cx+dx, cy+dy, h/2.0, sx, sy, h)
    return s
boe, bon = enu(KEEPOUT[0]['lat'], KEEPOUT[0]['lon'])   # Palazzo Bo
lie, lin = enu(KEEPOUT[1]['lat'], KEEPOUT[1]['lon'])   # Palazzo Liviano
blds += cluster(boe, bon, [(-80, 50, 35, 30, 48), (40, 80, 28, 40, 55), (90, -30, 40, 35, 40),
                           (-50, -80, 30, 30, 32), (15, 0, 45, 45, 60), (85, 100, 25, 25, 28)], "bo")
blds += cluster(lie, lin, [(0, 0, 45, 55, 50), (-60, 30, 30, 30, 30), (55, -35, 35, 28, 35)], "liv")

world = """<?xml version="1.0" encoding="UTF-8"?>
<sdf version="1.9">
  <world name="padova">
    <physics type="ode">
      <max_step_size>0.004</max_step_size>
      <real_time_factor>1.0</real_time_factor>
      <real_time_update_rate>250</real_time_update_rate>
    </physics>
    <gravity>0 0 -9.8</gravity>
    <magnetic_field>6e-06 2.3e-05 -4.2e-05</magnetic_field>
    <atmosphere type="adiabatic"/>
    <scene><grid>false</grid><ambient>0.5 0.5 0.5 1</ambient><background>0.75 0.82 0.9 1</background><shadows>true</shadows></scene>

    <model name="ground_plane"><static>true</static>
      <link name="link">
        <collision name="collision"><geometry><plane><normal>0 0 1</normal><size>1 1</size></plane></geometry>
          <surface><friction><ode/></friction><bounce/><contact/></surface></collision>
      </link>
    </model>

    <model name="padova_map"><static>true</static>
      <pose>%.1f %.1f 0 0 0 0</pose>
      <link name="link"><visual name="visual">
        <geometry><mesh><uri>model://padova_ground/padova_ground.obj</uri></mesh></geometry>
      </visual></link>
    </model>
%s
%s
%s
    <light name="sunUTC" type="directional">
      <pose>0 0 500 0 0 0</pose><cast_shadows>true</cast_shadows><intensity>1</intensity>
      <direction>0.001 0.625 -0.78</direction>
      <diffuse>0.904 0.904 0.904 1</diffuse><specular>0.271 0.271 0.271 1</specular>
      <attenuation><range>2000</range><linear>0</linear><constant>1</constant><quadratic>0</quadratic></attenuation>
      <spot><inner_angle>0</inner_angle><outer_angle>0</outer_angle><falloff>0</falloff></spot>
    </light>
    <spherical_coordinates>
      <surface_model>EARTH_WGS84</surface_model><world_frame_orientation>ENU</world_frame_orientation>
      <latitude_deg>%.7f</latitude_deg><longitude_deg>%.7f</longitude_deg><elevation>12</elevation>
    </spherical_coordinates>
  </world>
</sdf>
""" % (em, nm, cyl, markers, blds, lat0, lon0)
WORLD.write_text(world, encoding="utf-8")
print("world written:", WORLD, flush=True)
print("map posed at ENU (%.0f, %.0f) = A-B midpoint" % (em, nm), flush=True)
print("keep-out:", len(KEEPOUT), " destination B at ENU (%.0f,%.0f)" % (be, bn), flush=True)
