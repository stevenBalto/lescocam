# Sesión 2026-11-12 — Fase 5: rediseño de la aceptación y diagnóstico del top-1

**Área:** Backend (core / data / scripts / tests)
**Quién:** Christian Paniagua Castro

## Objetivo de la sesión
- Rediseñar lo que frena la meta del problema 1 (≥ 95 % top-1, ≤ 2 % aceptación errónea): aceptación, forma de la mano y licencia.

## Lo que se hizo
- **`DURACION_MAX` 4 → 6 s** (`core/palabras.py`, `senas.db` regenerada: las mismas 170 plantillas, solo cambia `meta.constantes`). Motor solo con DTW (`scripts/evaluar_banco.py`): top-1 64.2 → 67.1 %, top-3 79.6 → 82.5 %, dice bien 27.9 → 30.0 %, sin seña 4.2 → 0.4 %, aceptación errónea igual (0.4 %).
- **Aceptación nueva en `scripts/evaluar_banco_modelo.py`**: en la suma, el DTW y el modelo tienen que coincidir en la primera (`--sin-coincidir` lo quita). Validación nueva **por persona** (se ajusta con las demás, se valida con ella, 4 rondas) además de la de grupos; guarda el umbral y margen más estrictos de las rondas. Con `embedding_v3p.pt`, peso 0.7: top-1 82.9 %, top-3 95.0 %, por persona dice bien 45.8 % y **errónea 2.1 %** (antes 5.0 %).
- Ensamble de 4 modelos (misma receta, otra semilla): top-1 80.8 %, top-3 95.0 %, errónea 0.8 %, dice bien 42.5 %.
- Tests: 8 nuevos (suite 404). Revisión Sonnet alto: sin hallazgos altos; se arreglaron `ajustar` con tomas vacías y el JSON con `inf`.

## Lo que se midió y se descartó
- Rasgos nuevos a mano para el DTW (trayectoria sin el promedio, velocidad, puntos de la mano, rasgos centrados; 13 variantes): ninguno mejora ni en ASL (42 %) ni en el banco (67 %). El descriptor v3 está en su techo.
- Normalizar el sesgo de cada persona (media y desvío por persona, sin etiquetas): 67 → 60–70 %, sin mejora clara.
- Elegir el mejor segmento de la toma en vez del más largo: a lo sumo +1 punto.
- Entrenar el modelo también con las 85 palabras de CENAREC como clases: empeora (82 → 76 %), se aprende de memoria a ese firmante.
- Modelo más ancho (256, 6 bloques): 5 veces más lento y sin ventaja en las primeras épocas; se cortó.

## Decisiones y notas
- **El 82.9 % era una semilla con suerte.** Cuatro entrenamientos iguales dan 75.4, 78.7, 78.7 y 82.9 % en el banco. El número honesto de un modelo es ~79 ± 3 %; el del ensamble, 80.8 %.
- **Lo que manda es cuántas señas distintas ve el modelo al entrenar:** 250 glosas → 65 % en el banco, 1000 → 74 %, 2321 → 82 %. PopSign (CC BY 4.0, 250 señas, 1.1 TB de video) solo no alcanzaría.
- **Plantillas de otras personas ayudan mucho al DTW y no tienen problema de licencia.** En las 12 palabras del núcleo, dejando una persona afuera y usando a las otras 3 como plantilla: DTW 67 → 88 % entre las 85 palabras (inflado: solo esas 12 tenían plantillas extra) y 82 → 92 % comparando solo entre las 12. El modelo casi no cambia (97 → 98 % entre las 12).
- Los errores que quedan son pares parecidos (SÍ → SÁBADO en 6 de 8 tomas, ESTUDIAR → CARNE, DOMINGO → DÓNDE, POR-FAVOR → PERMISO): la diferencia entre personas (posición 0.7–1.2, forma 1.0–1.6) es mayor que la diferencia entre esas palabras (0.16 y 0.98).
- Unas 8 tomas del banco no tienen arreglo (4–6 cuadros por segundo, cortadas al final, manos que nunca bajan): el techo real ronda el 96 %.
- Licencia de ASL Citizen: el modelo sigue sin poder ir en la app. Hands-On y el CENAREC completo (1072 videos) no están extraídos en esta máquina.
- La GPU (RTX A500) se recalienta después de ~10 min seguidos y entrena 5 veces más lento. Windows Update reinició la máquina a las 2:47 am y cortó un entrenamiento.

## Lo que faltó por hacer
- [ ] Meta no alcanzada: top-1 ~80 % (meta 95 %). Aceptación errónea 0.8–2.1 % (meta 2 %): en el borde.
- [ ] Avisar al equipo: `DURACION_MAX` es 6 en `meta.constantes` de `senas.db`; la app tiene que usar ese valor.
- [ ] Medir `DURACION_MAX` 6 con deletreo real: una letra sostenida 4–6 s ahora llega al comparador y solo la frenan el umbral y el margen.
- [ ] `descriptores_v3p.npz` se generó con el máximo de 4 s; regenerarlo antes del próximo entrenamiento.
- [ ] `Segmentador._sena` crece sin tope mientras las manos sigan arriba (ya pasaba antes).
- [ ] 4 hallazgos bajos de la fase 3 en `extraer_asl_citizen.py`.

## Siguiente paso
- Decisión de Christian sobre el camino para subir el top-1:
  1. **Plantillas del equipo:** que cada uno grabe las 85 palabras (hoy 30 cada uno) y medir dejando una persona afuera. Es lo único medido que sube mucho y no depende de ninguna licencia.
  2. **Permiso de Microsoft** para usar en la app el modelo entrenado con ASL Citizen, o entrenar con datos LESCO propios (Hands-On + CENAREC completo).
  3. Revisar el criterio de la fase (95 % no es alcanzable con los datos de hoy).
- Medir: `.venv/Scripts/python -m scripts.evaluar_banco_modelo --modelo data/dictionary/asl_citizen/modelo/embedding_v3p.pt --peso 0.7`.
