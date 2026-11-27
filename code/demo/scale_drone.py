#!/usr/bin/env python3
"""GeoShield - enlarge ONLY THE APPEARANCE of the drone in Gazebo (for recording the demo).

    python3 scale_drone.py model.sdf 40

Scales the x500 visual meshes and their positions. Masses, inertias, collisions and sensors are
untouched: physics and flight are identical, only the drawing changes (at real size the drone is
invisible at map scale). The propellers are drawn fixed on the body (if they spun at that scale
they would orbit their real axis, which is 17 cm from the centre).
run_padova_spoof.sh applies it to its copy of the model when started with DEMO_SCALE=<factor>.
"""
import sys, copy
import xml.etree.ElementTree as ET

path, S = sys.argv[1], float(sys.argv[2])
tree = ET.parse(path); root = tree.getroot()

def nums(t): return [float(x) for x in t.split()]
def fmt(v): return ' '.join('%.6g' % x for x in v)
def pose_of(el):
    p = el.find('pose'); return nums(p.text) if p is not None and p.text else [0.0] * 6

base = next(l for l in root.iter('link') if l.get('name') == 'base_link')
for v in list(base.findall('visual')):
    mesh = v.find('geometry/mesh')
    if mesh is None:                       # electronics boards (small boxes): removed
        base.remove(v); continue
    sc = mesh.find('scale'); s0 = nums(sc.text) if sc is not None else [1, 1, 1]
    if sc is None: sc = ET.SubElement(mesh, 'scale')
    sc.text = fmt([x * S for x in s0])
    p = pose_of(v); p[:3] = [x * S for x in p[:3]]
    pe = v.find('pose')
    if pe is None: pe = ET.SubElement(v, 'pose')
    pe.text = fmt(p)

# rotor visuals: copied into base_link as static scaled meshes
for l in list(root.iter('link')):
    if not (l.get('name') or '').startswith('rotor_'): continue
    lp = pose_of(l)
    for v in list(l.findall('visual')):
        mesh = v.find('geometry/mesh')
        if mesh is None: l.remove(v); continue
        nv = copy.deepcopy(v); nv.set('name', 'demo_' + v.get('name'))
        sc = nv.find('geometry/mesh/scale'); s0 = nums(sc.text) if sc is not None else [1, 1, 1]
        if sc is None: sc = ET.SubElement(nv.find('geometry/mesh'), 'scale')
        sc.text = fmt([x * S for x in s0])
        vp = pose_of(v)
        p = [(lp[i] + vp[i]) * S for i in range(3)] + vp[3:]
        pe = nv.find('pose')
        if pe is None: pe = ET.SubElement(nv, 'pose')
        pe.text = fmt(p)
        base.append(nv); l.remove(v)

tree.write(path)
print("drone drawn at scale x%g (visual only)" % S)
