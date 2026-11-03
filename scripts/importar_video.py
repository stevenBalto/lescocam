"""Importa a signs.json las letras de un video del abecedario.

Pensado para videos donde cada letra aparece escrita en pantalla mientras se
hace la seña (como "Abecedario en LESCO" de Hands-On!). El video se corta en
tramos cada vez que cambia el rótulo y los tramos se asignan en orden a ORDEN.

  - Letras quietas: de la parte central de cada tramo salen varias tomas, con
    "frame": [ancho, alto] del recorte de la mano (signs.json version 3).
  - Letras con movimiento (J, LL, Ñ, RR, Z): el gesto se busca en VENTANAS_MOVIMIENTO
    (segundos del video, elegidos mirando los frames: el movimiento propio de la
    seña, sin la mano que entra o sale) y se recorta con el mismo Segmentador que
    usa el motor en vivo (core/movimiento.py). Se guarda en
    data/reference/movimientos.json (versionado, formato en core/movimiento.py).

Uso:
    .venv/bin/python -m scripts.importar_video data/dictionary/videos/abecedario-lesco.mp4
    .venv/bin/python -m scripts.importar_video VIDEO --guardar              # quietas + movimiento
    .venv/bin/python -m scripts.importar_video VIDEO --solo-movimientos     # solo movimientos.json

--guardar AGREGA tomas a signs.json cada vez que se corre (si ya estaban, quedan
duplicadas); para rehacer solo las letras con movimiento usá --solo-movimientos,
que reemplaza las tomas "video:<este video>" de movimientos.json y no toca signs.json.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from core.camara import Detector
from core.clasificador import RUTA_SENAS, Clasificador, escribir_signs, leer_signs, signs_vacio
from core.movimiento import (RUTA_MOVIMIENTOS, TIPO, cuadro_de_mano, escribir_movimientos, leer_movimientos,
                             movimientos_vacio, recortar_gesto, toma_desde_cuadros)
from core.sinteticas import regenerar

ORDEN = ["A", "B", "C", "CH", "D", "E", "F", "G", "H", "I", "J", "K", "L", "LL", "M",
         "N", "Ñ", "O", "P", "Q", "R", "RR", "S", "T", "U", "V", "W", "X", "Y", "Z"]
CON_MOVIMIENTO = {"J", "LL", "Ñ", "RR", "Z"}

# Medidas del video de Hands-On! (1280x720): primer plano de la mano a la
# izquierda y rótulo azul arriba a la derecha de ese panel.
RECORTE_MANO = (0, 0, 612, 720)        # x0, y0, x1, y1
ZONA_ROTULO = (250, 40, 612, 280)
AZUL_MIN, AZUL_MAX = (90, 80, 80), (130, 255, 255)
MIN_PIXELES_ROTULO = 300
MIN_CAMBIO_ROTULO = 800                # píxeles que cambian de un frame al otro = letra nueva

CENTRO = 0.6                           # fracción central del tramo que se usa (la mano ya está quieta)
DECIMALES = 6

# Dónde está el movimiento de cada letra en el video de Hands-On! (segundos). El
# rótulo no coincide con el gesto: J y LL empiezan al final del tramo de I y de L,
# y Z sale del cuadro por abajo (se usa la parte en que la mano se ve entera).
#   J : de I (meñique arriba) el meñique baja girando la muñeca y termina horizontal
#   LL: la L se desliza de costado ~0.7 manos y se queda quieta
#   Ñ : el puño de la N gira la muñeca de un lado al otro (~4 vaivenes)
#   RR: la R (índice y medio cruzados) se desliza de costado ~0.6 manos
#   Z : el índice arriba dibuja la Z (raya arriba, diagonal hacia abajo, raya abajo)
VENTANAS_MOVIMIENTO = {"J": (41.37, 43.21), "LL": (51.65, 52.72), "Ñ": (61.55, 64.56),
                       "RR": (78.74, 79.81), "Z": (105.31, 106.77)}


def mascara_rotulo(frame) -> np.ndarray:
    x0, y0, x1, y1 = ZONA_ROTULO
    hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, AZUL_MIN, AZUL_MAX) > 0


def buscar_tramos(ruta: Path):
    """Primera pasada: (fps, tramos [(inicio, fin)]) según los cambios del rótulo."""
    cap = cv2.VideoCapture(str(ruta))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir {ruta}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cortes, previa, hay = [], None, []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        mascara = mascara_rotulo(frame)
        if previa is not None and (mascara ^ previa).sum() > MIN_CAMBIO_ROTULO:
            if not cortes or len(hay) - cortes[-1] > 5:
                cortes.append(len(hay))
        hay.append(mascara.sum() > MIN_PIXELES_ROTULO)
        previa = mascara
    cap.release()
    tramos = [(a, b - 1) for a, b in zip(cortes, cortes[1:] + [len(hay)])
              if hay[a] and hay[(a + b - 1) // 2]]
    return fps, tramos


def vectores_por_tramo(ruta: Path, tramos, detector: Detector) -> list[list]:
    """Segunda pasada: vector normalizado de cada frame de cada tramo (None si no hay mano).

    No guarda los frames: un video entero en memoria pesa varios GB.
    """
    x0, y0, x1, y1 = RECORTE_MANO
    dueno = {}
    for n, (a, b) in enumerate(tramos):
        for i in range(a, b + 1):
            dueno[i] = n
    salida = [[] for _ in tramos]
    cap = cv2.VideoCapture(str(ruta))
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i in dueno:
            # Mismo camino que la cámara de la app: frame espejado tipo selfie.
            mano = detector.procesar(cv2.flip(frame[y0:y1, x0:x1], 1))
            salida[dueno[i]].append(None if mano is None else mano.vector)
        i += 1
    cap.release()
    return salida


def gestos_en_ventanas(ruta: Path, fps: float, detector: Detector, ventanas=VENTANAS_MOVIMIENTO) -> dict:
    """letra -> lista de Cuadros del gesto recortado (o None si no se encontró movimiento)."""
    x0, y0, x1, y1 = RECORTE_MANO
    rangos = {l: (int(round(a * fps)), int(round(b * fps))) for l, (a, b) in ventanas.items()}
    cuadros = {l: [] for l in ventanas}
    cap = cv2.VideoCapture(str(ruta))
    i = 0
    hasta = max(b for _, b in rangos.values())
    while i <= hasta:
        ok, frame = cap.read()
        if not ok:
            break
        dentro = [l for l, (a, b) in rangos.items() if a <= i <= b]
        if dentro:
            mano = detector.procesar(cv2.flip(frame[y0:y1, x0:x1], 1))
            for l in dentro:
                cuadros[l].append(cuadro_de_mano(mano, i / fps))
        i += 1
    cap.release()
    salida = {}
    for l, cs in cuadros.items():
        a = rangos[l][0]
        salida[l] = recortar_gesto(cs, [(a + k) / fps for k in range(len(cs))])
    return salida


def guardar_movimientos(gestos: dict, video: Path, fps: float, destino: Path = RUTA_MOVIMIENTOS) -> int:
    """Reemplaza las tomas "video:<video>" de cada letra en movimientos.json. Devuelve cuántas guardó."""
    datos = leer_movimientos(destino) if destino.exists() else movimientos_vacio()
    x0, y0, x1, y1 = RECORTE_MANO
    source = f"video:{video.name}"
    ahora = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    n = 0
    for letra, gesto in gestos.items():
        if not gesto:
            continue
        entrada = datos["signs"].setdefault(letra, {"categoria": "letra", "tipo": TIPO, "takes": []})
        entrada["takes"] = [t for t in entrada["takes"] if t.get("source") != source]
        entrada["takes"].insert(0, toma_desde_cuadros(gesto, source, fps, (x1 - x0, y1 - y0), ahora,
                                                      inicio=round(gesto[0].t, 3), fin=round(gesto[-1].t, 3)))
        n += 1
    escribir_movimientos(destino, datos)
    return n


def tomas_quietas(vectores: list, cuantas: int) -> list[tuple[np.ndarray, int]]:
    """Parte la zona central del tramo en `cuantas` grupos: [(promedio, frames usados), ...]."""
    n = len(vectores)
    margen = int(n * (1 - CENTRO) / 2)
    centro = [v for v in vectores[margen:n - margen] if v is not None]
    if len(centro) < cuantas:
        return []
    return [(grupo.mean(axis=0), len(grupo)) for grupo in np.array_split(np.array(centro), cuantas)]


def movimiento(vectores: list) -> float:
    """Cuánto se mueve la forma de la mano en el tramo (0 = quieta)."""
    validos = np.array([v for v in vectores if v is not None])
    if len(validos) < 2:
        return 0.0
    return float(np.linalg.norm(validos.std(axis=0)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("--guardar", action="store_true", help="escribir en signs.json (sin esto solo prueba)")
    parser.add_argument("--tomas", type=int, default=3, help="tomas por letra quieta")
    parser.add_argument("--destino", type=Path, default=RUTA_SENAS)
    parser.add_argument("--solo-movimientos", action="store_true",
                        help="guardar solo las letras con movimiento en movimientos.json (no toca signs.json)")
    parser.add_argument("--movimientos", type=Path, default=RUTA_MOVIMIENTOS)
    args = parser.parse_args(argv)

    if args.solo_movimientos:
        cap = cv2.VideoCapture(str(args.video))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        cap.release()
        detector = Detector(confianza_deteccion=0.3)
        try:
            gestos = gestos_en_ventanas(args.video, fps, detector)
        finally:
            detector.cerrar()
        for letra, g in gestos.items():
            print(f"{letra:3} " + ("❌ sin movimiento en la ventana" if not g else
                                   f"{g[0].t:6.2f}-{g[-1].t:6.2f}s  {len(g)} cuadros"))
        n = guardar_movimientos(gestos, args.video, fps, args.movimientos)
        print(f"\nGuardado: {n} letras con movimiento en {args.movimientos}.")
        return 0

    fps, tramos = buscar_tramos(args.video)
    if len(tramos) != len(ORDEN):
        print(f"Se esperaban {len(ORDEN)} letras y se encontraron {len(tramos)} tramos: "
              "revisá el recorte o el rótulo antes de importar.")
        for a, b in tramos:
            print(f"  {a / fps:6.2f}-{b / fps:6.2f}s")
        return 1

    clasificador = Clasificador(args.destino) if args.destino.exists() else None
    detector = Detector(confianza_deteccion=0.3)
    quietas = {}
    print(f"{'letra':5} {'tiempo':>13} {'mano':>5} {'mov':>5}  comparación con signs.json actual")
    try:
        todos = vectores_por_tramo(args.video, tramos, detector)
    finally:
        detector.cerrar()
    for etiqueta, (a, b), vectores in zip(ORDEN, tramos, todos):
        detectados = sum(v is not None for v in vectores)
        mov = movimiento(vectores)
        linea = f"{etiqueta:5} {a / fps:6.2f}-{b / fps:5.2f}s {detectados * 100 // len(vectores):4}% {mov:5.2f}  "
        if etiqueta in CON_MOVIMIENTO:
            print(linea + "con movimiento: va a movimientos.json")
            continue
        tomas = tomas_quietas(vectores, args.tomas)
        if not tomas:
            print(linea + "❌ muy pocos frames con mano")
            continue
        quietas[etiqueta] = tomas
        if clasificador:
            muestra = tomas[len(tomas) // 2][0]
            top = clasificador.mejores(muestra, 3)
            propia = dict(clasificador.mejores(muestra, 50)).get(etiqueta)
            marca = "✅" if top and top[0][0] == etiqueta else "⚠️ "
            linea += f"{marca} misma letra={propia:.3f} | " if propia is not None else "nueva | "
            linea += ", ".join(f"{e}={s:.3f}" for e, s in top)
        print(linea)

    if not args.guardar:
        print("\nPrueba sin guardar. Agregá --guardar para escribir en signs.json.")
        return 0

    datos = leer_signs(args.destino) if args.destino.exists() else signs_vacio()
    x0, y0, x1, y1 = RECORTE_MANO
    ahora = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for etiqueta, tomas in quietas.items():
        for vector, muestras in tomas:
            datos["signs"].setdefault(etiqueta, {"takes": []})["takes"].append({
                "vector": [round(float(x), DECIMALES) for x in vector],
                "samples": muestras,
                "recorded_at": ahora,
                "source": f"video:{args.video.name}",
                "frame": [x1 - x0, y1 - y0],
            })
    escribir_signs(args.destino, regenerar(datos))   # recalcula las sintéticas

    detector = Detector(confianza_deteccion=0.3)
    try:
        gestos = gestos_en_ventanas(args.video, fps, detector)
    finally:
        detector.cerrar()
    n = guardar_movimientos(gestos, args.video, fps, args.movimientos)
    print(f"\nGuardado: {sum(len(t) for t in quietas.values())} tomas en {args.destino}, "
          f"{n} letras con movimiento en {args.movimientos}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
