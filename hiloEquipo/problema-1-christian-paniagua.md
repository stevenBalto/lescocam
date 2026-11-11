# Problema 1 — Reconocer sin depender de firmantes humanos

**Responsable:** Christian Paniagua
**Meta:** ≥ 95 % top-1 con ≤ 2 % de aceptaciones erróneas en el banco de prueba.

## Qué hay que resolver

Hoy el motor se evalúa con el mismo firmante que grabó las plantillas (98.8 % en 85 palabras), y eso es optimista. Con otras personas, ángulos y distancias baja. No podemos ni queremos pedir que expertos o estudiantes hagan todas las señas.

## Cómo lo vamos a resolver

El motor trabaja en landmarks, no en imágenes. Entonces la variedad que necesitamos se puede fabricar sobre los landmarks y se puede aprender de otros idiomas de señas:

1. **Banco de prueba** para medir de verdad. Se imita el video del CENAREC; no hace falta saber LESCO. Esas tomas son solo de prueba, nunca plantillas.
2. **Aumentación en landmarks**: rotación 3D (giro ±30°, inclinación ±20°), escala ±15 %, amplitud del movimiento, velocidad ×0.7 a ×1.4, ruido leve, pérdida de cuadros de una mano y cambio de mano dominante.
3. **Preentrenamiento con ASL Citizen** (~84 mil videos, 2.7 mil señas, 52 firmantes): un modelo que convierte cada seña en un vector y reconoce por búsqueda de similitud. Agregar señas nuevas no obliga a reentrenar.
4. **Avatar 3D** como pista opcional, solo si sobra tiempo.

## Fases

- [x] ~~**Fase 1 — Banco de prueba**~~ ✅ 2026-11-11 — evidencia: 240 tomas, 4 firmantes y 4 cámaras (iPhone 13, HP Linux, 2 laptops Windows); motor actual: top-1 40.4 %, top-3 58.3 %, dice la palabra correcta 16.7 %, aceptación errónea 0.0 %, calla 83.3 %, sin seña 10.0 %. Por persona (top-1): Christian 16.7 %, Steven 35.0 % (35 % sin seña), Reyman 46.7 %, Johan 63.3 %. Resumen en `data/banco/resultado_inicial.json`.
  ~~Cada uno graba **30 palabras × 2 tomas** imitando el video del CENAREC (`scripts/grabar_banco.py`), con su cámara y variando luz, distancia y ángulo por tandas. Reparto de las 85 palabras iniciales: **12 del núcleo común** (las graban los 4, para comparar firmantes con las mismas palabras) + **18 propias** por persona; LESCO queda de reserva. Listas en `data/reference/banco/<nombre>.txt`. Las tomas (landmarks, no video) van en `data/banco/<persona>/` y se versionan (~100 KB cada una). Christian coordina; Steven, Reyman y Johan arrancan con «Vengo de parte de Christian» (skill `vengo-de-parte-de-christian`) y al terminar suben sus tomas y su registro `hiloEquipo/banco/<persona>.md`. Estado: `.venv/Scripts/python -m scripts.registrar_banco --estado`.~~
  Punto de partida para las fases 2 y 5. Pendientes anotados: revisar por qué Steven tiene 35 % sin seña (segmentación o encuadre en Linux); nadie usó el Huawei; las condiciones de Christian son todas luz buena, media y de frente.

- [ ] **Fase 2 — Aumentación en landmarks**
  Aplicar las variaciones de arriba a las 2 plantillas de cada palabra.
  **Hecho cuando:** se midió contra el banco y mejoró respecto al punto de partida de la fase 1.

- [ ] **Fase 3 — Datos de ASL Citizen**
  Descargar (~43 GB; leer los videos directo del zip o borrar el zip después, hay ~137 GB libres). Confirmar que la licencia (solo investigación no comercial) aplica a nuestro caso. Extraer landmarks de una muestra de ~15 mil videos en el **formato v1** (ver `README.md`).
  **Hecho cuando:** hay un archivo de landmarks listo para entrenar.

- [ ] **Fase 4 — Entrenar el modelo**
  Embedding sobre landmarks, entrenado en la RTX A500 de Christian. Reconocimiento por búsqueda vectorial contra las plantillas del CENAREC.
  **Hecho cuando:** el modelo entrena y reconoce señas del CENAREC por similitud.

- [ ] **Fase 5 — Integrar y medir**
  Conectar el modelo al motor y medir contra el banco de prueba.
  **Hecho cuando:** ≥ 95 % top-1 con ≤ 2 % de aceptaciones erróneas. Si no se llega, se itera sobre la fase que más pese.

## Notas

- Si Steven cambia el detector (problema 3), hay que re-extraer en la fase 3.
- Pista opcional (cualquiera con tiempo): avatar 3D para generar variedad de cuerpo y cámara pasando por el detector real.
