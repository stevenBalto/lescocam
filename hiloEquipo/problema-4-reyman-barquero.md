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

- [ ] **Fase 1 — Banco de luz**
  **Hecho cuando:** hay un conjunto de videos oscurecidos (al menos poca luz y contraluz, en 3 niveles) y se midió la tasa de detección actual en cada uno (punto de partida).

- [ ] **Fase 2 — Probar las mejoras**
  Gamma, CLAHE, umbral más bajo, y brillo medido en la zona de la mano.
  **Hecho cuando:** hay una tabla con la tasa de detección de cada combinación y se eligió la mejor con números.

- [ ] **Fase 3 — Medidor de luz en la app**
  Tres niveles, mejora automática en "regular", aviso de más luz solo si no detecta.
  **Hecho cuando:** funciona en la app de escritorio y se probó con luz real (buena, regular y baja).

- [ ] **Fase 4 — Verificar contra la meta**
  **Hecho cuando:** en poca luz y en contraluz se recupera ≥ 90 % de la detección de buena luz. Si no, se vuelve a la fase 2.

## Notas

- Esto afecta la cámara en vivo, no el entrenamiento: es independiente de los otros problemas.
- El banco de prueba del problema 1 incluye distintas luces, y sirve también como prueba real para este problema.
