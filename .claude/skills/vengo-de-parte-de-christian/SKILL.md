---
name: vengo-de-parte-de-christian
description: Banco de prueba de LESCOCam para Steven, Reyman y Johan (problema 1, fase 1). Se activa con "Vengo de parte de Christian". Pide el nombre antes de todo, muestra las 30 palabras de esa persona, da los pasos y pregunta si está lista; con el sí prepara todo y abre el grabador. Al terminar registra las palabras y deja todo listo para el push. Después no se habla más del problema 1.
---

# Banco de prueba — compañeros

Plan en `hiloEquipo/` (problema 1, fase 1). Cada persona graba **30 palabras × 2 tomas** imitando los videos de CENAREC. Las tomas son **solo de prueba**. No hace falta saber LESCO.

## 1. Pedir el nombre (antes de todo)

**No leas archivos, no corras comandos ni resumas nada hasta tener el nombre.** Preguntá solo: «¿Cómo te llamás?».

Buscá a la persona (sin distinguir mayúsculas ni tildes; alcanza con nombre de pila y un apellido):

| Persona | Nombre al grabar | Lista |
|---|---|---|
| Steven Baltodano | `Steven Baltodano` | `data/reference/banco/steven.txt` |
| Reyman Barquero | `Reyman Barquero` | `data/reference/banco/reyman.txt` |
| Johan Morales Chacón | `Johan Morales` | `data/reference/banco/johan.txt` |

Si es Christian: ya terminó su parte (`hiloEquipo/banco/christian-paniagua.md`); no usa esta skill. Si el nombre no coincide con nadie, decilo y volvé a preguntar.

## 2. Ponerse al día

`git pull`. Si falla o hay conflictos, parate y resolvelo con la persona antes de seguir.

## 3. Mostrar la lista y los pasos

Leé la lista de esa persona y mostrála en **3 tandas de 10 palabras** (las que están bajo `# Tanda N`). Después, estos pasos, **cortos**:

1. Se abre una ventana con el video de CENAREC a la izquierda y tu cámara a la derecha.
2. Imitá la seña con **su ritmo (1–2 s)**: manos abajo → seña **una sola vez** → manos abajo.
3. **ESPACIO** graba (cuenta 3 s, toma de 6 s). **G** guarda. **R** repite **solo si te equivocaste vos o no se veían tus manos**, nunca porque el motor no la reconoció.
4. Son 2 tomas por palabra (60 en total, unos 25 min). Cada tanda de 10 cambia luz, distancia y ángulo: la pantalla te dice qué hacer.
5. Podés cerrar con **Q** y retomar después; sigue donde quedaste.

Preguntá también **con qué cámara** graba y anotá un nombre corto sin espacios (`hp-windows`, `hp-linux`, `huawei`...). Si usa el celular como cámara: app **Iriun Webcam** en el celular + programa de Windows/Linux desde iriun.com, mismo Wi-Fi, celular en horizontal y fijo, que se vean hombros y manos.

Terminá preguntando: **«¿Estás listo para proceder?»**. No empieces sin el sí.

## 4. Preparar y abrir el grabador (con el sí)

1. **Entorno** (si no existe `.venv`): `python -m venv .venv` y `.venv/Scripts/python -m pip install -r requirements-dev.txt` (en Linux: `python3 -m venv .venv` y `.venv/bin/python -m pip install -r requirements-dev.txt`). Python 3.12 o superior. No uses npm; no instales `opencv-python`.
2. **Cámara:** probá que abre (`cv2.VideoCapture(0)`; probá 1, 2 si falla). Si no abre, resolvelo con la persona antes de seguir (otra app la usa, permisos, o falta el programa de la cámara del celular).
3. **Videos de CENAREC** de su lista: `.venv/Scripts/python -m scripts.descargar_cenarec --lista data/reference/banco/<nombre>.txt` (30 videos, ~1 min). Quedan en `data/dictionary/` (ignorado por git).
4. **Abrir el grabador** en segundo plano (`run_in_background`):
   `.venv/Scripts/python -m scripts.grabar_banco "<Nombre al grabar>" --camara-nombre <cámara> --plan`
   (Linux: `.venv/bin/python`; si la cámara no es la 0, agregá `--camara N`). Avisale que la ventana se abrió y que mire la línea **"hombros OK | manos detectadas"** en verde antes de grabar.

Mientras graba, solo ayudá con problemas puntuales (encuadre, cámara, el programa). **No modifiques código ni otros archivos.**

## 5. Cuando termine el grabador

1. Corré `.venv/Scripts/python -m scripts.registrar_banco "<Nombre al grabar>"`.
   - Si dice que falta algo: decile qué falta y volvé a abrir el grabador (retoma solo).
   - Si está completo, escribe `hiloEquipo/banco/<nombre>.md` (palabras, cámara, tomas y resultado). Eso es el registro de que quedaron las palabras de esa persona.
2. Decile que **todo está listo y falta subirlo**, y hacé el push **solo de sus archivos**: `data/banco/<carpeta de la persona>/` y `hiloEquipo/banco/<nombre>.md`. En este orden:
   1. **Commit** con el subagente `commits` (español, sin coautores, sin mencionar a Claude, ej. «Agregar banco de prueba de Steven Baltodano»), agregando esos archivos por nombre. Nada más.
   2. **`git pull`**. Si hay conflictos, resolverlos con la persona.
   3. **Chequeos de `/preparar-push`** y **`git push`**.
3. Con el push hecho: «Listo. Christian revisa cuando estén los 4.» **No hay nada más que conversar sobre el problema 1** con esta persona: no comentes resultados ni análisis.

Si la persona pregunta por sus propios problemas del plan, que use el arranque normal («Hola chat, póngamonos al hilo del proyecto para avanzar»).
