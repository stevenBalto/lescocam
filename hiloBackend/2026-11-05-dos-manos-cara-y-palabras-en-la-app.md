# Sesión 2026-11-04/05 — Palabras de CENAREC, dos manos y cara (problema 3)

**Área:** Backend (core / data / scripts / tests) + conexión en desktop
**Quién:** stevenBalto

## Objetivo de la sesión
- Procesar todos los videos de CENAREC descargados.
- Resolver el problema 3 del plan del equipo (`hiloEquipo/problema-3-steven-baltodano.md`): detectar ambas manos en ≥ 90 % de los cuadros de las 598 señas bimanuales.

## Lo que se hizo
- **CENAREC completo:** 1072 videos extraídos → `data/dictionary/cenarec/senas_todas.db` (1039 palabras, 2138 plantillas, 8,7 MB, fuera de git). Sin repeticiones: CALZONCILLOS, ENTRENADOR, GASTAR.
- Commit del reconocimiento de palabras (`core/cuerpo.py`, `palabras.py`, `reconocedor_palabras.py`, `senas_db.py`, scripts y demo) y del arreglo de mayúsculas de `descargar_cenarec.py`.
- **Fase 1:** modo palabras conectado en la app (Ajustes › Cámara › «Reconocer palabras completas»; Escribir agrega cada palabra; no pausa con los brazos abajo). `scripts/medir_dos_manos.py`: punto de partida **83,1 %**.
- **Fase 2:** `DetectorCuerpo(recorte=True)` (`core/cuerpo.buscar_en_recortes`): si falta una mano se la busca en un recorte alrededor de la muñeca de la pose; no busca en brazos en reposo (velocidad: ~30 fps, peor caso 27). Las 598: **93,5 %**; reconocimiento cruzado top-1 98,2 → 99,2 %. Umbral 0,3 empeora y se descartó. `scripts/probar_deteccion.py` compara configuraciones.
- **Fase 3:** posición de la mano respecto de la nariz, solo cerca de la cara (`VERSION_DESCRIPTOR = 2`). No empeora (1039 palabras: bien 95,3 → 95,4 %; banco 33,3 → 33,3 %). La versión "siempre" empeoraba con otras personas.
- **Fase 4:** RTMW no hizo falta.
- **Extra:** mano dominante en el modo letras (`core/camara.Detector(mano=...)`, Ajustes › «Mano para deletrear»).
- Tests: 296 pasan.

## Lo que faltó por hacer
- [ ] **Pendiente hasta tener TODOS los videos y materiales juntos** (para no re-extraer ni re-entrenar cada vez que se agregan videos):
  - [ ] Re-extraer todos los videos con `DetectorCuerpo(recorte=True)` (versión con el ajuste de reposo) y volver a medir las bimanuales (`probar_deteccion.py --muestra 598 --config recorte_v2`).
  - [ ] Decidir con Christian (problema 1) si su entrenamiento usa la extracción con recorte (ya avisado; falta su respuesta).
  - [ ] Regenerar `data/reference/senas.db` y `senas_todas.db` desde esa extracción.
  - [ ] Volver a medir la cara (fase 3) con la extracción nueva y el banco de las 4 personas; probar `PESO_CARA` 2 y `CARA_RADIO` 0,9.
  - [ ] Las ~32 palabras de CENAREC que faltan (`data/dictionary/cenarec/extra/`; CARRO solo dentro de una oración).
- [ ] Modo único letras + palabras sin interruptor: hablarlo con Johan (problema 2).
- [ ] Probar en vivo: HOLA en modo palabras y «Mano para deletrear» con un zurdo.
- [ ] Grabar el banco de prueba de Steven (30 palabras, `data/reference/banco/steven.txt`; «Vengo de parte de Christian»).
- [ ] Actualizar `.claude/agents/datos-senas.md` y `flutter-movil.md` (senas.db v2, `movimientos.json`, signs.json v3).

## Decisiones y notas
- **Cambio de contrato: afecta a la app móvil.** `senas.db` pasa a `version_descriptor 2`: 83 columnas (por mano: posición 2, rasgos 31, ejes 6, **cara 2**; + marca activa) y `constantes` con `CARA_MODO`, `CARA_RADIO`, `NARIZ_TIPICA`. Formato completo en el encabezado de `core/senas_db.py`. Una base vieja se rechaza (`VersionIncompatible`).
- El formato de landmarks v1 (2 manos + pose) **no cambió**; el recorte cambia los valores extraídos (menos huecos).
- La interpolación de huecos, la muñeca del pose como respaldo y la asignación de manos por la muñeca ya estaban en `core/palabras.py`.
- CENAREC: permiso dado en reunión; falta la confirmación por escrito.

## Siguiente paso
- Grabar el banco de prueba de Steven y, cuando estén todos los videos, correr la lista "Pendiente hasta tener TODOS los videos".
