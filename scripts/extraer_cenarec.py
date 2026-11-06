"""Extrae las dos manos y el cuerpo de los videos del Diccionario LESCO de CENAREC.

Por cada frame (espejado como la cámara en vivo) corre core/cuerpo.DetectorCuerpo
(HandLandmarker con 2 manos + PoseLandmarker lite, modo VIDEO) y guarda lo crudo
en un cache por video:

    data/dictionary/cenarec/extraccion/<variante>/<idw>.npz      (ignorado por git)

con t, frame, manos (F, 2, 21, 3), lado (F, 2), score (F, 2), pose (F, 33, 4)
(ver core/cuerpo.a_arrays). Un video ya extraído no se reprocesa (salvo --forzar).

Variantes (para evaluar robustez; se aplican al frame original antes de espejar):
    base        tal cual (640x360, 30 fps)
    15fps       un frame de cada dos
    4x3         recorte central 480x360 (cámara 4:3)
    cerca       zoom 1.3 centrado en el pecho (las manos en reposo quedan fuera)
    lejos       persona al 70 % con borde del color del fondo
    giro        cámara girada 8 grados
    desplazado  persona corrida 80 px a un costado
    espejo      sin espejar: la persona queda zurda
    poca_luz_1..3   poca luz, 3 niveles (tenue -> casi a oscuras)
    contraluz_1..3  contraluz con ventana atrás, 3 niveles (sujeto oscuro, fondo quemado)

Uso:
    .venv/bin/python -m scripts.extraer_cenarec                       # palabras_iniciales.txt
    .venv/bin/python -m scripts.extraer_cenarec --todas --procesos 6  # los 1072 videos
    .venv/bin/python -m scripts.extraer_cenarec --variante 4x3 cerca lejos
    .venv/bin/python -m scripts.extraer_cenarec --etiquetas HOLA GRACIAS
    .venv/bin/python -m scripts.extraer_cenarec --video data/dictionary/videos/abecedario-lesco.mp4
        (cualquier otro video -> extraccion/otros/<nombre>.npz, para medir falsos positivos)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "dictionary" / "cenarec"
CATALOGO = CARPETA / "catalogo.json"
VIDEOS = CARPETA / "videos"
EXTRACCION = CARPETA / "extraccion"
LISTA = RAIZ / "data" / "reference" / "palabras_iniciales.txt"
VARIANTES = ("base", "15fps", "4x3", "cerca", "lejos", "giro", "desplazado", "espejo",
             "poca_luz_1", "poca_luz_2", "poca_luz_3",
             "contraluz_1", "contraluz_2", "contraluz_3")


def leer_lista(ruta: Path = LISTA) -> list[str]:
    return [l.strip() for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def catalogo() -> dict:
    """etiqueta -> {"idw", "archivo", ...} de los videos descargados."""
    datos = json.loads(CATALOGO.read_text(encoding="utf-8"))["palabras"]
    salida = {}
    for idw, d in datos.items():
        if d.get("archivo") and (VIDEOS / d["archivo"]).exists():
            salida[d["etiqueta"]] = {"idw": int(idw), **d}
    return salida


def muestra_escala(cat: dict, iniciales: list, n: int, semilla: int = 7) -> list:
    """Las letras deletreadas (LETRA-*) + n palabras al azar que no están en la lista (siempre las mismas)."""
    import random
    letras = sorted(e for e in cat if e.startswith("LETRA-"))
    resto = sorted(e for e in cat if e not in iniciales and e not in letras)
    random.Random(semilla).shuffle(resto)
    return letras + resto[:n]


def ruta_cache(idw: int, variante: str = "base") -> Path:
    return EXTRACCION / variante / f"{int(idw):05d}.npz"


def ruta_otro(video: Path) -> Path:
    return EXTRACCION / "otros" / f"{Path(video).stem}.npz"


def transformar(frame, variante: str):
    """Frame original -> frame de la variante (sin espejar todavía). None = saltear el frame."""
    import cv2
    alto, ancho = frame.shape[:2]
    if variante == "4x3":
        a = alto * 4 // 3
        x0 = (ancho - a) // 2
        return frame[:, x0:x0 + a]
    if variante == "cerca":
        f = 1.3
        w, h = int(ancho / f), int(alto / f)
        cx, cy = ancho // 2, int(alto * 0.45)
        x0, y0 = max(0, cx - w // 2), max(0, cy - h // 2)
        return cv2.resize(frame[y0:y0 + h, x0:x0 + w], (ancho, alto), interpolation=cv2.INTER_LINEAR)
    if variante == "lejos":
        f = 0.7
        chico = cv2.resize(frame, (int(ancho * f), int(alto * f)), interpolation=cv2.INTER_AREA)
        fondo = np.median(np.concatenate([frame[:20, :20].reshape(-1, 3), frame[:20, -20:].reshape(-1, 3)]), axis=0)
        lienzo = np.empty_like(frame)
        lienzo[:] = fondo.astype(np.uint8)
        y0, x0 = alto - chico.shape[0], (ancho - chico.shape[1]) // 2   # apoyada abajo, como de cintura para arriba
        lienzo[y0:, x0:x0 + chico.shape[1]] = chico
        return lienzo
    if variante == "giro":
        m = cv2.getRotationMatrix2D((ancho / 2, alto / 2), 8, 1.0)
        return cv2.warpAffine(frame, m, (ancho, alto), borderMode=cv2.BORDER_REPLICATE)
    if variante == "desplazado":
        m = np.float32([[1, 0, 80], [0, 1, 0]])
        return cv2.warpAffine(frame, m, (ancho, alto), borderMode=cv2.BORDER_REPLICATE)
    if variante.startswith("poca_luz_") or variante.startswith("contraluz_"):
        # Poca luz / contraluz (3 niveles cada uno): baja la exposición y mete ruido de
        # sensor, que es lo que de verdad confunde a MediaPipe. La misma función la usa
        # la app para simular estas condiciones desde la PC (core/mejora_luz.simular_luz).
        from core.mejora_luz import simular_luz
        return simular_luz(frame, variante)
    return frame


def extraer_video(ruta_video: Path, variante: str = "base", detector=None) -> tuple[dict, float]:
    """(arrays del cache, fps). Usa un DetectorCuerpo nuevo por video (el modo VIDEO arrastra el seguimiento)."""
    import cv2
    from core.cuerpo import DetectorCuerpo, a_arrays
    det = detector or DetectorCuerpo()
    cap = cv2.VideoCapture(str(ruta_video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cuadros, i = [], 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t = i / fps
            i += 1
            if variante == "15fps" and (i - 1) % 2:
                continue
            frame = transformar(frame, variante)
            if variante != "espejo":
                frame = cv2.flip(frame, 1)
            cuadros.append(det.procesar(frame, t))
    finally:
        cap.release()
        if detector is None:
            det.cerrar()
    return a_arrays(cuadros), fps


def _trabajo(args):
    idw, etiqueta, archivo, variante, forzar = args
    destino = ruta_cache(idw, variante)
    if destino.exists() and not forzar:
        return idw, etiqueta, 0.0, 0, "cache"
    inicio = time.perf_counter()
    try:
        # Un detector por video: el modo VIDEO exige tiempos crecientes y arrastra el seguimiento.
        datos, fps = extraer_video(VIDEOS / archivo, variante)
    except Exception as e:  # un video roto no frena el resto
        return idw, etiqueta, time.perf_counter() - inicio, 0, f"error: {e}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, fps=np.float64(fps), idw=np.int32(idw), etiqueta=np.array(etiqueta),
                        variante=np.array(variante), **datos)
    tmp.replace(destino)
    return idw, etiqueta, time.perf_counter() - inicio, len(datos["t"]), "ok"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lista", type=Path, default=LISTA, help="archivo con una etiqueta por línea")
    p.add_argument("--todas", action="store_true", help="todos los videos descargados")
    p.add_argument("--etiquetas", nargs="*", help="solo estas etiquetas")
    p.add_argument("--max", type=int, default=0, help="como mucho N videos (en orden de etiqueta)")
    p.add_argument("--muestra", type=int, default=0,
                   help="la lista + N palabras más al azar (semilla fija) y las letras LETRA-*: para medir escala")
    p.add_argument("--variante", nargs="*", default=["base"], choices=VARIANTES)
    p.add_argument("--procesos", type=int, default=max(1, min(6, (os.cpu_count() or 2) // 2)))
    p.add_argument("--forzar", action="store_true", help="reprocesar aunque haya cache")
    p.add_argument("--video", type=Path, nargs="*", help="otros videos (no de CENAREC) -> extraccion/otros/")
    a = p.parse_args(argv)

    if a.video:
        for ruta in a.video:
            destino = ruta_otro(ruta)
            if destino.exists() and not a.forzar:
                print(f"{ruta.name}: cache")
                continue
            inicio = time.perf_counter()
            datos, fps = extraer_video(ruta)
            destino.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(destino, fps=np.float64(fps), etiqueta=np.array(ruta.stem), variante=np.array("base"),
                                **datos)
            print(f"{ruta.name}: {len(datos['t'])} frames en {time.perf_counter() - inicio:.0f} s -> {destino}")
        return 0

    cat = catalogo()
    if a.etiquetas:
        etiquetas = a.etiquetas
    elif a.todas:
        etiquetas = sorted(cat)
    else:
        etiquetas = leer_lista(a.lista)
        if a.muestra:
            etiquetas += muestra_escala(cat, etiquetas, a.muestra)
    faltan = [e for e in etiquetas if e not in cat]
    if faltan:
        print(f"Sin video: {', '.join(faltan)}", file=sys.stderr)
    etiquetas = [e for e in etiquetas if e in cat]
    if a.max:
        etiquetas = etiquetas[:a.max]
    trabajos = [(cat[e]["idw"], e, cat[e]["archivo"], v, a.forzar) for v in a.variante for e in etiquetas]

    inicio = time.perf_counter()
    hechos, tiempos, frames, errores = 0, [], 0, []
    with Pool(a.procesos) as pool:
        for idw, etiqueta, seg, n, estado in pool.imap_unordered(_trabajo, trabajos):
            hechos += 1
            if estado == "ok":
                tiempos.append(seg)
                frames += n
            elif estado != "cache":
                errores.append((etiqueta, estado))
            print(f"[{hechos}/{len(trabajos)}] {etiqueta} ({idw}): {estado} {seg:.1f} s", flush=True)
    total = time.perf_counter() - inicio
    if tiempos:
        print(f"\nExtraídos {len(tiempos)} videos en {total:.0f} s con {a.procesos} procesos: "
              f"{total / len(tiempos):.2f} s/video de reloj, {np.mean(tiempos):.1f} s/video por proceso, "
              f"{1000 * sum(tiempos) / max(frames, 1):.1f} ms/frame por proceso")
    for e, estado in errores:
        print(f"ERROR {e}: {estado}", file=sys.stderr)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
