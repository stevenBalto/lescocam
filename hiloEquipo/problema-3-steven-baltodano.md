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

- [x] ~~**Fase 1 — Conectar el modo palabras y medir**~~ ✅ 2026-11-05 — evidencia: ambas manos en **83,1 %** de los 50 158 cuadros de seña de las 598 bimanuales (**79,2 %** sin contar 1965 cuadros con las dos manos del mismo lado); 213/598 palabras ≥ 90 %. Modo palabras conectado en la app (Ajustes › Cámara › «Reconocer palabras completas»). Medido con `scripts/medir_dos_manos.py`, resultado en `hiloEquipo/medidas/problema3-fase1-base.json`.
  **Hecho cuando:** el modo palabras funciona en la app de escritorio y se midió el porcentaje de cuadros con ambas manos sobre las 598 señas bimanuales (punto de partida).

- [ ] **Fase 2 — Reforzar la detección**
  Interpolación de huecos, muñeca del pose como respaldo, umbral de seguimiento más bajo.
  **Hecho cuando:** se volvió a medir y subió respecto a la fase 1. Si ya se llega a ≥ 90 %, se pasa directo a la fase 3.

  Causas medidas en la fase 1 (cuadros donde falta una mano):
  - 58 % están en huecos de ≤ 5 cuadros y 75 % en huecos de ≤ 8 (a 30 fps): se pierde un instante y vuelve.
  - Cuando falta una mano, el pose ve las dos muñecas en el 100 % de los cuadros.
  - 1965 cuadros con las dos manos marcadas del mismo lado (MediaPipe confunde izquierda/derecha).
  - 21 % de los cuadros con una mano tienen las manos juntas o cruzadas.

  Pasos, en orden, midiendo después de cada uno (`medir_dos_manos` + que `evaluar_palabras` no empeore):
  1. Asignar el lado de cada mano por la muñeca del pose más cercana (arregla los del mismo lado).
  2. Rellenar huecos cortos (≤ 8 cuadros) interpolando entre el cuadro anterior y el siguiente.
  3. Huecos largos: última forma de mano conocida, ubicada en la muñeca del pose.
  4. Bajar el umbral de confianza 0,5 → 0,3 (re-extrae las 598: probar primero con una muestra y **avisar a Christian**).

## Extra (fuera de las fases)

- [ ] Modo letras: detectar las dos manos y leer solo la **dominante** (zurdos; que la otra mano no confunda).
- [ ] Modo único letras + palabras sin interruptor: hablarlo con Johan (problema 2, respaldo por deletreo) antes de empezar.

- [ ] **Fase 3 — Usar la cara en las señas**
  **Hecho cuando:** la ubicación de la seña respecto al rostro entra al reconocimiento, y se midió que no empeora el resultado.

- [ ] **Fase 4 — Alternativa RTMW (solo si no se llegó a la meta)**
  **Hecho cuando:** se comparó RTMW contra MediaPipe con el mismo conjunto de señas y se decidió con números. Si la meta ya se cumplió en la fase 2, esta fase se tacha con la nota "no hizo falta".

## Notas

- El formato de landmarks v1 está congelado (ver `README.md`). Si se cambia el detector, avisar a Christian antes: obliga a re-extraer los datos del problema 1.
- El respaldo por deletreo del problema 2 se conecta al modo palabras que se deja funcionando en la fase 1.
