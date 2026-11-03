# Sesión 2026-11-03 — Letras con movimiento y diccionario de CENAREC

**Área:** Backend (core / data / scripts / tests)
**Quién:** stevenBalto

## Objetivo de la sesión
- Reconocer las letras con movimiento (J, LL, Ñ, RR, Z) y empezar con palabras completas usando el Diccionario LESCO de CENAREC.

## Lo que se hizo
- `core/movimiento.py` (nuevo): formato de `data/reference/movimientos.json`, segmentación del gesto, descriptor (forma 31 rasgos + orientación + trayectoria del centro de la palma relativa al tamaño de la mano), remuestreo a 20 muestras y DTW (banda 0.3). Acepta con confianza ≥ 0.5 y margen 0.1.
- `core/reconocedor.py` (nuevo): combina quietas y movimiento. Evita disparos por temblor; demora 0.5 s las posturas de partida (I, L, N, R, X) por si siguen en movimiento (LL y no L + LL); calla las quietas después de un gesto.
- `data/reference/movimientos.json` (nuevo, 128 KB): plantillas de J, LL, Ñ, RR y Z sacadas del video de Hands-On!.
- `desktop/motor.py`: usa `Reconocedor.desde_archivos()`; la API de la UI no cambia.
- `scripts/importar_video.py --solo-movimientos`, `scripts/recorder.py` graba letras con movimiento, `scripts/evaluar_movimiento.py` (nuevo).
- Resultados: 100/100 variantes de prueba correctas; 0 letras inventadas con temblor, transiciones o el video entero; las quietas siguen igual (25/25 y 17/25). Costo: I, L, M, N, Q, R, X tardan hasta 0.6 s más.
- Diccionario LESCO de CENAREC: 1104 palabras, un MP4 por palabra (640x360, ~10 s, ~1.3 MB, una persona de frente, fondo azul, la seña repetida dos veces). `scripts/descargar_cenarec.py` (nuevo) descarga de a un pedido con pausa y retoma si se corta. Descarga completa lanzada a `data/dictionary/cenarec/` (ignorado por git).
- Tests: 225 pasan.

## Lo que faltó por hacer
- [ ] Probar en vivo las letras con movimiento (app, pantalla Escribir) y grabar las propias: `.venv/bin/python -m scripts.recorder J LL Ñ RR Z --persona steven`.
- [ ] Confirmar por correo el permiso de CENAREC y guardarlo.
- [ ] Procesar los videos de CENAREC (con `motor-vision`): dos manos + cuerpo/cara (posición de la seña), separar las dos repeticiones, guardar en SQLite (`senas.db`), reconocedor de palabras. Empezar con 50–100 palabras comunes y medir.
- [ ] Limitaciones del movimiento: una sola persona de referencia; sostener la L más de ~0.9 s da "L" y luego "LL"; una Z chica igual se acepta; la plantilla de Z no tiene la raya de abajo completa.
- [ ] El Aceptador repite cada 1.5 s una letra sostenida (en el video cada letra sale 2–3 veces).
- [ ] Borrar `data/dictionary/secuencias_video.json` (obsoleto).
- [ ] Actualizar `.claude/agents/datos-senas.md` y `flutter-movil.md` con v3, `frame`, `categoria`, `sintetica:` y `movimientos.json`.
- [ ] Pendientes de la sesión anterior: tanda 4 (F G H CH L W), números con el grabador, P Q X, M R K (dedos tapados), N oficial de imagen inconsistente, compañeros grabando, UI (modo números, letra en curso, Práctica y Enseñar), permisos de LESCO oficial y Hands-On!, README Linux, Flutter, hook, Curso/Equipo.

## Decisiones y notas
- Cambio de contrato: afecta a la app móvil. Archivo nuevo `data/reference/movimientos.json` (`version: 1`, `version_vector: 3`): por letra `categoria`, `tipo: "movimiento"` y tomas con `source`, `recorded_at`, `fps`, `frame`, `inicio`/`fin` y `cuadros` (`t`, `lado`, `muneca` [x, y] px, `escala` px, `vector` 63). Formato completo y constantes en los encabezados de `core/movimiento.py` y `core/reconocedor.py`. `signs.json` no cambió.
- Para 5 letras con movimiento alcanza un JSON aparte; SQLite queda para las palabras.
- CENAREC: su `robots.txt` declara `ai-train=no` y bloquea robots de IA. El usuario informa que CENAREC autorizó el uso en una reunión por Meet; falta la confirmación por escrito. Los videos no se versionan ni se redistribuyen.
- Para ahorrar tokens: `/clear` y `/retomar backend` al volver; el procesamiento de palabras con `motor-vision` es caro, conviene hacerlo por partes.

## Siguiente paso
- Revisar que la descarga de CENAREC haya terminado (`data/dictionary/cenarec/catalogo.json`) y elegir 50–100 palabras comunes para el primer procesamiento con `motor-vision`.
