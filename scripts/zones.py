# GeoShield - definicion UNICA de escenario (importado por mapa, planificador, fence y mundo 3D).
# Coordenadas reales de Padova (verificadas con OpenStreetMap / Nominatim).
#
# Escenario: salir de A (San Giuseppe, Riviera Paleocapa) y llegar a B (Torre Archimede,
# Dipartimento di Matematica "Tullio Levi-Civita", zona Portello/Scrovegni, donde dan clase).
# La recta A->B cruza la zona prohibida de Palazzo Bo (universidad del centro historico),
# asi que en vuelo NORMAL el dron debe rodearla por el camino mas corto.

# Punto de SALIDA (A) = tambien el HOME de spawn del simulador
START = (45.4021, 11.8670)        # San Giuseppe / Riviera Paleocapa (SW de Padova)
HOME  = START

# DESTINO (B)
DEST  = (45.4113328, 11.8878209)  # Torre Archimede - Dip. Matematica "Tullio Levi-Civita"

# ZONAS PROHIBIDAS (keep-out): universidad del centro historico de Padova
KEEPOUT = [
    {"name": "Palazzo Bo (Universita, centro)",   "lat": 45.4067383, "lon": 11.8773940, "r": 220},
    {"name": "Palazzo Liviano (Universita, centro)", "lat": 45.4079860, "lon": 11.8714491, "r": 150},
]

# Area operativa permitida (keep-in): engloba A, B y las zonas
KEEPIN = {"name": "Area operativa Padova", "lat": 45.40672, "lon": 11.87741, "r": 1500}

# Nombres legibles de A y B (para mapas/etiquetas)
START_NAME = "A - Riviera Paleocapa (San Giuseppe)"
DEST_NAME  = "B - Torre Archimede (Matematica)"
