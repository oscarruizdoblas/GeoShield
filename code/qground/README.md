# QGroundControl

Abre [`geoshield_padova.plan`](geoshield_padova.plan) en QGroundControl con **Plan → Open**. El archivo reúne la misión normal y las figuras circulares configuradas para Padova.

La fuente canónica de coordenadas y radios es [`../python/zones.py`](../python/zones.py). Para regenerar el plan, desde la raíz del repositorio ejecuta:

```bash
python3 code/python/make_qgc_plan.py
```

El generador guarda el resultado aquí. Revisa visualmente el plan en QGC antes de cargarlo al vehículo.
