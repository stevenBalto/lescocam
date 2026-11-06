# Problema 4 — Luz y contraste distintos

**Responsable:** Reyman Barquero
**Meta:** recuperar ≥ 90 % de la detección que hay con buena luz, en poca luz y en contraluz.

## Qué hay que resolver

La cámara muestra la imagen con la luz que tiene el usuario y después no logra identificar las señas. No todos los usuarios tienen buena iluminación; hay que ser lo más adaptable posible y pedir más luz solo cuando de verdad no se pueda detectar.

## Cómo lo vamos a resolver

No encontramos ningún estudio que mida cómo afectan CLAHE o gamma a MediaPipe, así que lo medimos nosotros:

1. **Banco de luz**: oscurecer artificialmente los videos del CENAREC (poca luz, contraluz, ruido) y medir la tasa de detección en cada caso.
2. **Mejora automática**: probar gamma, CLAHE y un umbral de confianza más bajo, y quedarse con lo que mejore la detección. El brillo se mide en la zona de la mano, no en todo el cuadro, porque el contraluz (ventana atrás) es el caso más frecuente.
3. **Medidor de luz en la app**: tres niveles (buena, regular, baja). En "regular" se aplica la mejora automática; solo se pide más luz si de verdad no detecta.

## Fases

- [x] ~~**Fase 1 — Banco de luz**~~ ✅ 2026-11-05 — evidencia: banco de luz en `scripts/extraer_cenarec.py` (variantes `poca_luz_1..3` y `contraluz_1..3`) y medidor `scripts/evaluar_luz.py`. Tasa de detección de manos (≥1) medida sobre 30 videos, % vs luz normal: poca luz 1 = 100 %, poca luz 2 = 89 %, poca luz 3 = 0 %; contraluz 1 = 100 %, contraluz 2 = 100 %, contraluz 3 = 28 %. Casos a recuperar: poca luz 2 y 3, contraluz 3.
  **Hecho cuando:** hay un conjunto de videos oscurecidos (al menos poca luz y contraluz, en 3 niveles) y se midió la tasa de detección actual en cada uno (punto de partida).

- [x] ~~**Fase 2 — Probar las mejoras**~~ ✅ 2026-11-05 — evidencia: mejoras en `core/mejora_luz.py` (gamma, CLAHE, denoise) y grilla en `scripts/evaluar_mejora_luz.py`, medida sobre 30 videos (% vs luz normal). Elegida con números: **denoise + CLAHE** (no estropea la luz buena; recupera poca luz 2 de 83 %→99 % y contraluz 3 de 23 %→84 %; gamma a secas empeora el contraluz). Alternativa denoise + gamma para poca luz extrema (poca luz 3: 0 %→40 %, único que ayuda). Umbral de confianza se queda en 0.5 (0.3 solo ayudaba en el caso casi a oscuras). Brillo cuadro vs. zona de la mano: en poca luz baja todo (cuadro 15 / mano 11), en contraluz el cuadro queda brillante (139) con la mano sin detectar → el contraluz no se detecta por brillo general. Casos que no llegan a 90 %: poca luz 3 y contraluz 3 (contraluz 3 queda en 84 %) → se verifican con luz real en la fase 4.
  Gamma, CLAHE, umbral más bajo, y brillo medido en la zona de la mano.
  **Hecho cuando:** hay una tabla con la tasa de detección de cada combinación y se eligió la mejor con números.

- [x] ~~**Fase 3 — Medidor de luz en la app**~~ ✅ 2026-11-05 — evidencia: medidor de luz en la app (`core/mejora_luz.MedidorLuz` + bucle de `desktop/motor.py`) con 3 niveles (buena/regular/baja), mejora automática (denoise+CLAHE, o gamma si está muy oscuro) y aviso "Necesita más luz". Probado con luz REAL por Reyman (laptop-windows): luces apagadas con brillo de pantalla → "poca luz, mejorando"; brillo al mínimo → "necesito más luz"; al subir el brillo se reanuda y detecta solo, aun con la pieza a oscuras. Simulador de iluminación desde la PC en Ajustes › Cámara (solo --dev) para reproducir poca_luz_1..3 y contraluz_1..3. Pendiente para la fase 4: contraluz 3 todavía inconsistente (coincide con el 84 % medido en la fase 2; en contraluz el cuadro está brillante y el medidor no lo marca por brillo). Extras surgidos de las pruebas: primer uso una sola vez y pausa por falta de manos/luz que se reanuda sola.
  Tres niveles, mejora automática en "regular", aviso de más luz solo si no detecta.
  **Hecho cuando:** funciona en la app de escritorio y se probó con luz real (buena, regular y baja).

- [ ] **Fase 4 — Verificar contra la meta**
  **Hecho cuando:** en poca luz y en contraluz se recupera ≥ 90 % de la detección de buena luz. Si no, se vuelve a la fase 2.

## Notas

- Esto afecta la cámara en vivo, no el entrenamiento: es independiente de los otros problemas.
- El banco de prueba del problema 1 incluye distintas luces, y sirve también como prueba real para este problema.
