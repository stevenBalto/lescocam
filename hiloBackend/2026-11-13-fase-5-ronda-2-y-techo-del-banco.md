# Sesión 2026-11-13 — Fase 5: medición con la ronda 2 y techo del banco

**Área:** Backend (core / data / scripts / tests)
**Quién:** Christian Paniagua Castro

## Objetivo de la sesión
- Con las 85 palabras grabadas por los 4 (680 tomas), medir el motor usando de plantilla las tomas de las otras personas y ver si alcanza la meta del problema 1 (≥ 95 % top-1, ≤ 2 % aceptación errónea).

## Lo que se hizo
- Ronda 2 completa: 170 tomas por persona (`scripts/registrar_banco.py --estado`).
- `scripts/evaluar_banco_cruzado.py` (nuevo): deja una persona afuera por ronda; plantillas = `cenarec` (senas.db), `equipo` (las otras 3 personas) o `todo`. Reglas de aceptación del motor, sin ajustar nada.
- Resultados sobre las 680 tomas (top-1 / top-3):

| Método | top-1 | top-3 | ¿puede ir en el producto? |
|---|---|---|---|
| Motor de hoy (DTW, plantillas CENAREC) | 70.4 % | 88.2 % | sí (errónea 0.4 %, dice bien 30.6 %) |
| DTW con plantillas CENAREC + las otras 3 personas (`todo`) | 72.4 % | 90.1 % | sí (errónea 3.1 % con los umbrales de hoy) |
| DTW solo con las otras 3 personas, sin CENAREC (`equipo`) | 69.0 % | 88.4 % | sí (errónea 3.4 %, dice bien 40.0 %) |
| Modelo entrenado desde cero con las tomas del equipo + DTW | 77.5 % | — | sí |
| Modelo de ASL Citizen + DTW (laboratorio) | 85.3 % | 96.3 % | no (licencia) |
| La otra toma de la MISMA persona como plantilla, DTW | 88.8 % | — | (techo, no es un método) |
| Ídem con el modelo de laboratorio + DTW | 93.2 % | — | (techo, no es un método) |

## Lo que se midió y se descartó
- Plantillas del equipo sumadas a las de CENAREC, con DTW: +2 puntos (70.4 → 72.4 %); solas rinden menos que CENAREC (69.0 %). Parte de la subida de la errónea (0.4 → 3.1 %) puede venir de que, con más plantillas por palabra, la duración mínima exigida baja. La mejor variante (media de las 3 más cercanas, CENAREC × 0.9) llega a 75 %. La ganancia de las 12 palabras del núcleo (82 → 92 %) no se sostuvo con las 85.
- Galería del equipo para el modelo de laboratorio: no suma (85 %). Afinarlo con las tomas del equipo: no suma (83 %).
- Desempate por pares entre las 3 primeras con pesos aprendidos de las plantillas: empeora (85 → 79 %).
- Más muestras por seña (16, 32, 48 en vez de 24): igual (69–70 %).
- Plantilla de dos manos forzada cuando la mano de apoyo queda baja: +0.6 puntos. BUENO (0 de 8) y TRABAJAR (2 de 8) fallan porque la plantilla del CENAREC quedó de una mano (la mano de apoyo está bajo el umbral de reposo) y las 4 personas la hicieron con dos.
- Simulación de entrenar con LESCO propio (CENAREC + Hands-On = 2 personas, muchas señas): con solo los 2 firmantes de ASL Citizen con más videos (2321 glosas, 8601 filas) el modelo + DTW da 66 % en el banco de 240, igual que el DTW solo. Lo que hace bueno al modelo es la variedad de personas (52), no solo la cantidad de señas.

## Decisiones y notas
- **El banco tiene un techo de ~93 %.** Ni usando la otra toma de la misma persona (grabada segundos antes, misma luz) se llega a 95 %: entre el 7 y el 11 % de las tomas no se parece ni a su gemela. La meta de 95 % top-1 no es alcanzable sobre este banco con ningún método.
- Los errores del mejor método están concentrados: 20 palabras tienen 75 de los 100 errores; pares fijos (SÍ → SÁBADO, TRABAJAR → AÑO, DOMINGO → DÓNDE, POR-FAVOR → PERMISO, MARTES/MIÉRCOLES/SÁBADO, CARNE ↔ ESTUDIAR).
- La detección de manos explica poco: con cobertura ≥ 80 % el acierto es 87 %; con < 50 % baja a 62 % (21 tomas).
- WLASL (2000 señas, 119 personas, licencia C-UDA): sin confirmar si permite usar el modelo en una app; una ficha dice "sin uso comercial".
- `scripts/grabar_banco.py` tiene un cambio local sin subir (el video de referencia corre a velocidad real); no es de esta sesión, no se tocó.

## Lo que faltó por hacer
- [ ] Decisión de Christian sobre cómo seguir (abajo).
- [ ] Reajustar umbral y margen si entran plantillas del equipo (la errónea sube a 3.1 % con los de hoy).
- [ ] Arreglar las plantillas de BUENO y TRABAJAR (mano de apoyo baja).
- [ ] Pendientes anteriores: avisar al equipo de `DURACION_MAX` 6, medirlo con deletreo real, `descriptores_v3p.npz` generado con el máximo de 4 s.

## Siguiente paso
- Presentar a Christian el techo del banco y las opciones:
  1. Producto con lo que sí se puede usar: modelo entrenado con tomas del equipo + DTW (77.5 %), diciendo la palabra solo cuando está seguro y mostrando 3 opciones cuando no (la correcta está entre las 3 primeras el 88–90 %).
  2. Más personas grabando las 85 palabras (medir antes cuánto sube con 1, 2 y 3 personas de entrenamiento para saber cuántas harían falta).
  3. Buscar un conjunto con muchas personas y licencia que permita usar el modelo en la app (verificar WLASL C-UDA, Slovo, otros).
  4. Reescribir el criterio de la fase 5 con el techo medido.
- Medir: `.venv/Scripts/python -m scripts.evaluar_banco_cruzado` (DTW, ~10 min).
