# Sesión 2026-11-01 — Alfabeto desde imágenes y video

**Área:** Backend (core / data / scripts / tests)
**Quién:** stevenBalto

## Objetivo de la sesión
- Cargar el alfabeto de LESCO en `signs.json` a partir de material de referencia (imágenes y un video) en vez de grabarlo a mano.

## Lo que se hizo
- `git pull` del PR #1 (interfaz de escritorio, cámara, voz). Instalado PySide6 6.12.0 en `.venv` (`pip-audit`: sin vulnerabilidades). En Linux hizo falta `sudo apt install libxcb-cursor0` para que Qt abra ventanas.
- Revisado el motor actual: MediaPipe → 21 puntos → vector de 63 normalizado (`core/landmarks.py`) → similitud de coseno contra las tomas (`core/clasificador.py`, umbral 0.92) → `core/aceptador.py` (10 frames seguidos y margen 0.02).
- Las 11 letras que había (grabadas a mano) no coincidían con la referencia: D, I y la `c` salían como otras letras. Se reemplazaron.
- `scripts/importar_imagenes.py`: importa una carpeta de imágenes (una por seña, el nombre del archivo es la etiqueta). Sin `--guardar` solo prueba; `--reemplazar` borra lo anterior; los números se saltan salvo con `--numeros`.
- Importadas 25 letras quietas desde imágenes (A–Y, con CH): 1 toma cada una.
- `scripts/importar_video.py`: corta un video del abecedario en tramos según el rótulo azul que cambia en pantalla y los asigna en orden del alfabeto (sin OCR). Usa solo el primer plano de la mano (mitad izquierda). Las letras quietas dan 3 tomas cada una (promedio del centro del tramo); las de movimiento se guardan como secuencias aparte.
- Importado el video "Abecedario en LESCO" (Hands-On!): +75 tomas. `signs.json` queda con 25 letras y 100 tomas (1 de imagen + 3 de video por letra).
- Secuencias de J, LL, Ñ, RR y Z guardadas en `data/dictionary/secuencias_video.json` (ignorado por git).
- Tests: 113 pasan.

## Lo que faltó por hacer
- [ ] Mejorar la comparación del motor: confunde letras parecidas (R~U 0.98, M~N 0.98, U~V, A~S, D~C~O, K~U). Probar ángulos de dedos y distancias entre puntas en vez de posiciones crudas (`motor-vision`).
- [ ] Probar en vivo con varias personas y anotar qué letras reconoce y cuáles no.
- [ ] Separar números de letras: 2~V, 5~L, 6~W tienen la misma forma. Hace falta un modo números/deletreo antes de importar 1–9.
- [ ] Soporte de señas con movimiento (letras J, LL, Ñ, RR, Z y palabras como HOLA): ventana de frames + DTW. Antes de grabarlas, pasar el almacenamiento a SQLite (`senas.db`).
- [ ] Escribir `scripts/recorder.py` para sumar tomas con la webcam (otras manos y ángulos).
- [ ] Pedir permiso de uso a la página oficial de LESCO (imágenes) y a Hands-On! (video) antes de publicar la app.
- [ ] Anotar en `desktop/README.md` los comandos de Linux y la dependencia `libxcb-cursor0`.
- [ ] Instalar Flutter para la app móvil.
- [ ] Cada compañero: activar el hook con `git config core.hooksPath .githooks`.
- [ ] Completar "Curso" y "Equipo" en el README.

## Decisiones y notas
- Cambio de contrato: afecta a la app móvil. El formato de `signs.json` es el mismo (`version: 2`, `signs` → `takes` → `vector`), pero las etiquetas cambiaron (`c` pasó a `C`, se agregaron CH, F, G, K, M, N, P, Q, R, S, T, U, W, X) y cada toma tiene un campo nuevo opcional `source` (`imagen:...` o `video:...`).
- Almacenamiento: las señas de referencia se quedan en `signs.json` dentro del repo mientras sean solo posturas quietas. Se pasa a SQLite al empezar con movimiento. Los datos de cada usuario (señas propias, historial, ajustes) van en su carpeta de datos, nunca en el repo.
- Las imágenes y el video de referencia están en `data/dictionary/` (ignorado por git): no se versionan ni se redistribuyen. Cada compañero que quiera reimportar tiene que bajarlos.
- El ángulo de cámara importa: la P de la imagen (de costado) no coincide con la del video (de frente). El video se parece más al uso real con webcam.
- OCR no hace falta para videos con rótulo: alcanza con detectar el cambio del rótulo y usar el orden del alfabeto.
- Para bajar videos de YouTube: `yt-dlp` (con pipx, `yt-dlp[default]`) y `--js-runtimes node`.

## Siguiente paso
- Juntar los resultados de las pruebas en vivo de los compañeros y arrancar con `motor-vision` la mejora de la comparación para letras parecidas.
