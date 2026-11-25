# Experimento 02 — deriva gradual simulada

## Objetivo

Estudiar en PX4 SITL cómo evoluciona la posición reportada cuando aparece una desviación sintética lenta, y compararla con el vuelo nominal del Experimento 01. La pregunta de evaluación es si las señales disponibles permiten distinguir esa evolución del ruido normal del sistema.

## Estado

**Pendiente; no ejecutado.** Esta carpeta describe el experimento previsto, no un resultado. No hay vídeo, imágenes, CSV ni ULog asociados.

## Qué habrá que registrar

- Qué señal recibe el estimador de PX4 y cómo se verifica que la anomalía llegó hasta él.
- GPS reportado, posición global estimada y estado/innovaciones del estimador, con marcas temporales comunes.
- Trayectoria, separación GPS–EKF, alertas del detector y cambios de modo o respuesta del vehículo.
- Versión de PX4/Gazebo, configuración del escenario, duración y criterio para detener la prueba.

## Límites de interpretación

Un marcador desplazado en QGroundControl no demuestra por sí solo que PX4 aceptara una posición manipulada. La validación prevista es exclusivamente en SITL y debe conservar las comprobaciones de seguridad normales. No hay ninguna inyección configurada o ejecutada como parte de este registro.

## Evidencia

Aún no existe evidencia de ejecución. Cuando se realice, guardar aquí el vídeo o su enlace, capturas representativas y los registros necesarios; anotar claramente qué se midió y qué no pudo verificarse.
