# Evidencias — Experimento 01

## Vídeo

[Abrir «Experimento 1.mp4» en Google Drive](https://drive.google.com/file/d/1tfNl-XtwFbwF7WvPxh80LVK_pFf5RQCq/view?usp=drive_link)

El original local mide aproximadamente 1,1 GB. Siguiendo la decisión anterior del proyecto, se conserva el enlace compartido y no se añade el vídeo completo al repositorio.

## Telemetría y log PX4

La carpeta `telemetria/` contiene copias de los tres CSV. El ULog está en `registro-px4/`; mide aproximadamente 146 MB y permanece solo en la copia local, porque Git lo ignora mediante la regla `*.ulg`. Los CSV pueden revisarse con las herramientas de [`../../../code/python/README.md`](../../../code/python/README.md).

| Archivo | Contenido |
|---|---|
| `telemetria/gps_raw.csv` | Muestras GPS reportadas por PX4. |
| `telemetria/global_pos.csv` | Posición global estimada. |
| `telemetria/est_status.csv` | Estado e innovaciones del estimador. |
| `registro-px4/2026-11-14_10-43-27.ulg` | Registro completo PX4 de la ejecución normal identificada en el informe técnico (copia local ignorada por Git). |

## Imágenes

No hay capturas fijas verificadas de QGC/Gazebo durante el vuelo. Las capturas de prueba disponibles muestran OBS/VS Code o un viewport negro, así que no se presentan como evidencia experimental. El vídeo enlazado es el material visual disponible.
