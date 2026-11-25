# Documentación de los experimentos GeoShield

Los cuatro experimentos comparan el comportamiento de PX4 SITL y GeoShield en el mismo escenario. El estado indica qué se ha ejecutado realmente; una descripción de un experimento futuro no implica que ya haya resultados.

| Experimento | Escenario | Estado | Evidencias actuales |
|---|---|---|---|
| [01 — Vuelo normal](experimento-01/README.md) | GPS simulado nominal; ruta A→B→A que evita las zonas protegidas. Es la línea base de comparación. | **Realizado** el 14-11-2026 en PX4 SITL. | CSV de GPS, posición global y estado del estimador; ULog de PX4; vídeo enlazado desde Drive. No hay capturas de pantalla independientes validadas. |
| [02 — Deriva gradual](experimento-02/README.md) | Escenario futuro de manipulación gradual sintética en SITL, comparado con la línea base. | **Pendiente; no ejecutado.** | Ninguna. |
| [03 — Salto abrupto](experimento-03/README.md) | Escenario futuro de cambio sintético abrupto en SITL y evaluación de la respuesta observada. | **Pendiente; no ejecutado.** | Ninguna. |
| [04 — Defensa GeoShield](experimento-04/README.md) | Evaluación futura del detector y la respuesta defensiva frente a anomalías simuladas. | **Pendiente; no ejecutado.** | Ninguna. |

## Cómo leer los resultados

QGroundControl muestra telemetría recibida de PX4, pero el movimiento de su marcador por sí solo no demuestra qué muestras aceptó el EKF. Para afirmar que una anomalía alcanzó la navegación, hay que respaldarlo con señales del estimador y logs PX4 sincronizados en el tiempo. El vuelo normal no es una prueba de resistencia a spoofing ni demuestra por sí solo la aplicación efectiva de la geocerca.

## Alcance

El plan es para simulación de software (PX4 SITL y Gazebo). No se han realizado ataques en este estado del proyecto. No se usarán aeronaves físicas ni transmisiones RF en estos experimentos documentados.
