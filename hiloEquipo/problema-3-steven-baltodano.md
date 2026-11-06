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

- [x] ~~**Fase 2 — Reforzar la detección**~~ ✅ 2026-11-05 — evidencia: ambas manos en **93,5 %** de los 50 158 cuadros de seña de las 598 bimanuales (fase 1: 83,1 %); 477/598 palabras ≥ 90 % (antes 213); reconocimiento cruzado de las 598: top-1 98,2 → **99,2 %**, aceptadas mal 0,4 % → 0,4 %. Medido con `scripts/probar_deteccion.py` y `medir_dos_manos.py --variante det_recorte`, resultado en `hiloEquipo/medidas/problema3-fase2-recorte.json`.
  Interpolación de huecos, muñeca del pose como respaldo, umbral de seguimiento más bajo.
  **Hecho cuando:** se volvió a medir y subió respecto a la fase 1. Si ya se llega a ≥ 90 %, se pasa directo a la fase 3.

  Qué se hizo:
  - Interpolación de huecos y muñeca del pose como respaldo **ya estaban** en `core/palabras.py` (y la asignación de cada mano por la muñeca del pose, sin las etiquetas Left/Right). Los 1965 cuadros "del mismo lado" eran en su mayoría dos manos distintas con la etiqueta mal: el 83,1 % de la fase 1 es el número real.
  - **Umbral 0,5 → 0,3: empeora** (muestra de 50: 83,3 → 78,2 %, top-1 97 → 93 %). Descartado.
  - **Recorte (nuevo, `core/cuerpo.buscar_en_recortes`, `DetectorCuerpo(recorte=True)`)**: si falta una mano, se la busca otra vez en un recorte alrededor de la muñeca del pose. Muestra de 50: 83,3 → 93,0 %; las 598: 83,1 → 93,5 %. Sin librerías nuevas (el mismo HandLandmarker en modo IMAGE).
  - Velocidad en vivo: el recorte buscaba en cada cuadro la mano de un brazo en reposo (CASA: 30 → 19 fps). Ahora no busca si el brazo está en reposo: CASA 27 fps, el resto ~30 fps.
  - Encendido en la app (modo palabras) y en `scripts/demo_palabras.py`.

  **Pendiente (cuando estén todos los videos):** ver «Pendiente para cuando estén todos los videos» abajo.

## Extra (fuera de las fases)

- [ ] Modo letras: detectar las dos manos y leer solo la **dominante** (zurdos; que la otra mano no confunda).
- [ ] Modo único letras + palabras sin interruptor: hablarlo con Johan (problema 2, respaldo por deletreo) antes de empezar.

- [ ] **Fase 3 — Usar la cara en las señas**
  **Hecho cuando:** la ubicación de la seña respecto al rostro entra al reconocimiento, y se midió que no empeora el resultado.

- [ ] **Fase 4 — Alternativa RTMW (solo si no se llegó a la meta)**
  **Hecho cuando:** se comparó RTMW contra MediaPipe con el mismo conjunto de señas y se decidió con números. Si la meta ya se cumplió en la fase 2, esta fase se tacha con la nota "no hizo falta".

## Pendiente para cuando estén todos los videos

Para no re-extraer y re-entrenar cada vez que se agregan videos, esto se hace **una sola vez**, cuando estén todos los materiales juntos:

- [ ] Re-extraer **todos** los videos con `DetectorCuerpo(recorte=True)` (la versión que no busca en brazos en reposo) y volver a medir las bimanuales: `scripts/probar_deteccion.py --muestra 598 --config recorte_v2` (la medición de 93,5 % es de la versión anterior del recorte, sin el ajuste de reposo).
- [ ] Coordinar con Christian (problema 1): que su entrenamiento use la misma extracción con recorte que la app. Ya se le avisó del cambio; falta su decisión.
- [ ] Regenerar `data/reference/senas.db` (y la base completa) desde la extracción con recorte, para que plantillas y cámara pasen por el mismo detector.
- [ ] Volver a medir la fase 3 (cara) con la extracción nueva.

## Notas

- El formato de landmarks v1 está congelado (ver `README.md`). Si se cambia el detector, avisar a Christian antes: obliga a re-extraer los datos del problema 1.
- El respaldo por deletreo del problema 2 se conecta al modo palabras que se deja funcionando en la fase 1.
