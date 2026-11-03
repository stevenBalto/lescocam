# Sesión 2026-11-02 — Sintéticas, números y tomas propias

**Área:** Backend (core / data / scripts / tests)
**Quién:** stevenBalto

## Objetivo de la sesión
- Grabar tomas propias del alfabeto por tandas, agregar datos sintéticos ("nivel 1") y cargar los números.

## Lo que se hizo
- Grabadas con `scripts/recorder.py` (5 tomas c/u, `webcam:steven`): A, B, C, D, E, I, N, O, S, T, U, V, Y → 13 de 25 letras.
- El grabador ahora imprime cada intento con su top-3 en la terminal (sirve para diagnosticar letras que no pasan).
- `core/sinteticas.py` + `scripts/generar_sinteticas.py`: tomas sintéticas deterministas SOLO desde tomas oficiales (flexión de nudillos MCP +10°/−5°); se descartan si no quedan primeras con margen ≥ 0.25. 188 sintéticas guardadas en `signs.json` (`source: "sintetica:..."`). Los importadores las regeneran solos.
- Variaciones probadas y descartadas por empeorar o no aportar: giros 3D, largo de dedos/palma, flexión de falanges.
- Números 1–9 importados desde las imágenes oficiales con `"categoria": "numero"`. `Clasificador(categoria=...)` filtra; por defecto "letra", así el deletreo no confunde 2 con V. No chocan entre sí (más cercano 4~6).
- Resultados con sintéticas: cruzada imagen→video 86.7 → 88.0 %, aceptadas 61 → 68 %, flujo del video 16 → 17 de 25, 0 inventadas. Mejora chica: lo que más ayuda son datos reales de personas distintas.
- Commits `23375ce` (y antes `0ba6fc1`, `fb06b49`, `8fc5b7a`), todo subido a GitHub. 190 tests pasan.

## Lo que faltó por hacer
- [ ] Grabar tanda 4: F, G, H, CH, L, W (ojo: F y T oficiales se contradicen).
- [ ] Grabar los números 1–9 con el grabador.
- [ ] Grabar P, Q, X (referencias contradictorias entre imagen y video).
- [ ] M, R, K no pasan el control: MediaPipe no ve los dedos tapados (M → la ve como H/I; R → U; K → V). Llevar a `motor-vision`: probar profundidad (z) de las puntas para el cruce de la R, posición del pulgar para K y M.
- [ ] La N oficial de la imagen se reconoce como M: revisar/limpiar esa toma.
- [ ] Que los compañeros graben con `--persona <nombre>` (lo que más mejora el motor).
- [ ] Medir "persona nueva" sin sesgo con una grabación de otra persona que no pase por el filtro.
- [ ] Escritorio: modo números en la interfaz (`Clasificador(categoria="numero")` ya está listo); mostrar la letra que ve y una barra hasta confirmar; conectar Práctica y Enseñar una seña.
- [ ] Actualizar `.claude/agents/datos-senas.md` y `flutter-movil.md` con v3, `frame`, `categoria` y `sintetica:`.
- [ ] Pendientes anteriores que siguen: movimiento (SQLite + DTW), permisos de uso (LESCO oficial y Hands-On!), README de escritorio para Linux, Flutter, hook de cada compañero, Curso/Equipo en el README.

## Decisiones y notas
- Cambio de contrato: afecta a la app móvil. Campo opcional `"categoria"` por seña ("letra" por defecto | "numero"): comparar solo dentro de la categoría del modo. Las tomas `"sintetica:"` se usan como cualquier toma (no hay que generarlas en Dart). El control de calidad compara solo contra oficiales (`imagen:`/`video:`).
- El personaje 3D en Blender ("nivel 2") queda solo como experimento para R/K/M si lo anterior no alcanza. La laptop (7 GB RAM, gráfica integrada) lo correría justo y sin ventana (`blender --background`), sin MCP.
- Mientras un subagente modifica `signs.json`, no grabar (se pisan los cambios).

## Siguiente paso
- Cerrar la app y grabar la tanda 4: `.venv/bin/python -m scripts.recorder F G H CH L W --persona steven`.
