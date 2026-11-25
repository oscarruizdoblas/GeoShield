#!/usr/bin/env python3
# GeoShield - DETECTOR de spoofing GPS en vivo (pymavlink, puerto 14540).
# Observa la telemetria y aplica reglas calibradas con el vuelo BASE (sin spoofing).
# Objetivo: 0 falsos positivos en vuelo limpio; pillar spoofing BRUSCO y GRADUAL.
# Uso: python3 detector.py [segundos]   (sin argumento: hasta Ctrl-C)
#
# Senales vigiladas:
#   1) d_gps_ekf : distancia entre GPS crudo (GPS_RAW_INT) y posicion EKF (GLOBAL_POSITION_INT)
#   2) innov_*   : ratios de innovacion del EKF (ESTIMATOR_STATUS); el EKF rechaza a 1.0
#   3) salto     : velocidad aparente entre muestras consecutivas (teletransporte)
import sys, os, time, csv, math
from datetime import datetime
from pymavlink import mavutil

# ---- UMBRALES (base: media/p99/max del vuelo limpio -> margen para 0 FP) ----
DIST_HARD   = 3.0    # m   divergencia GPS-EKF grande      (base max ~1.0)
DIST_WARN   = 1.5    # m   divergencia moderada ...
WARN_SECS   = 3.0    # ... sostenida este tiempo -> deriva GRADUAL (base nunca pasa de 1.0)
INNOV_LIM   = 0.5    #     ratio de innovacion pos/vel     (base max 0.02-0.11; EKF rechaza a 1.0)
JUMP_SPEED  = 15.0   # m/s velocidad aparente entre muestras (base max ~6.4)
COOLDOWN    = 2.0    # s   para no repetir la misma alerta en rafaga

def hav(a, b, c, d):
    R = 6371000.0; p1, p2 = math.radians(a), math.radians(c)
    dp = math.radians(c - a); dl = math.radians(d - b)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

DUR = float(sys.argv[1]) if len(sys.argv) > 1 else None
LOGDIR = os.path.expanduser('~/geoshield/logs/detector_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
os.makedirs(LOGDIR, exist_ok=True)
af = open(os.path.join(LOGDIR, 'alerts.csv'), 'w', newline='')
aw = csv.writer(af); aw.writerow(['t', 'iso', 'regla', 'valor', 'umbral', 'detalle']); af.flush()

last_cool = {}
n_alert = 0
def alerta(regla, valor, umbral, detalle):
    global n_alert
    now = time.time()
    if now - last_cool.get(regla, 0) < COOLDOWN:
        return
    last_cool[regla] = now; n_alert += 1
    iso = datetime.now().strftime('%H:%M:%S')
    print("  ⚠ [%s] ALERTA %-14s valor=%.3f (umbral %.3f)  %s" % (iso, regla, valor, umbral, detalle), flush=True)
    aw.writerow([now, iso, regla, "%.4f" % valor, "%.4f" % umbral, detalle]); af.flush()

m = mavutil.mavlink_connection('udpin:0.0.0.0:14540')
print("DETECTOR GeoShield -> esperando heartbeat en 14540...", flush=True)
if m.wait_heartbeat(timeout=20) is None:
    print("SIN HEARTBEAT (¿PX4 apagado o el 14540 ocupado por otro script?)", flush=True); sys.exit(1)
print("enlace OK. Vigilando. Alertas -> %s" % LOGDIR, flush=True)
print("umbrales: dist_hard=%.1fm  dist_warn=%.1fm/%.0fs  innov=%.2f  salto=%.0fm/s" % (DIST_HARD, DIST_WARN, WARN_SECS, INNOV_LIM, JUMP_SPEED), flush=True)
for mid, us in [(24, 200000), (33, 100000), (230, 200000)]:
    m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, float(mid), float(us), 0, 0, 0, 0, 0); time.sleep(0.1)

last_gps = None   # (t, lat, lon)
last_gp  = None
prev_gps = None
prev_gp  = None
warn_since = None
cur = {'d': 0.0, 'ih': 0.0, 'iv': 0.0}
t0 = time.time(); lp = 0
try:
    while DUR is None or time.time() - t0 < DUR:
        msg = m.recv_match(type=['GPS_RAW_INT', 'GLOBAL_POSITION_INT', 'ESTIMATOR_STATUS'], blocking=True, timeout=1)
        now = time.time()
        if msg is not None:
            ty = msg.get_type()
            if ty == 'GPS_RAW_INT':
                g = (now, msg.lat/1e7, msg.lon/1e7);
                if g[1] != 0.0:
                    if prev_gps:
                        dt = g[0] - prev_gps[0]
                        if dt > 0:
                            sp = hav(prev_gps[1], prev_gps[2], g[1], g[2]) / dt
                            if sp > JUMP_SPEED:
                                alerta('salto_GPS', sp, JUMP_SPEED, 'teletransporte del GPS crudo (%.0f m/s)' % sp)
                    prev_gps = g; last_gps = g
            elif ty == 'GLOBAL_POSITION_INT':
                g = (now, msg.lat/1e7, msg.lon/1e7)
                if prev_gp:
                    dt = g[0] - prev_gp[0]
                    if dt > 0:
                        sp = hav(prev_gp[1], prev_gp[2], g[1], g[2]) / dt
                        if sp > JUMP_SPEED:
                            alerta('salto_EKF', sp, JUMP_SPEED, 'teletransporte de la posicion EKF (%.0f m/s)' % sp)
                prev_gp = g; last_gp = g
            elif ty == 'ESTIMATOR_STATUS':
                cur['ih'] = msg.pos_horiz_ratio; cur['iv'] = msg.vel_ratio
                if msg.pos_horiz_ratio > INNOV_LIM:
                    alerta('innov_pos', msg.pos_horiz_ratio, INNOV_LIM, 'el EKF desconfia de la posicion GPS')
                if msg.vel_ratio > INNOV_LIM:
                    alerta('innov_vel', msg.vel_ratio, INNOV_LIM, 'el EKF desconfia de la velocidad GPS')

        # distancia GPS<->EKF (brusca y gradual)
        if last_gps and last_gp and abs(last_gps[0] - last_gp[0]) < 1.0:
            d = hav(last_gps[1], last_gps[2], last_gp[1], last_gp[2]); cur['d'] = d
            if d > DIST_HARD:
                alerta('div_GPS_EKF', d, DIST_HARD, 'GPS y EKF discrepan %.1f m' % d)
            if d > DIST_WARN:
                if warn_since is None:
                    warn_since = now
                elif now - warn_since >= WARN_SECS:
                    alerta('deriva_gradual', d, DIST_WARN, 'divergencia sostenida %.1fs -> posible spoofing lento' % (now - warn_since))
            else:
                warn_since = None

        if now - lp > 3:
            estado = 'LIMPIO' if n_alert == 0 else ('%d ALERTAS' % n_alert)
            print("  [%s] estado=%-10s d_gps_ekf=%.2fm  innov_pos=%.3f  innov_vel=%.3f" % (datetime.now().strftime('%H:%M:%S'), estado, cur['d'], cur['ih'], cur['iv']), flush=True)
            lp = now
except KeyboardInterrupt:
    print("\nparando detector...", flush=True)
finally:
    af.close()
    print("FIN. Alertas totales: %d  (registro: %s)" % (n_alert, os.path.join(LOGDIR, 'alerts.csv')), flush=True)
