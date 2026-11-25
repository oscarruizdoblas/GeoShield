# Experimento 03 — cambio abrupto simulado

## Objetivo

Evaluar en PX4 SITL la respuesta temporal ante un cambio sintético abrupto de posición y comparar la trayectoria, las innovaciones del estimador y los modos observados con el vuelo normal del Experimento 01.

## Estado

**Pendiente; no ejecutado.** Esta carpeta es una ficha de planificación. No hay vídeo, imágenes, CSV ni ULog del experimento.

## Qué habrá que registrar

- Señal de posición observada por PX4 y evidencia de que llegó a la navegación/estimador.
- Instante del cambio, GPS reportado, estado global estimado e innovaciones del estimador.
- Tiempo hasta cualquier detección, rechazo, cambio de modo o recuperación.
- Versión/configuración SITL, criterios de parada y comparación con una ejecución nominal equivalente.

## Límites de interpretación

Una variación del mapa de QGroundControl no basta para atribuir el efecto al EKF. La prueba futura se limita a PX4 SITL, sin aeronave física ni transmisión RF, y mantiene activas las comprobaciones de seguridad.

## Evidencia

Aún no existe evidencia de ejecución. Añadir en esta carpeta el registro de PX4, CSV de telemetría, capturas y vídeo o enlace cuando la prueba se realice.
