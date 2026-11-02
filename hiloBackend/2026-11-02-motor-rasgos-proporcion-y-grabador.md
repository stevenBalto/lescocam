# Sesión 2026-11-02 — Motor por rasgos, proporción de cámara y grabador

**Área:** Backend (core / data / scripts / tests)
**Quién:** stevenBalto

## Objetivo de la sesión
- Que el motor reconozca mejor las letras (le costaba "agarrarlas" y más con la mano de lado) y poder sumar tomas propias sin que entren señas mal hechas.

## Lo que se hizo
- Push de la sesión anterior (se configuró `gh auth login` + `gh auth setup-git` para poder subir desde la terminal).
- `scripts/evaluar_motor.py` (nuevo): medición reproducible — validación cruzada por fuente (imagen↔video), robustez a giros 3D (±15/30/45°), cuadro a cuadro simulando cámaras 4:3 y 16:9, video entero por el Aceptador y tomas de webcam contra solo las oficiales.
- `core/rasgos.py` (nuevo): la comparación pasó de coseno sobre posiciones crudas a 31 rasgos de forma (ángulos de flexión, distancias entre puntas, pulgar en el marco de la palma, cruce índice–medio) más una orientación gruesa con poco peso (para no perder Q/P/G/H). `core/clasificador.py` compara por distancia euclídea; confianza `1 − d/2`, `UMBRAL` 0.45.
- Corrección de proporción de imagen (`core/landmarks.py`, `core/camara.py`): antes de normalizar, x·ancho, y·alto, z·ancho. `Detector.procesar` toma el tamaño del propio frame.
- `signs.json` pasó a **version 3**: cada toma tiene `"frame": [ancho, alto]`. `scripts/migrar_v3.py` migra sin regrabar (verificado contra re-procesado real). La carga rechaza otras versiones. Copia v2 en `data/reference/signs.v2.json.bak` (ignorado por git).
- `core/aceptador.py`: estabilidad por tiempo (0.4 s, mínimo 4 frames) en vez de 12 frames; margen 0.10.
- `core/referencia.py` (nuevo): `FUENTES_OFICIALES = ("imagen:", "video:")` y carga solo de oficiales.
- `scripts/recorder.py` (nuevo): grabador con webcam que muestra la imagen oficial al lado y compara cada toma SOLO contra la referencia oficial (✅ aceptada / ⚠️ dudosa / ❌ rechazada); solo se guardan las ✅, con `source: webcam:<persona>` y `frame`.
- Grabadas 15 tomas `webcam:steven` (5 de A, B y C). Probado en vivo: A, B y C se reconocen mucho mejor.
- Importadores de imágenes y video actualizados a v3.
- Resultados (antes → después): cruzada entre personas 56–68% → 84–87%; giro 45° 23% → 82%; webcam 4:3 70% → 86% y 16:9 53% → 86% cuadro a cuadro; letras inventadas → 0.
- Tests: 168 pasan.

## Lo que faltó por hacer
- [ ] Grabar el resto del alfabeto por tandas (E S M N T · R U V K · I Y D O · F G H CH L W · P Q X al final), 5 tomas por letra.
- [ ] Que los compañeros graben con `scripts/recorder.py --persona <nombre>`.
- [ ] Resolver las letras contradictorias entre imagen y video (P, Q, X, F/T), idealmente con alguien que sepa LESCO.
- [ ] Siguen confusiones P→H, M→S, U→R, H→K entre imagen y video.
- [ ] Actualizar el formato de `signs.json` (v3, `frame`) en `.claude/agents/datos-senas.md` y `.claude/agents/flutter-movil.md`.
- [ ] `data/dictionary/secuencias_video.json` sigue en v2; agregar a `importar_video` una opción para regenerar solo las secuencias.
- [ ] Medir `MAX_DISPERSION` del grabador con manos reales.
- [ ] App de escritorio: mostrar la letra que cree ver y una barra hasta confirmarla; avisos de mano lejos o poca luz.
- [ ] Conectar "Enseñar una seña" y "Práctica" (hoy son solo diseño; Práctica dice "¡Bien hecha!" sin mano).
- [ ] Separar números de letras (2~V, 5~L, 6~W): modo números/deletreo.
- [ ] Soporte de movimiento (J, LL, Ñ, RR, Z y palabras): SQLite + ventana de frames + DTW; dos manos y posición respecto a la cara para palabras.
- [ ] Pedir permiso de uso a la página oficial de LESCO (imágenes) y a Hands-On! (video) antes de publicar.
- [ ] Anotar en `desktop/README.md` los comandos de Linux y la dependencia `libxcb-cursor0`.
- [ ] Instalar Flutter para la app móvil.
- [ ] Cada compañero: activar el hook con `git config core.hooksPath .githooks`.
- [ ] Completar "Curso" y "Equipo" en el README.

## Decisiones y notas
- Cambio de contrato: afecta a la app móvil. `signs.json` es ahora `"version": 3` (rechazar otras versiones) y cada toma lleva `"frame": [ancho, alto]`. Normalización: x·ancho, y·alto, z·ancho sobre el frame espejado → restar muñeca (0) → dividir por distancia muñeca→punto 9 → si la mano es "Left", invertir x. Comparación: `rasgos()` (31 valores, ver `core/rasgos.py`), distancia euclídea, confianza `1 − d/2` recortada a [0,1], mejor toma por letra. Aceptador: `UMBRAL` 0.45, `MARGEN` 0.10, 0.4 s estables con mínimo 4 frames, repetir la misma letra cada 1.5 s.
- Datos en dos niveles: la referencia oficial (imágenes y videos de profesionales) define cómo es la seña; nuestras grabaciones solo aportan variedad y entran únicamente si coinciden con la oficial. No definimos señas nuevas: una letra sin referencia oficial no se puede grabar.
- No se bajó el umbral a ciegas: el que separa letras parecidas es el margen; con margen 0.08 ya aparecían letras inventadas.
- La proporción de la cámara explicaba gran parte de los fallos en vivo: la misma mano quedaba estirada distinto en 640x480, 612x720 o 16:9.
- Para usar el grabador hay que cerrar la app de escritorio (comparten la cámara).

## Siguiente paso
- Grabar la tanda 1 (E S M N T) con `.venv/bin/python -m scripts.recorder E S M N T --persona steven` y medir con `scripts/evaluar_motor.py`.
