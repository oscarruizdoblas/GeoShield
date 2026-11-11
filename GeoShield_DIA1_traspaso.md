# GeoShield — Traspaso del Día 1 (para continuar en el Día 2)

## Qué es el proyecto
**GeoShield** — proyecto universitario (asignatura *Cyberphysical and IoT Security*). En **SIMULACIÓN** (sin hardware ni radio real) estudia **GPS spoofing** (soft/hard, inspirado en el paper "Tractor Beam") contra un dron autónomo, y construye **detección + defensa** (geofencing resiliente). NUNCA se transmite GPS real: todo es manipulación de datos de navegación dentro del simulador. Objetivo crítico: **verificar que el GPS manipulado llega de verdad a la navegación de PX4**, no solo que cambia la vista en QGC.

Equipo (2): **Ignacio** (simulación PX4/Gazebo, MAVLink, módulo de ataque GPS) y **Oscar** (QGroundControl + geofencing, detector de anomalías, defensa, gráficas y docs). Plan de 7 días; Día 1 = 2026-11-02/03.

## Entorno (Día 1 — HECHO y verificado)
- Windows 11 + WSL2 (WSL **3.0.3**, con **WSLg** para GUI). Distro usada: **`Ubuntu`** (usuario `oruiz`), Ubuntu 24.04. (Existe otra distro `Ubuntu-24.04`/usuario `oscar` que **NO** se usa.)
- **PX4** en `~/PX4-Autopilot` (clon superficial de `main`, commit dc918f99; sin tags → versión v0.0.0). Compilado en `build/px4_sitl_default`. Airframe: **4001_gz_x500**.
- **Gazebo Harmonic** (gz sim 8.15.0).
- **Python** = Anaconda base `/home/oruiz/yes` (pymavlink 2.4.50, matplotlib 3.11.2, mavsdk 4.1.0, numpy, pandas).
- **QGroundControl v5.1** AppImage en `~/QGC/QGroundControl.AppImage`.

## Cómo arrancar todo (workflow reproducible)
1. **Simulador** — SIEMPRE headless en WSL (si no, se rompe el lockstep):
   ```
   cd ~/PX4-Autopilot && HEADLESS=1 make px4_sitl gz_x500
   ```
2. **QGroundControl** (en otra terminal WSL):
   ```
   cd ~/QGC && ./QGroundControl.AppImage --appimage-extract-and-run
   ```
   Conecta solo por localhost (udp 14550). Cuando PX4 diga `Ready for takeoff!`, en QGC: **Takeoff → deslizar**. Para aterrizar: **Land → deslizar**.

## Gotchas de WSL resueltos (IMPORTANTE — no repetir)
1. **DNS roto por la VPN de Padua** → `/etc/resolv.conf` fijado a 8.8.8.8 / 1.1.1.1 + `/etc/wsl.conf` con `[network] generateResolvConf = false`. Backup: `/etc/resolv.conf.geoshield.bak`.
2. **`/usr/bin/perf` es un bind-mount de solo lectura de WSL** → rompe la instalación de `linux-tools-common` (dep de PX4) con "Invalid cross-device link". Fix permanente: `/etc/dpkg/dpkg.cfg.d/90-geoshield-exclude-perf` con `path-exclude=/usr/bin/perf`.
3. **Gazebo con ventana (GUI) rompe el lockstep PX4↔Gazebo en WSL**: avalancha de `vehicle_imu timestamp error` + `NodeShared::Publish() Interrupted system call`, el EKF no converge y el armado se deniega ("Resolve system health failures first"). → Usar **`HEADLESS=1`** y visualizar por QGC.
4. **Armar/despegar exige un GCS (o RC) conectado** ("Preflight Fail: No connection to the GCS"). QGC conectado lo satisface → aparece `Ready for takeoff!`.

## Estado al cierre del Día 1
- **Vuelo normal del X500 CONSEGUIDO**: QGC armó y despegó (`Armed by external command` + `Takeoff detected`), voló estable ~3 m en modo Hold.
- **Home por defecto del SITL = Zúrich** (47.3977, 8.5456). Para GeoShield se cambiará a **Padua**.
- El modelo X500 tiene **2 GPS** (`GPS[0]`, `GPS[1]`) y el EKF publica *innovations* → base del detector de spoofing.

## Puertos MAVLink
- **14550** = GCS/QGC · **14540** = offboard/MAVSDK. PX4 avisa "MAVLink only on localhost".
- Script de prueba de control por MAVLink (pymavlink como GCS): `~/gcs_fly.py`.

## Día 2 — propuesta (parte de Oscar)
- **Geofencing**: definir polígono/área (coordenadas reales de Padua) en QGC y/o params PX4 (`GF_*`).
- **Mapa de Padua**: matplotlib + imagen de OpenStreetMap + coordenadas GPS reales (NO modelo 3D).
- **Esqueleto del detector**: leer por MAVLink (pymavlink) GPS vs estimación del EKF (*innovations*, p.ej. mensajes `ESTIMATOR_*`), de modo que un spoofing gradual no dispare el EKF pero sí el detector propio.
- **Cambiar el home del SITL a Padua** (vars `PX4_HOME_LAT`/`PX4_HOME_LON`/`PX4_HOME_ALT` al lanzar, o params).
