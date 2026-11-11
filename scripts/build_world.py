#!/usr/bin/env python3
# GeoShield - mundo 3D de Gazebo para el escenario NUEVO.
# Suelo = textura OSM centrada en el punto medio A-B (cubre salida, centro y destino).
# El plano se POSA en el offset del punto medio para que el dron (spawn en HOME=0,0)
# caiga en el lugar correcto del mapa. Zonas rojas (Bo, Liviano) + edificios + marcadores A/B.
import math, os, sys
sys.path.insert(0, '/home/oruiz/geoshield')
from zones import HOME, DEST, KEEPOUT

lat0, lon0 = HOME[0], HOME[1]
HALF = 1000.0
MPLAT = 110540.0
MPLON = 111320.0 * math.cos(math.radians(lat0))
def enu(lat, lon): return ((lon-lon0)*MPLON, (lat-lat0)*MPLAT)

latm = (HOME[0]+DEST[0])/2.0; lonm = (HOME[1]+DEST[1])/2.0
em, nm = enu(latm, lonm)          # centro del mapa (offset del punto medio)
be, bn = enu(DEST[0], DEST[1])    # destino B

MODELDIR = "/home/oruiz/PX4-Autopilot/Tools/simulation/gz/models/padova_ground"
WORLD = "/home/oruiz/PX4-Autopilot/Tools/simulation/gz/worlds/padova.sdf"

# ---- suelo texturizado (quad de 2*HALF, UVs: norte=+y) ----
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

# ---- cilindros rojos (zonas keep-out) ----
H = 70.0
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

# ---- marcadores A (verde) y B (amarillo) ----
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

# ---- edificios grises alrededor de las zonas del centro ----
blds = ""
def cluster(cx, cy, specs, tag):
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
open(WORLD, "w").write(world)
print("escrito world:", WORLD, flush=True)
print("mapa posado en ENU (%.0f, %.0f) = punto medio A-B" % (em, nm), flush=True)
print("keep-out:", len(KEEPOUT), " destino B en ENU (%.0f,%.0f)" % (be, bn), flush=True)
