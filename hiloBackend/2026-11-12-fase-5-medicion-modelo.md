# Sesión 2026-11-12 — Fase 5 (parcial): modelo + DTW medidos en el banco

**Área:** Backend (core / data / scripts / tests)
**Quién:** Christian Paniagua Castro

## Objetivo de la sesión
- Fase 5 del problema 1: sumar el modelo de señas al DTW y medir contra el banco (meta ≥ 95 % top-1, ≤ 2 % aceptación errónea).

## Lo que se hizo
- ASL Citizen completo: 35 458 videos más (50 458 en total, 0 errores, 7 h 18 min). `landmarks_v1.npz` 620 MB; `descriptores_v3p.npz` 84 317 descriptores con puntos de la mano (209 columnas). Todo en `data/dictionary/asl_citizen/` (ignorado por git).
- `core/palabras.py`: `CuadroPalabra.puntos` (21 puntos normalizados por mano). Aditivo: descriptor y `senas.db` sin cambios.
- `scripts/entrada_modelo.py` (entrada del modelo, plantillas CENAREC con puntos) y `scripts/evaluar_banco_modelo.py` (DTW / modelo / suma contra el banco, validación cruzada christian+steven ↔ reyman+johan).
- Modelo `embedding_v3p.pt` (25 épocas). Glosas nuevas de ASL: modelo 59 %, suma 61 % (peso 0.7, elegido con ASL).
- Banco (240 tomas), suma peso 0.7:
  - DURACION_MAX 4: top-1 79.2 %, top-3 91.2 %, validación: dice bien 38.8 %, errónea 5.0 %.
  - DURACION_MAX 6: top-1 82.9 %, top-3 95.0 %, validación: dice bien 42.9 %, errónea 5.0 %.
- `tests/test_fase5_modelo.py`: 17 tests (suite 396). Revisión Sonnet alto: se arregló un bug alto (etiquetas sin plantilla del modelo daban −inf → NaN en z) y el redondeo del umbral. Commit `96b15fc`.

## Lo que faltó por hacer
- [ ] Meta no alcanzada: top-1 83 % (meta 95 %), errónea 5 % (meta 2 %).
- [ ] DURACION_MAX 4 → 6 sin aplicar (cambio de contrato de `senas.db`, se aplica una sola vez con el rediseño).
- [ ] Hallazgo medio de la revisión: con puntos, `entrenar_embedding` compara CENAREC contra otro conjunto (solo `LISTA`) que sin puntos.
- [ ] 4 hallazgos bajos de la fase 3 en `extraer_asl_citizen.py`.

## Decisiones y notas
- Licencia de ASL Citizen (`use.txt` en el zip): solo investigación no comercial, prohibido distribuir los datos o sus modificaciones. El modelo entrenado con ASL NO va en la app; sirve para investigar (elegir arquitectura y rasgos).
- Reemplazo para la app: PopSign ASL v1.0 (CC BY 4.0, 250 señas, Georgia Tech) y tomas LESCO del equipo (Christian: cada uno puede grabar muchas más).
- Erróneas: el umbral ajustado con reyman+johan (más fáciles, 88 % top-1) deja pasar 10 % de errores en christian+steven (77 %). Hay que calibrar mejor la aceptación.
- Confusiones por forma de la mano: MAMÁ→BAÑO, MIÉRCOLES→MARTES, POR-FAVOR→PERMISO.
- Christian aprobó usar Fable (reinicio gratis) para el rediseño.

## Siguiente paso
- Rediseño con Fable (esfuerzo alto):
  1. Aceptación: exigir que DTW y modelo coincidan en la 1.ª; ajustar dejando una persona afuera (4 rondas), quedarse con el umbral más estricto.
  2. Forma de la mano: negativos difíciles en el entrenamiento (pares confundidos), más peso a los puntos.
  3. Licencia: entrenar con PopSign (CC BY 4.0) + tomas LESCO del equipo en vez de ASL Citizen.
- Medir con `.venv/Scripts/python -m scripts.evaluar_banco_modelo --modelo <pt> --peso 0.7` (DURACION_MAX 6 hoy se prueba parcheando `Segmentador.__init__.__defaults__`).
