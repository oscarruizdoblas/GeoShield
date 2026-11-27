#!/usr/bin/python3
"""GeoShield - GPS SPOOFING RELAY (simulation only: no radio, no real GPS signal is involved).

Where it sits
-------------
The Gazebo NavSat (GPS) sensor of the X500 is remapped (see run_padova_spoof.sh) so that it
publishes on /geoshield/navsat_true instead of the topic PX4 reads. This relay subscribes to
that topic and republishes every message on the topic PX4 listens to:

    Gazebo NavSat --/geoshield/navsat_true--> [this relay] --PX4 GPS topic--> PX4 EKF2

In 'none' mode it is fully transparent. During an attack it adds a false offset to the GPS
fix. PX4's EKF fuses the forged fix, believes the drone is somewhere else, and the position
controller "corrects" the error, so the REAL drone is steered away from its route
(this is not just a display artefact in QGroundControl).

Attack models
-------------
  --mode none                 transparent pass-through (used between tests)
  --mode jump                 the full offset (E, N) is applied instantly
  --mode drift [--rate R]     the offset grows at R m/s with a smooth start (--ramp seconds),
                              constant speed and a smooth stop at the final offset.
                              By default the reported GPS velocity is also shifted by the
                              drift velocity, so position and velocity stay consistent
                              (stealthier). --no-vel forges the position only.

The offset (E, N) in metres is that of the FAKE fix relative to the true one. The drone thinks
it is at (true + offset), so while following its route it physically moves the opposite way.
The default offset (E=+90, N=-156, 180 m) pushes the real drone towards Palazzo Bo.

The attack starts when the REAL drone is more than --trigger-dist metres from HOME and stops
(back to transparent) as soon as the file ~/geoshield/run/ATTACK_STOP appears.

Outputs relay.csv: true fix, forged fix, offset and an 'attack' flag for every GPS message.
Runs with the system Python (/usr/bin/python3) because it needs python3-gz-transport13.
"""
import sys, os, time, math, csv, argparse, threading
from datetime import datetime
from gz.transport13 import Node
from gz.msgs10.navsat_pb2 import NavSat
from zones import HOME

ap = argparse.ArgumentParser(description='GeoShield in-simulation GPS spoofing relay')
ap.add_argument('--mode', choices=['none', 'jump', 'drift'], default='none')
ap.add_argument('--east', type=float, default=90.0, help='final East offset of the fake GPS (m)')
ap.add_argument('--north', type=float, default=-156.0, help='final North offset of the fake GPS (m)')
ap.add_argument('--rate', type=float, default=3.0, help='drift speed (m/s), drift mode only')
ap.add_argument('--ramp', type=float, default=4.0, help='seconds of smooth acceleration at the start of the drift')
ap.add_argument('--no-vel', action='store_true', help='drift the position only (GPS velocity left untouched)')
ap.add_argument('--trigger-dist', type=float, default=400.0, help='true distance from HOME that triggers the attack (m)')
ap.add_argument('--world', default='padova')
ap.add_argument('--model', default='x500_0')
ap.add_argument('--logdir', default=None)
ap.add_argument('--verbose', action='store_true', help='print true GPS, forged GPS and offset every second (for the demo)')
a = ap.parse_args()

# Control files shared with the test launcher (run_attack_test.sh)
RUN = os.path.expanduser('~/geoshield/run'); os.makedirs(RUN, exist_ok=True)
STOP_FLAG = os.path.join(RUN, 'ATTACK_STOP')     # created by the launcher to end the attack
START_FILE = os.path.join(RUN, 'attack_start')   # written here when the attack begins
for f in (STOP_FLAG, START_FILE):
    if os.path.exists(f): os.remove(f)
LOGDIR = a.logdir or os.path.expanduser('~/geoshield/logs/relay_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + a.mode)
os.makedirs(LOGDIR, exist_ok=True)
lf = open(os.path.join(LOGDIR, 'relay.csv'), 'w', newline='')
lw = csv.writer(lf)
# t: wall clock, t_sim: simulation time stamp of the GPS message, off_e/off_n: applied offset (m)
lw.writerow(['t', 't_sim', 'true_lat', 'true_lon', 'alt', 'spoof_lat', 'spoof_lon', 'off_e', 'off_n', 'attack'])

TOPIC_IN = '/geoshield/navsat_true'
TOPIC_OUT = '/world/%s/model/%s/link/base_link/sensor/navsat_sensor/navsat' % (a.world, a.model)
M_PER_DEG = 111194.93                      # metres per degree of latitude (R = 6371 km)
D = math.hypot(a.east, a.north)            # magnitude of the final offset
UE, UN = ((a.east / D, a.north / D) if D > 0 else (0.0, 0.0))   # unit vector of the offset

def dist_home(lat, lon):
    """Flat-earth distance (m) from HOME; accurate enough over a few km."""
    dn = (lat - HOME[0]) * M_PER_DEG
    de = (lon - HOME[1]) * M_PER_DEG * math.cos(math.radians(HOME[0]))
    return math.hypot(de, dn)

# Relay state: s = current offset magnitude (m), v = current drift speed (m/s)
st = {'n': 0, 'active': False, 'stopped': False, 's': 0.0, 'v': 0.0, 't_prev': None,
      't_att': None, 'flush': 0.0, 'dist': 0.0, 'lat': 0.0, 'lon': 0.0}
lock = threading.Lock()
node = Node()
pub = node.advertise(TOPIC_OUT, NavSat)

def cb(msg):
    """Called for every true GPS message: decide the offset, forge the fix, publish it to PX4."""
    with lock:
        now = time.time()
        t_sim = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        lat, lon = msg.latitude_deg, msg.longitude_deg
        st['n'] += 1; st['lat'] = lat; st['lon'] = lon
        st['dist'] = dist_home(lat, lon)
        dt = 0.0 if st['t_prev'] is None else max(0.0, min(0.5, t_sim - st['t_prev']))
        st['t_prev'] = t_sim

        # End of the attack requested by the launcher: the GPS becomes true again (in one step)
        if st['active'] and os.path.exists(STOP_FLAG):
            st['active'] = False; st['stopped'] = True; st['s'] = 0.0; st['v'] = 0.0
            print("[relay] ATTACK STOPPED (GPS is true again)", flush=True)
        # Trigger: the real drone has flown far enough from HOME
        if a.mode != 'none' and not st['active'] and not st['stopped'] and st['dist'] > a.trigger_dist:
            st['active'] = True; st['t_att'] = now
            with open(START_FILE, 'w') as f: f.write("%.3f %s\n" % (now, a.mode))
            print("[relay] >>> %s ATTACK STARTED %.0f m from HOME (target offset E=%.0f N=%.0f m)" % (a.mode.upper(), st['dist'], a.east, a.north), flush=True)

        ve = vn = 0.0
        if st['active']:
            if a.mode == 'jump':
                st['s'] = D
            else:
                # drift: speed limited by (1) the cruise rate, (2) a linear ramp-up, and
                # (3) a braking profile sqrt(2*a*remaining) so it stops smoothly at D
                age = now - st['t_att']
                acc = a.rate / max(a.ramp, 1e-3)
                rem = D - st['s']
                if rem <= 0.02:
                    st['v'] = 0.0; st['s'] = D
                else:
                    st['v'] = min(a.rate, acc * age, max(0.05, math.sqrt(2.0 * acc * rem)))
                    st['s'] = min(D, st['s'] + st['v'] * dt)
                if not a.no_vel:
                    # coherent velocity: the GPS velocity agrees with the moving fake position,
                    # so the EKF sees no position/velocity inconsistency
                    ve, vn = UE * st['v'], UN * st['v']
        off_e, off_n = UE * st['s'], UN * st['s']

        # Forge the message: copy the true one and shift position (and velocity)
        out = NavSat(); out.CopyFrom(msg)
        out.latitude_deg = lat + off_n / M_PER_DEG
        out.longitude_deg = lon + off_e / (M_PER_DEG * math.cos(math.radians(lat)))
        out.velocity_east = msg.velocity_east + ve
        out.velocity_north = msg.velocity_north + vn
        pub.publish(out)
        st['slat'], st['slon'] = out.latitude_deg, out.longitude_deg

        lw.writerow(["%.3f" % now, "%.3f" % t_sim, "%.7f" % lat, "%.7f" % lon, "%.2f" % msg.altitude,
                     "%.7f" % out.latitude_deg, "%.7f" % out.longitude_deg, "%.2f" % off_e, "%.2f" % off_n, int(st['active'])])
        if now - st['flush'] > 1.0:
            lf.flush(); st['flush'] = now

if not node.subscribe(NavSat, TOPIC_IN, cb):
    print("[relay] ERROR: cannot subscribe to %s" % TOPIC_IN, flush=True); sys.exit(1)
print("[relay] %s -> %s" % (TOPIC_IN, TOPIC_OUT), flush=True)
print("[relay] mode=%s  log=%s" % (a.mode, LOGDIR), flush=True)
try:
    # Main thread only prints status; the work happens in the subscription callback
    last_n = 0
    period = 1.0 if a.verbose else 5.0
    if a.verbose and a.mode != 'none':
        print("[relay] %s attack ARMED: it starts when the drone is %.0f m from A" % (a.mode.upper(), a.trigger_dist), flush=True)
        print("[relay] target: shift the GPS %.0f m (E=%.0f, N=%.0f)%s" % (D, a.east, a.north,
              (", at %.1f m/s, with coherent velocity" % a.rate) if a.mode == 'drift' and not a.no_vel else ""), flush=True)
    while True:
        time.sleep(period)
        with lock:
            rate = (st['n'] - last_n) / period; last_n = st['n']
            if not a.verbose:
                print("[relay] %4.1f Hz  dist_home=%.0f m  attack=%s  offset=%.1f m" % (rate, st['dist'], 'YES' if st['active'] else 'no', st['s']), flush=True)
            elif st['active']:
                print("[relay] ATTACK  true GPS %.6f, %.6f  ->  sent to PX4 %.6f, %.6f   offset %5.1f m  (%.1f m/s)" % (
                    st['lat'], st['lon'], st.get('slat', 0), st.get('slon', 0), st['s'], st['v'] if a.mode == 'drift' else 0.0), flush=True)
            elif not st['stopped'] and a.mode != 'none':
                print("[relay] armed: drone is %4.0f m from A (starts at %.0f m); GPS untouched" % (st['dist'], a.trigger_dist), flush=True)
except KeyboardInterrupt:
    pass
finally:
    lf.close()
