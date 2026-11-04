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

- [ ] **Fase 1 — Banco de prueba**
  Los 4 graban ~30 palabras × 2 tomas cada uno, imitando el video del CENAREC, con distinta luz y distancia. Christian coordina. Se guardan como tomas `webcam:<persona>` (ubicación por definir en esta fase; no se versiona lo que pase de 5 MB).
  **Hecho cuando:** el banco existe y se midió el motor actual (top-1, top-3, aceptaciones erróneas y resultado por persona). Ese es el punto de partida.

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
