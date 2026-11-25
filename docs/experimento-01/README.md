# Experimento 01 — vuelo autónomo normal

## Objetivo

Obtener una línea base del escenario Padova con GPS simulado nominal, misión normal y planificación alrededor de las zonas keep-out. No se aplicó spoofing.

## Qué se hizo

El 14 de noviembre de 2026 se ejecutó PX4 SITL con un X500 en Gazebo Sim 8, conectado a QGroundControl. El vehículo despegó desde A (Riviera Paleocapa), recorrió la ruta planificada hasta B (Torre Archimede), volvió por la ruta inversa y aterrizó en A. El planificador informó siete nodos incluyendo el origen y seis waypoints por sentido.

La telemetría registrada contiene 3.128 muestras GPS válidas, unos 601 segundos de datos y 4.010 m de recorrido muestreado. La distancia mínima muestreada al borde de Palazzo Bo fue 72,1 m; a Palazzo Liviano, 395,9 m. Son mínimos entre muestras, no una prueba continua de separación. El vuelo terminó con detección de aterrizaje en A.

## Qué demuestra y qué no

- **Demuestra:** el vuelo nominal SITL A→B→A se completó y la ruta registrada pasó fuera de los radios configurados.
- **No demuestra:** resistencia a spoofing, aceptación/rechazo de muestras por el EKF en un escenario manipulado, ejecución del detector, ni aplicación efectiva de cada parámetro/evento de geofence durante todo el vuelo.
- El vídeo permite revisar QGC y Gazebo en la misma grabación, pero el X500 no se identifica claramente en todo momento. No se conserva una captura fija validada como evidencia independiente.

## Evidencias guardadas

- [Vídeo de pantalla en Google Drive y detalle de los registros](evidencia/README.md).
- `evidencia/telemetria/gps_raw.csv`: GPS reportado por PX4.
- `evidencia/telemetria/global_pos.csv`: posición global estimada.
- `evidencia/telemetria/est_status.csv`: estado/innovaciones del estimador.
- `evidencia/registro-px4/2026-11-14_10-43-27.ulg`: ULog PX4 correspondiente al vuelo normal identificado en el informe. El ULog es local e ignorado por Git por su tamaño.
- Las imágenes PNG disponibles en el espacio de trabajo eran capturas de pruebas de OBS/VS Code o pantallas negras, no evidencias del vuelo; por eso no se copian como pruebas del experimento.

El [informe técnico detallado](informe-tecnico-en.md) conserva el método, métricas, arquitectura y limitaciones en inglés. La [vista general de los cuatro experimentos](../README.md) explica cómo se usa esta línea base.
