#!/usr/bin/env python3
"""GeoShield - live detector panel (a window for the demo videos).

    python3 detector_panel.py            -> always follows the most recent test in ~/geoshield/logs/
    python3 detector_panel.py --logdir D -> follows one specific test

It only READS the CSV files written by detector.py (signals/alerts/response) and spoof_relay.py
(relay); it opens no MAVLink link, so it can be opened and closed at any time.
Shows: NORMAL/ALERT banner, first rule and detection delay, current signals as bars against
their thresholds, the forged GPS offset (known only to the simulator), the response steps and
the latest alerts.
Needs tkinter (included in the conda Python; for the system one: sudo apt install python3-tk).
"""
import argparse, csv, glob, os, time
import tkinter as tk

ap = argparse.ArgumentParser()
ap.add_argument('--logdir', default=None)
ap.add_argument('--logs', default=os.path.expanduser('~/geoshield/logs'))
a = ap.parse_args()

# Thresholds (the same as detector.py)
DIST_HARD, INNOV_LIM, INNOV_SOFT = 3.0, 0.5, 0.15

VERDE, ROJO, GRIS, AMBAR = '#1b8a3a', '#c62828', '#555555', '#b26a00'
BG, FG, TENUE = '#14171c', '#e8eaed', '#9aa0a6'


class Tail:
    """Read the new rows of a CSV file that another process is still writing."""
    def __init__(self, path):
        self.path, self.pos, self.header, self.rest = path, 0, None, ''

    def read(self):
        rows = []
        try:
            with open(self.path, newline='') as f:
                f.seek(self.pos); data = f.read(); self.pos = f.tell()
        except OSError:
            return rows
        data = self.rest + data
        lines = data.split('\n'); self.rest = lines.pop()      # the last line may be incomplete
        for r in csv.reader(l for l in lines if l.strip()):
            if self.header is None: self.header = r; continue
            if len(r) == len(self.header): rows.append(dict(zip(self.header, r)))
        return rows


def newest():
    """Folder of the test to follow: --logdir, or the newest folder containing test.txt."""
    if a.logdir: return a.logdir
    ds = [d for d in glob.glob(os.path.join(a.logs, '*')) if os.path.isfile(os.path.join(d, 'test.txt'))]
    return max(ds, key=os.path.getmtime) if ds else None


class Panel:
    def __init__(self, root):
        self.root = root
        root.title('GeoShield - detector'); root.configure(bg=BG); root.geometry('560x640')
        self.titulo = tk.Label(root, text='GeoShield - spoofing detector', bg=BG, fg=FG, font=('DejaVu Sans', 13, 'bold'))
        self.titulo.pack(pady=(10, 0))
        self.prueba = tk.Label(root, text='', bg=BG, fg=TENUE, font=('DejaVu Sans', 10)); self.prueba.pack()
        self.banner = tk.Label(root, text='NO DATA', bg=GRIS, fg='white', font=('DejaVu Sans', 26, 'bold'), pady=14)
        self.banner.pack(fill='x', padx=12, pady=10)
        self.sub = tk.Label(root, text='', bg=BG, fg=FG, font=('DejaVu Sans', 11)); self.sub.pack()

        self.ataque = tk.Label(root, text='', bg=BG, fg=TENUE, font=('DejaVu Sans', 11, 'bold')); self.ataque.pack(pady=(8, 2))
        tk.Label(root, text='(the real offset is known only to the simulator, not to the drone)', bg=BG, fg=TENUE, font=('DejaVu Sans', 8)).pack()

        self.cv = tk.Canvas(root, width=536, height=150, bg=BG, highlightthickness=0); self.cv.pack(pady=8)
        tk.Label(root, text='Response', bg=BG, fg=FG, font=('DejaVu Sans', 11, 'bold')).pack(anchor='w', padx=14)
        self.resp = tk.Label(root, text='-', bg=BG, fg=FG, font=('DejaVu Sans Mono', 10), justify='left', anchor='w'); self.resp.pack(fill='x', padx=14)
        tk.Label(root, text='Latest alerts', bg=BG, fg=FG, font=('DejaVu Sans', 11, 'bold')).pack(anchor='w', padx=14, pady=(8, 0))
        self.alist = tk.Label(root, text='-', bg=BG, fg=TENUE, font=('DejaVu Sans Mono', 9), justify='left', anchor='w'); self.alist.pack(fill='x', padx=14)
        self.dir = None
        self.tick()

    def reset(self, d):
        self.dir = d
        self.ts, self.ta, self.tr, self.tl = (Tail(os.path.join(d, n)) for n in ('signals.csv', 'alerts.csv', 'response.csv', 'relay.csv'))
        self.sig = None; self.alerts = []; self.resps = []; self.rel = None; self.t_att = None; self.max_off = 0.0
        try: self.meta = dict(kv.split('=', 1) for kv in open(os.path.join(d, 'test.txt')).read().split() if '=' in kv)
        except OSError: self.meta = {}

    def bar(self, y, nombre, valor, umbral, unidad, tope):
        # one horizontal bar: green below the threshold, red above; white line = threshold
        cv, x0, w = self.cv, 150, 300
        cv.create_text(8, y + 9, text=nombre, fill=FG, anchor='w', font=('DejaVu Sans', 10))
        cv.create_rectangle(x0, y, x0 + w, y + 18, fill='#2a2f37', outline='')
        if valor is not None:
            frac = min(1.0, valor / tope)
            cv.create_rectangle(x0, y, x0 + w * frac, y + 18, fill=ROJO if valor > umbral else VERDE, outline='')
            cv.create_text(x0 + w + 8, y + 9, text=('%.2f %s' % (valor, unidad)).strip(), fill=FG, anchor='w', font=('DejaVu Sans Mono', 10))
        xu = x0 + w * umbral / tope
        cv.create_line(xu, y - 4, xu, y + 22, fill='white', width=2)
        cv.create_text(xu, y + 30, text='threshold %g' % umbral, fill=TENUE, font=('DejaVu Sans', 8))

    def tick(self):
        d = newest()
        if d and d != self.dir: self.reset(d)
        if self.dir:
            for r in self.ts.read(): self.sig = r
            self.alerts += self.ta.read(); self.resps += self.tr.read()
            for r in self.tl.read():
                self.rel = r
                try:
                    off = (float(r['off_e']) ** 2 + float(r['off_n']) ** 2) ** 0.5
                    self.max_off = off
                    if off > 0.01 and self.t_att is None: self.t_att = float(r['t'])
                except (KeyError, ValueError): pass
            self.draw()
        self.root.after(300, self.tick)

    def draw(self):
        m = self.meta     # test.txt keys: name/mode/response (or the Spanish nombre/modo/respuesta)
        name, mode, resp = (m.get('name', m.get('nombre', '?')), m.get('mode', m.get('modo', '?')), m.get('response', m.get('respuesta', '?')))
        self.prueba.config(text='test: %s   attack: %s   response: %s' % (name, mode, resp))
        vivo = self.sig is not None and time.time() - float(self.sig['t']) < 5
        if self.alerts:
            a0 = self.alerts[0]
            self.banner.config(text='ALERT: SPOOFING', bg=ROJO)
            txt = 'first rule: %s at %s   (%d alerts)' % (a0['regla'], a0['iso'], len(self.alerts))
            if self.t_att is not None and float(a0['t']) >= self.t_att:
                txt += '\ndetected %.1f s after the attack started' % (float(a0['t']) - self.t_att)
            self.sub.config(text=txt)
        elif self.sig is None:
            self.banner.config(text='WAITING FOR THE DETECTOR', bg=GRIS); self.sub.config(text='')
        else:
            self.banner.config(text='NORMAL' if vivo else 'NORMAL (detector stopped)', bg=VERDE if vivo else GRIS)
            self.sub.config(text='no alerts')
        if self.rel is None: self.ataque.config(text='simulator true GPS: no data', fg=TENUE)
        elif self.max_off > 0.01: self.ataque.config(text='ATTACK IN PROGRESS: GPS forged by %.0f m' % self.max_off, fg='#ff8a65')
        elif self.t_att is not None: self.ataque.config(text='attack stopped (true GPS again)', fg=AMBAR)
        else: self.ataque.config(text='no attack: the drone receives the true GPS', fg='#81c995')

        self.cv.delete('all')
        s = self.sig
        f = (lambda k: float(s[k])) if s else (lambda k: None)
        self.bar(8, 'GPS vs estimate', f('d_gps_ekf'), DIST_HARD, 'm', 6.0)
        self.bar(58, 'position innov.', f('innov_pos'), INNOV_LIM, '', 1.0)
        self.bar(108, 'velocity innov.', f('innov_vel'), INNOV_SOFT, '', 0.6)

        self.resp.config(text='\n'.join('%s  %-10s %s' % (r['iso'], r['accion'], r['detalle'][:44]) for r in self.resps) or
                         ('(this test only detects, no response)' if resp == 'no' else '-'))
        self.alist.config(text='\n'.join('%s  %-15s %8.2f  (threshold %g)' % (r['iso'], r['regla'], float(r['valor']), float(r['umbral'])) for r in self.alerts[-6:]) or '-')


root = tk.Tk()
Panel(root)
root.mainloop()
