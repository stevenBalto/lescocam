"""Extrae las dos manos y el cuerpo de los videos del diccionario de Hands-On LESCO.

Mismo camino que scripts/extraer_cenarec.py (extraer_video: frame espejado ->
core/cuerpo.DetectorCuerpo, modo VIDEO) y por defecto CON recorte
(DetectorCuerpo(recorte=True), problema 3), que es lo que usa la app. Los videos
los baja scripts/descargar_handson.py (Johan, problema 2).

Cache por video (ignorado por git, mismo formato v1 que CENAREC, core/cuerpo.a_arrays):

    data/dictionary/handson/extraccion/recorte/<id de Vimeo>.npz     (--sin-recorte: .../base/)

Los videos son 1920x1080 (o 960x540 con descargar_handson --alto 540) a ~24 fps, ~9 s, una persona de frente que hace la seña
DOS veces con reposo en el medio (como CENAREC). Un video ya extraído no se
reprocesa (salvo --forzar); uno roto no frena al resto.

Uso:
    .venv/bin/python -m scripts.extraer_handson                    # todos los descargados
    .venv/bin/python -m scripts.extraer_handson --max 20           # prueba
    .venv/bin/python -m scripts.extraer_handson --ids 1135903819   # solo esos
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "dictionary" / "handson"
VIDEOS = CARPETA / "videos"
CATALOGO = CARPETA / "catalogo.json"
EXTRACCION = CARPETA / "extraccion"


def catalogo() -> dict:
    """id de Vimeo (str) -> {"etiqueta", "letra", "archivo"} de los videos descargados."""
    if not CATALOGO.exists():
        return {}
    datos = json.loads(CATALOGO.read_text(encoding="utf-8"))["palabras"]
    return {vid: d for vid, d in datos.items() if d.get("archivo") and (VIDEOS / d["archivo"]).exists()}


def ruta_cache(vid, carpeta: str = "recorte") -> Path:
    return EXTRACCION / carpeta / f"{vid}.npz"


def _trabajo(args):
    vid, etiqueta, archivo, forzar, recorte = args
    destino = ruta_cache(vid, "recorte" if recorte else "base")
    if destino.exists() and not forzar:
        return vid, etiqueta, 0.0, 0, "cache"
    inicio = time.perf_counter()
    try:
        from core.cuerpo import DetectorCuerpo
        from scripts.extraer_cenarec import extraer_video
        det = DetectorCuerpo(recorte=recorte)
        try:
            datos, fps = extraer_video(VIDEOS / archivo, "base", detector=det)
        finally:
            det.cerrar()
    except Exception as e:  # un video roto no frena el resto
        return vid, etiqueta, time.perf_counter() - inicio, 0, f"error: {e}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, fps=np.float64(fps), vid=np.array(str(vid)), etiqueta=np.array(etiqueta),
                        variante=np.array("base"), **datos)
    tmp.replace(destino)
    return vid, etiqueta, time.perf_counter() - inicio, len(datos["t"]), "ok"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--max", type=int, default=0, help="como mucho N videos")
    p.add_argument("--muestra", type=int, default=0, help="N videos al azar (semilla 7)")
    p.add_argument("--ids", nargs="*", help="solo estos ids de Vimeo")
    p.add_argument("--procesos", type=int, default=max(1, min(6, (os.cpu_count() or 2) // 2)))
    p.add_argument("--forzar", action="store_true", help="reprocesar aunque haya cache")
    p.add_argument("--sin-recorte", action="store_true", help="DetectorCuerpo() de antes -> extraccion/base/")
    a = p.parse_args(argv)

    cat = catalogo()
    if not cat:
        print(f"No hay videos en {VIDEOS}: correr scripts/descargar_handson.py", file=sys.stderr)
        return 1
    ids = sorted(cat, key=lambda v: (cat[v]["etiqueta"], v))
    if a.ids:
        ids = [v for v in a.ids if v in cat]
    if a.muestra:
        ids = sorted(random.Random(7).sample(ids, min(a.muestra, len(ids))))
    if a.max:
        ids = ids[:a.max]
    trabajos = [(v, cat[v]["etiqueta"], cat[v]["archivo"], a.forzar, not a.sin_recorte) for v in ids]

    inicio = time.perf_counter()
    hechos, tiempos, errores = 0, [], []
    with Pool(a.procesos) as pool:
        for vid, etiqueta, seg, n, estado in pool.imap_unordered(_trabajo, trabajos):
            hechos += 1
            if estado == "ok":
                tiempos.append(seg)
            elif estado != "cache":
                errores.append((etiqueta, vid, estado))
            print(f"[{hechos}/{len(trabajos)}] {etiqueta} ({vid}): {estado} {seg:.1f} s", flush=True)
    total = time.perf_counter() - inicio
    if tiempos:
        print(f"\nExtraídos {len(tiempos)} videos en {total:.0f} s con {a.procesos} procesos "
              f"({total / len(tiempos):.2f} s/video de reloj)")
    for e, vid, estado in errores:
        print(f"ERROR {e} ({vid}): {estado}", file=sys.stderr)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
