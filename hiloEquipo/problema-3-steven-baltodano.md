# Problema 3 — La cámara detecta solo una mano

**Responsable:** Steven Baltodano
**Meta:** ambas manos detectadas en ≥ 90 % de los cuadros de las 598 señas bimanuales del CENAREC.

## Qué hay que resolver

Para el alfabeto basta una mano, pero para palabras y señas complejas hacen falta las dos y el cuerpo. El motor ya detecta 2 manos más pose en modo palabras (`DetectorCuerpo`, `core/cuerpo.py`); solo el modo letras usa una mano, y es a propósito. Lo que falta es conectar el modo palabras en la app de escritorio, y por eso parece que solo ve una. El riesgo real es que MediaPipe pierda una mano cuando se cruzan o se tapan.

## Cómo lo vamos a resolver

1. **Conectar y medir**: conectar el modo palabras en la app y medir en qué porcentaje de cuadros aparecen ambas manos.
2. **Reforzar cuando se pierde una mano**: interpolar los huecos entre cuadros, usar la muñeca del pose como respaldo y bajar el umbral de confianza de seguimiento.
3. **Usar la cara**: los puntos de nariz, ojos y boca ya vienen dentro del pose (del 0 al 10), sin librería nueva, para ubicar la seña respecto al rostro.
4. **RTMW solo si hace falta**: si tras el refuerzo no se llega a la meta, probar RTMW (133 puntos de cuerpo completo) y comparar. No hay evidencia de que sea mejor con manos cruzadas, por eso va al final.

## Fases

- [ ] **Fase 1 — Conectar el modo palabras y medir**
  **Hecho cuando:** el modo palabras funciona en la app de escritorio y se midió el porcentaje de cuadros con ambas manos sobre las 598 señas bimanuales (punto de partida).

- [ ] **Fase 2 — Reforzar la detección**
  Interpolación de huecos, muñeca del pose como respaldo, umbral de seguimiento más bajo.
  **Hecho cuando:** se volvió a medir y subió respecto a la fase 1. Si ya se llega a ≥ 90 %, se pasa directo a la fase 3.

- [ ] **Fase 3 — Usar la cara en las señas**
  **Hecho cuando:** la ubicación de la seña respecto al rostro entra al reconocimiento, y se midió que no empeora el resultado.

- [ ] **Fase 4 — Alternativa RTMW (solo si no se llegó a la meta)**
  **Hecho cuando:** se comparó RTMW contra MediaPipe con el mismo conjunto de señas y se decidió con números. Si la meta ya se cumplió en la fase 2, esta fase se tacha con la nota "no hizo falta".

## Notas

- El formato de landmarks v1 está congelado (ver `README.md`). Si se cambia el detector, avisar a Christian antes: obliga a re-extraer los datos del problema 1.
- El respaldo por deletreo del problema 2 se conecta al modo palabras que se deja funcionando en la fase 1.
