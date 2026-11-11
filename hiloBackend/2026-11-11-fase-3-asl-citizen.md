# Sesión 2026-11-11 — Fase 3: datos de ASL Citizen

**Área:** Backend (core / data / scripts / tests)
**Quién:** Christian Paniagua Castro

## Objetivo de la sesión
- Cerrar la Fase 3 del problema 1: tener un archivo de landmarks v1 de ASL Citizen listo para entrenar.

## Lo que se hizo
- Descarga de ASL Citizen (45 924 134 223 bytes, tamaño exacto) a `data/dictionary/asl_citizen/`.
- `scripts/extraer_asl_citizen.py`: lee los videos directo del zip, muestra estratificada de 15 000 (solo train y val), 4 procesos, reanudable, `DetectorCuerpo(recorte=True)`.
- `scripts/construir_landmarks_asl.py`: arma `landmarks_v1.npz` (float16 + offsets) y `cargar()`.
- `tests/test_asl_citizen.py`: 17 tests. Suite completa: 355 pasan.
- Revisión (Sonnet alto): sin hallazgos graves. Se arregló el mmap inútil en `.npz`; `cargar()` lee todo a RAM (~0.6 GB).
- Extracción real: 15 000 videos, 0 errores, 2 h 02 min (0.49 s/video, no las 8-10 h estimadas). 2 731 glosas, 41 firmantes.
- `landmarks_v1.npz`: 674 722 cuadros, 190 MB. Cuerpo en 99.88 %, alguna mano 43 %, dos manos 20 %.
- Fase 3 tachada y subida (commit `56285d8`).

## Lo que faltó por hacer
- [ ] 4 hallazgos bajos de la revisión en `extraer_asl_citizen.py` (JSON atómico, temporal huérfano si se mata el proceso, `maxtasksperchild`, filtrar `USABLES` al reusar `muestra.json`). No urgen: la extracción ya terminó.
- [ ] Christian: avisar al equipo del contrato `senas.db` v3 y a Steven de `buscar_en_recortes` (pendientes de antes).

## Decisiones y notas
- ASL no es LESCO: los datos sirven para aprender variación entre firmantes y formas de mano, no vocabulario. Que transfiera a LESCO es una apuesta; lo mide la Fase 5 contra el banco.
- Licencia (solo investigación no comercial): `data/dictionary/` está ignorado por git; al terminar la investigación se borra `data/dictionary/asl_citizen/` (zip, extracción y `landmarks_v1.npz`). Christian aceptó la licencia.
- `--alto-max 480` no cambió la detección (los videos ya son chicos).
- Pendiente de decidir en Fase 4: si el modelo entrenado se sube a git (la licencia no lo aclara).
- Subagentes del proyecto (`commits`, `escritor-pruebas`, `revisor-codigo`) no cargan en esta sesión; se usaron agentes genéricos con el modelo y esfuerzo de la matriz.

## Siguiente paso
- Fase 4: entrenar el embedding sobre `landmarks_v1.npz` en la RTX A500 y reconocer por búsqueda vectorial contra las plantillas de CENAREC. Requiere Opus 5.5 con esfuerzo alto (Christian lo habilita). Primero confirmar el diseño con él.
