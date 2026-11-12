---
name: ronda-dos
description: Ronda 2 del banco de LESCOCam para los 4 del equipo (problema 1, fase 5). Se activa con "Ronda dos". Pide el nombre antes de todo, muestra las 55 palabras que le faltan a esa persona, da los pasos y pregunta si está lista; con el sí prepara todo y abre el grabador donde quedó. Al terminar registra las tomas y las sube. Después no se habla más del problema 1.
---

# Ronda dos del banco — los 4 del equipo

Problema 1, fase 5 (`hiloEquipo/problema-1-christian-paniagua.md`). En la ronda 1 cada uno grabó 30 palabras. Ahora cada uno graba **las 55 que le faltan × 2 tomas**, para que las 85 queden grabadas por los 4. Con eso se mide a cada persona usando de plantilla las tomas de las otras tres. No hace falta saber LESCO.

**Hablale corto.** A nadie del equipo le gusta leer: frases de una línea, sin explicar el porqué salvo que pregunten.

## 1. Pedir el nombre (antes de todo)

**No leas archivos, no corras comandos ni resumas nada hasta tener el nombre.** Preguntá solo: «¿Cómo te llamás?».

Buscá a la persona (sin distinguir mayúsculas ni tildes; alcanza con el nombre de pila):

| Persona | Nombre al grabar | Lista | Cámara de la ronda 1 |
|---|---|---|---|
| Christian Paniagua | `Christian Paniagua` | `data/reference/banco/christian.txt` | `iphone13` |
| Steven Baltodano | `Steven Baltodano` | `data/reference/banco/steven.txt` | `hp-linux` |
| Reyman Barquero | `Reyman Barquero` | `data/reference/banco/reyman.txt` | `laptop-windows` |
| Johan Morales Chacón | `Johan Morales` | `data/reference/banco/johan.txt` | `laptop` |

El «Nombre al grabar» tiene que ser **exactamente** ese: así las tomas nuevas caen en la misma carpeta que las de la ronda 1. Si el nombre no coincide con nadie, decilo y volvé a preguntar.

## 2. Ponerse al día

`git pull`. Si falla o hay conflictos, parate y resolvelo con la persona antes de seguir.

**En todos los comandos de esta skill:** Windows usa `.venv/Scripts/python`; Linux, `.venv/bin/python`.

**Entorno** (solo si no existe `.venv`): `python -m venv .venv` y `.venv/Scripts/python -m pip install -r requirements-dev.txt` (Linux: `python3 -m venv .venv` y `.venv/bin/python -m pip install -r requirements-dev.txt`). Python 3.12 o superior. No uses npm; no instales `opencv-python`; no instales `requirements-train.txt` (no hace falta).

Después corré `.venv/Scripts/python -m scripts.registrar_banco "<Nombre al grabar>"`:
- Si dice «Completo: 170 tomas», decile que ya terminó y no sigas.
- Si dice que faltan tomas (lo normal), la línea «Faltan tomas: …» trae las palabras pendientes: de ahí sale cuántas le faltan.

## 3. Mostrar sus palabras y los pasos

Leé su lista y mostrá **solo lo que está después de la línea `RONDA 2`**: las tandas 4 a 9 (10 palabras cada una, la última 5), una línea por tanda. Si ya grabó una parte, decile cuántas palabras le faltan.

Después, estos pasos, **tal cual y sin agregar texto**:

1. Es igual que la vez pasada: video del CENAREC a la izquierda, tu cámara a la derecha.
2. Manos abajo → la seña **una sola vez**, al ritmo del video → manos abajo.
3. **ESPACIO** graba. **G** guarda. **R** repite.
4. **Antes de guardar, fijate que la hiciste bien**: igual al video y con las manos dentro del cuadro. Si no, **R**.
5. **Si la hiciste bien, guardala aunque el programa diga «no se decide» u otra palabra.** Eso no es tu error. Repetir solo las que fallan arruina la medición.
6. Si dice **«sin seña»** o **«no vio manos»**: no bajaste las manos del todo, fue muy lenta o no se vieron. Repetila **una vez**. Si vuelve a salir y la hiciste bien, guardala.
7. Son 55 palabras × 2 tomas (unos 45 min). Cada 10 palabras la pantalla te pide cambiar luz, distancia o ángulo.
8. Podés cerrar con **Q** y seguir otro día: retoma donde quedaste.

Preguntá **con qué cámara** graba. Lo mejor es la misma de la ronda 1 (la de la tabla): usá ese mismo nombre. Si cambia de cámara, un nombre corto sin espacios (`hp-windows`, `huawei`...). Celular como cámara: app **Iriun Webcam** en el celular + el programa de iriun.com en la compu, mismo Wi-Fi, celular en horizontal y fijo, que se vean hombros y manos.

Terminá preguntando: **«¿Listo para empezar?»**. No empieces sin el sí.

## 4. Preparar y abrir el grabador (con el sí)

1. **Cámara:** probá que abre (`cv2.VideoCapture(0)`; probá 1, 2 si falla). Si no abre, resolvelo con la persona antes de seguir.
2. **Videos del CENAREC** de su lista: `.venv/Scripts/python -m scripts.descargar_cenarec --lista data/reference/banco/<nombre>.txt` (baja los que falten de los 85). Quedan en `data/dictionary/` (ignorado por git).
3. **Abrir el grabador** en segundo plano (`run_in_background`):
   `.venv/Scripts/python -m scripts.grabar_banco "<Nombre al grabar>" --camara-nombre <cámara> --plan`
   (si la cámara no es la 0, agregá `--camara N`). Arranca solo en la primera palabra pendiente (la 31 si no grabó nada de la ronda 2). Avisale que la ventana se abrió y que mire la línea **«hombros OK | manos detectadas»** en verde antes de grabar.
   - Si el grabador responde «Ya hay tomas tuyas con otro nombre», usaste mal el nombre: volvé a abrirlo con el «Nombre al grabar» de la tabla.

Mientras graba, solo ayudá con problemas puntuales (encuadre, cámara, el programa). **No modifiques código ni otros archivos.** Si pregunta si repite una toma porque el programa no la reconoció: **no, si la hizo bien se guarda** (solo «sin seña» o «no vio manos» se repite, una vez).

## 5. Cuando termine el grabador

1. Mirá que en `data/banco/` haya **una sola carpeta de esa persona** (`christian-paniagua`, `steven-baltodano`, `reyman-barquero` o `johan-morales`). Si apareció otra con su nombre, parate y avisale a Christian antes de subir nada.
2. Corré `.venv/Scripts/python -m scripts.registrar_banco "<Nombre al grabar>"`.
   - Si dice que falta algo: decile qué falta y volvé a abrir el grabador (retoma solo).
   - Si está completo (170 tomas), reescribe `hiloEquipo/banco/<carpeta de la persona>.md`.
3. Decile que **falta subirlo** y hacé el push **solo de sus archivos**: `data/banco/<carpeta de la persona>/` y `hiloEquipo/banco/<carpeta de la persona>.md`. En este orden:
   1. **Commit** con el subagente `commits` (español, sin coautores, sin mencionar a Claude, ej. «Agregar ronda 2 del banco de Steven Baltodano»), agregando esos archivos por nombre. Nada más.
   2. **`git pull`**. Si hay conflictos, resolverlos con la persona.
   3. **Chequeos de `/preparar-push`** y **`git push`**.
4. Si cierra antes de terminar (con **Q**), subí igual lo que lleve con los mismos pasos (sin el `.md` si `registrar_banco` dice que está incompleto) y decile cuántas palabras le faltan.
5. Con el push hecho: «Listo. Christian mide cuando estén los 4.» **No hay nada más que conversar sobre el problema 1** con esta persona: no comentes resultados ni análisis. Si es Christian quien grabó, seguí normal con él.

Si la persona pregunta por sus propios problemas del plan, que use el arranque normal («Hola chat, póngamonos al hilo del proyecto para avanzar»).
