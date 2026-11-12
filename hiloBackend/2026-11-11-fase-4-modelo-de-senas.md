# Sesión 2026-11-11 — Fase 4: modelo de señas por similitud

**Área:** Backend (core / data / scripts / tests)
**Quién:** Christian Paniagua Castro

## Objetivo de la sesión
- Cerrar la Fase 4 del problema 1: un modelo que entrena y reconoce señas de CENAREC por similitud.

## Lo que se hizo
- PyTorch 2.14.1 con CUDA 13 en `.venv` (`requirements-train.txt`, aparte: la app y el escritorio no lo necesitan). torch 2.11 se descartó porque exige setuptools < 82, que tiene fallas conocidas. pip-audit limpio.
- `scripts/descriptores_asl.py`: cada video de ASL pasa por `cuadro_palabra` → `Segmentador` → descriptor v3 crudo (24 × 83), igual que CENAREC y el banco. 14 950 de 15 000 videos dan seña; 25 036 descriptores (variantes de espejo).
- `scripts/modelo_senas.py`: red convolucional temporal (0,44 M parámetros) → vector de 128, ArcFace.
- `scripts/entrenar_embedding.py`: separa 410 glosas que nunca se entrenan, elige la época con A, evalúa A/B/CENAREC y compara con el DTW del motor y con la suma de los dos.
- Resultados (modelo en `data/dictionary/asl_citizen/modelo/`, ignorado por git):
  - CENAREC: modelo 100 %, DTW 98.8 %.
  - Glosas nuevas con personas nuevas (410 glosas, 1 video de referencia): DTW 38 %, modelo 44 %, modelo + DTW 47 %.
- `tests/test_modelo_senas.py`: 24 tests (suite 379). Revisión con Sonnet alto: sin hallazgos graves; se aplicaron los 4 bajos (galería de A solo de train, submuestra al azar para el DTW, corrección de ArcFace con theta + m > pi, docstring).
- Fase 4 tachada en `hiloEquipo/problema-1-christian-paniagua.md`.

## Lo que faltó por hacer
- [ ] 4 hallazgos bajos de la revisión de la fase 3 en `extraer_asl_citizen.py` (no urgen).

## Decisiones y notas
- Christian aceptó cerrar la fase con la mejora moderada y medir en la fase 5; si no alcanza, se itera.
- Con más épocas sobreajusta (pérdida ~0). El límite son los datos: ~4 videos por glosa. Siguiente palanca: extraer los ~28 mil videos de train de ASL Citizen que faltan (~4 h).
- El modelo sale de ASL Citizen: no se sube a git ni se distribuye hasta revisar la licencia (decisión de Christian). Antes de meterlo en la app hay que resolverlo.
- Se ofreció Fable; se guarda para la fase 5 si hace falta rediseñar a fondo.

## Siguiente paso
- Fase 5: conectar el modelo (sumado al DTW, z por consulta) al comparador y medir contra el banco con `scripts/evaluar_banco.py` (hoy DTW: top-1 64.2 %, errónea 0.4 %). Meta ≥ 95 % top-1 y ≤ 2 % errónea. Ajustar umbral y margen con validación cruzada entre personas (christian+steven / reyman+johan).
