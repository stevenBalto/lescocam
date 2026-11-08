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

- [x] ~~Modo letras: detectar las dos manos y leer solo la **dominante** (zurdos; que la otra mano no confunda).~~ ✅ 2026-11-05 — `core/camara.Detector(mano="derecha"|"izquierda")` busca las dos y lee solo esa; en la app: Ajustes › Cámara › «Mano para deletrear» (por defecto «Cualquiera», como antes). Falta probarlo en vivo con un zurdo.
- [ ] Modo único letras + palabras sin interruptor: hablarlo con Johan (problema 2, respaldo por deletreo) antes de empezar.

- [x] ~~**Fase 3 — Usar la cara en las señas**~~ ✅ 2026-11-05 — evidencia: la posición de cada mano respecto de la nariz entra al descriptor (`core/palabras.py`, `VERSION_DESCRIPTOR = 2`, 83 columnas) y no empeora: CENAREC 1039 palabras, aceptadas bien 95,3 → 95,4 %, mal 0,1 → 0,1 %; banco de prueba (120 tomas, 2 personas) top-1 33,3 → 33,3 %, mal 0 → 0 %. Resultado en `hiloEquipo/medidas/problema3-fase3-cara.json`.
  **Hecho cuando:** la ubicación de la seña respecto al rostro entra al reconocimiento, y se midió que no empeora el resultado.

  Qué se hizo:
  - Primera versión ("resta": muñeca - nariz siempre): **empeora con otras personas** (banco: top-1 33 → 27 %, aparecen 2,5–5 % de aceptadas mal). La distancia nariz-hombros cambia de persona a persona y con la cámara: suma un error fijo a todas las señas. Descartada.
  - Versión elegida ("cerca"): la posición respecto de la nariz solo cuenta con la mano a menos de 0,6 anchos de hombro de la cara (30 de las 85 palabras iniciales pasan por ahí: AZUL, COSTA-RICA, POLLO, NIÑO...). No empeora nada; tampoco mejora de forma medible con estos datos (CENAREC es una sola persona y en el banco el 85 % de las tomas falla por otras razones).
  - **Cambio de contrato: afecta a la app móvil.** `senas.db` pasa a `version_descriptor 2` (83 columnas: + 2 de cara por mano) y guarda `CARA_MODO`, `CARA_RADIO` y `NARIZ_TIPICA` en `constantes`. Una base vieja se rechaza (`VersionIncompatible`). `data/reference/senas.db` regenerado (85 palabras, desde el cache, sin re-extraer videos).

- [x] ~~**Fase 4 — Alternativa RTMW (solo si no se llegó a la meta)**~~ ✅ 2026-11-05 — no hizo falta: la meta (≥ 90 %) se cumplió en la fase 2 con el recorte (93,5 %).
  **Hecho cuando:** se comparó RTMW contra MediaPipe con el mismo conjunto de señas y se decidió con números. Si la meta ya se cumplió en la fase 2, esta fase se tacha con la nota "no hizo falta".

## Pendientes de Steven Baltodano

Las 4 fases están cerradas. Queda a cargo de Steven:

1. **Grabar su banco de prueba (30 palabras)** — se arranca diciéndole a Claude «Vengo de parte de Christian». Lista en `data/reference/banco/steven.txt`:
   - [ ] Tanda 1: VERDE, HOLA, NOMBRE, GRACIAS, AÑO, JUEVES, SÍ, CUÁNTO, NO, ENTENDER
   - [ ] Tanda 2: PAN, MAMÁ, BEBÉ, NIÑO, AMARILLO, SÁBADO, HOY, QUÉ-PASAR, COMER, IR
   - [ ] Tanda 3: HIJA, POR-FAVOR, CÓMO, CASA, FRUTA, COSTA-RICA, QUERER, MAL, AYUDAR, TRABAJAR
2. - [x] ~~**Cuando Johan agregue los videos de palabras**, hacer la lista de abajo «Pendiente para cuando estén todos los videos».~~ ✅ 2026-11-07 (ver abajo).
3. - [ ] Probar en vivo: HOLA en modo palabras y «Mano para deletrear» con un zurdo.
4. - [ ] Hablar con Johan del modo único letras + palabras (ver «Extra»).

## Pendiente para cuando estén todos los videos

Para no re-extraer y re-entrenar cada vez que se agregan videos, esto se hace **una sola vez**, cuando estén todos los materiales juntos:

- [x] ~~Re-extraer **todos** los videos con `DetectorCuerpo(recorte=True)` y volver a medir las bimanuales.~~ ✅ 2026-11-07 — CENAREC (1072 videos, `extraer_cenarec.py --recorte` → `extraccion/recorte/`) y Hands-On (2161 de 2281 videos a 540p, `extraer_handson.py` → `handson/extraccion/recorte/`). Resultados (`medir_dos_manos.py`, en `hiloEquipo/medidas/`):
  - **CENAREC**, señas de dos manos: ambas manos **90,2 %** (antes 83,1 %; meta ≥ 90 % ✅). Contando solo cuadros con los dos brazos levantados (`--brazos-arriba`): 85,9 % → **93,7 %**. Lo que se pierde respecto del 93,5 % de la fase 2 son manos en la cintura (el ajuste de reposo, que hace el recorte más rápido); el reconocimiento no cambia (top-1 99,2 %).
  - **Hands-On**, palabras de dos manos: 67,3 % en bruto, pero no es el detector: Hands-On hace algunas de esas palabras con una sola mano, la 2.ª repetición está grabada **de perfil** y el encuadre corta en la cintura. Con los dos brazos levantados: **83,9 %**; muestra de 300 videos sin y con recorte: 80,5 % → 83,6 %. 1.ª repetición (de frente) 88,9 %, 2.ª (de perfil) 78,4 %.
  - 120 videos de Hands-On no se pueden bajar (Vimeo 401): lista en `medidas/handson-videos-no-descargados.md`, para pedírselos a Hands-On.
- [ ] Coordinar con Christian (problema 1): que su entrenamiento use la misma extracción con recorte que la app. Ya se le avisó del cambio (aviso en `README.md`, actualizado); falta su decisión.
- [x] ~~Regenerar `data/reference/senas.db` (y la base completa) desde la extracción con recorte.~~ ✅ 2026-11-07 — `senas.db` = 85 palabras, extracción con recorte, **solo CENAREC**. Banco de prueba (120 tomas, 2 personas): top-1 33,3 % → 31,7 % (2 tomas, ruido), aceptación errónea 0 %. **Con plantillas de Hands-On (`--handson`) empeora**: top-1 29,2 %, errónea **3,3 %** (meta ≤ 2 %), así que no entran a la app. Base completa (afuera de git): `data/dictionary/senas_todas_fuentes.db` (2306 palabras, CENAREC + Hands-On, para medir).
- [x] ~~Volver a medir la fase 3 (cara) con la extracción nueva; probar `PESO_CARA` 2.~~ ✅ 2026-11-07 — entre personas (plantillas de CENAREC, prueba con Hands-On y al revés, 406 palabras en común, `scripts/evaluar_fuentes.py`): peso de la cara 0, 1 y 2 dan lo mismo (top-1 ~21 % y ~26 %). La cara no ayuda ni estorba; se deja `PESO_CARA = 1`. Falta medirla con el banco de las 4 personas cuando esté completo. Resultado en `medidas/problema3-fuentes-cara.json`.

**Para Christian (problema 1):** el reconocimiento **entre personas** es bajo: con plantillas de una persona y prueba con otra, top-1 ~21–26 % y aceptadas mal ~4–6 %. Probé si la mano en reposo más alta de Hands-On lo explicaba (bajar el umbral de reposo a 0,7/0,6/0,5): no mejora, se deja 0,85. El problema de fondo es la variación entre personas, que es lo que ataca el problema 1.

## Notas

- El formato de landmarks v1 está congelado (ver `README.md`). Si se cambia el detector, avisar a Christian antes: obliga a re-extraer los datos del problema 1.
- El respaldo por deletreo del problema 2 se conecta al modo palabras que se deja funcionando en la fase 1.
