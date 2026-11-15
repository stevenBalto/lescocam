---
name: ronda-tres
description: Ronda 3 del banco de LESCOCam para los 4 del equipo (problema 1, fase 5). Se activa con "Ronda tres". Pide el nombre antes de todo, dice el modelo y esfuerzo, da las indicaciones y pregunta si está listo; con el sí prepara los videos y abre el grabador donde quedó (2076 palabras, 1 toma). Al terminar o al cerrar, sube sus tomas. Después no se habla más del problema 1.
---

# Ronda tres del banco — los 4 del equipo

Problema 1, fase 5. Cada uno graba **todo el vocabulario (CENAREC + Hands-On) menos las 85 de las rondas 1 y 2: 2076 palabras × 1 toma**. Así cada palabra queda con 4 personas. No hace falta saber LESCO: se imita el video.

**Hablale corto.** Frases de una línea, sin explicar el porqué salvo que pregunte.

## 1. Pedir el nombre (antes de todo)

**No leas archivos, no corras comandos ni resumas nada hasta tener el nombre.** Preguntá solo: «¿Cómo te llamás?».

| Persona | Nombre al grabar | Lista | Carpeta de tomas |
|---|---|---|---|
| Christian Paniagua | `Christian Paniagua` | `data/reference/ronda3/christian.txt` | `data/ronda3/christian-paniagua/` |
| Steven Baltodano | `Steven Baltodano` | `data/reference/ronda3/steven.txt` | `data/ronda3/steven-baltodano/` |
| Reyman Barquero | `Reyman Barquero` | `data/reference/ronda3/reyman.txt` | `data/ronda3/reyman-barquero/` |
| Johan Morales Chacón | `Johan Morales` | `data/reference/ronda3/johan.txt` | `data/ronda3/johan-morales/` |

El «Nombre al grabar» va **exacto**. Si no coincide con nadie, decilo y volvé a preguntar.

## 2. Modelo, esfuerzo e indicaciones

Primero decí, en una línea: **«Para esto alcanza con Sonnet, esfuerzo medio (`/model sonnet` y `/effort medium`).»** Si la sesión está en otro modelo o esfuerzo, decí cuál está activo.

Después mostrá esto **tal cual**:

1. Video a la izquierda (CENAREC o Hands-On), tu cámara a la derecha.
2. Mirá el video. Manos abajo → la seña **una sola vez**, igual al video → manos abajo.
3. **ESPACIO** graba. **G** guarda. **R** repite. **Q** cierra (retoma donde quedaste).
4. **Si sentís que la hiciste igual al video y con las manos dentro del cuadro, guardala.** Con eso alcanza.
5. Si dice **«sin seña»** o **«no vio manos»**: repetila **una vez**. Si vuelve a salir y la hiciste bien, guardala.
6. Si un video no se entiende o no se puede imitar, **N** pasa a la siguiente (queda pendiente).
7. Son 2076 palabras, unas **9–10 horas**. Hacelo en varios días, de 1–2 horas. Cada 10 palabras la pantalla te pide cambiar luz, distancia o ángulo.

Preguntá **con qué cámara** graba: la misma de antes, con el mismo nombre (`iphone13`, `hp-linux`, `laptop-windows`, `laptop`...). Celular: **Iriun Webcam**, celular horizontal y fijo, que se vean hombros y manos.

Terminá con: **«¿Listo para empezar?»**. No empieces sin el sí.

## 3. Preparar (con el sí)

**En todos los comandos:** Windows `.venv/Scripts/python`; Linux `.venv/bin/python`.

1. `git pull`. Si falla o hay conflictos, resolvelo con la persona.
2. **Entorno** (solo si no existe `.venv`): `python -m venv .venv` y `.venv/Scripts/python -m pip install -r requirements-dev.txt`. Sin npm, sin `opencv-python`, sin `requirements-train.txt`.
3. **Videos de referencia** (unos 3.6 GB): tienen que existir `data/dictionary/cenarec/videos/` y `data/dictionary/handson/videos/`, cada uno con su `catalogo.json` al lado.
   - Si faltan: pedile a Christian el zip **`videos_ronda3.zip`** y descomprimilo en la carpeta `lescocam/` (crea `data/dictionary/...`). Trae también `data/dictionary/senas_completa.db`: con eso el motor de su PC queda con las 2161 palabras.
   - Sin zip (lento, horas): `.venv/Scripts/python -m scripts.descargar_cenarec` (sin `--lista` baja todo) y `.venv/Scripts/python -m scripts.descargar_handson --alto 540`.
   - Comprobá: `.venv/Scripts/python -c "from core import banco; from pathlib import Path; from scripts.grabar_banco import catalogo_referencias as c; l=banco.leer_lista(Path('data/reference/ronda3/<nombre>.txt')); print('sin video:', len([p for p in l if p not in c()]))"` → tiene que dar **0** (o pocos: esos se graban igual con N para saltarlos).
4. **Cámara:** probá que abre (`cv2.VideoCapture(0)`; 1, 2 si falla).
5. **Abrir el grabador** en segundo plano (`run_in_background`):
   `.venv/Scripts/python -m scripts.grabar_banco "<Nombre al grabar>" --camara-nombre <cámara> --plan --a-ciegas --tomas 1 --lista data/reference/ronda3/<nombre>.txt --destino data/ronda3`
   (si la cámara no es la 0, agregá `--camara N`). Retoma sola en la primera pendiente. Avisale que mire **«hombros OK | manos detectadas»** en verde antes de grabar.

Mientras graba: solo ayudá con problemas puntuales (encuadre, cámara, programa). **No modifiques código ni otros archivos.**

## 4. Subir (al cerrar con Q o al terminar)

1. En `data/ronda3/` tiene que haber **una sola carpeta de esa persona** (tabla). Si hay otra con su nombre, parate y avisale a Christian.
2. Contá sus tomas: `.venv/Scripts/python -c "from pathlib import Path; print(len(list(Path('data/ronda3/<carpeta>').glob('*.npz'))))"`.
3. Subí **solo su carpeta** `data/ronda3/<carpeta>/`:
   1. **Commit** con el subagente `commits` (español, sin coautores, sin mencionar a Claude), agregando esa carpeta por nombre. Ej.: «Agregar ronda 3 del banco de Steven Baltodano (640 de 2076)».
   2. **`git pull`** (conflictos: resolverlos con la persona).
   3. **Chequeos de `/preparar-push`** y **`git push`**.
4. Decile cuántas le faltan (2076 − tomas). Para seguir otro día: «Ronda tres».
5. Con 2076: «Listo. Christian mide cuando estén los 4.» **No hay nada más que conversar sobre el problema 1** con esta persona. Si es Christian, seguí normal con él.

Si pregunta por sus propios problemas del plan, que use el arranque normal («Hola chat, póngamonos al hilo del proyecto para avanzar»).
