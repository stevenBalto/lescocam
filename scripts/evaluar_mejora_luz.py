"""Problema 4, fase 2: prueba mejoras (gamma, CLAHE, umbral más bajo) sobre el banco de luz.

Para cada variante de luz mala (poca_luz_*, contraluz_*) aplica cada mejora ANTES
de MediaPipe y vuelve a medir la tasa de detección de manos, comparándola con la
luz normal de hoy (base, sin mejora, umbral 0.5). Así se ve con números qué
combinación recupera la detección. El objetivo del problema es >= 90 % de la
detección que hay con buena luz.

Qué se cruza:
    variante     el caso de luz mala (banco de luz de la fase 1)
    estrategia   ninguna / gamma / clahe / gamma_clahe (core/mejora_luz.py)
    conf         umbral de confianza de MediaPipe (0.5 actual; 0.3 más permisivo)

El frame pasa por: luz mala (transformar) -> mejora -> espejo -> detector. Cada
combinación se cachea en data/dictionary/cenarec/extraccion/mejora/ (ignorado).

Con --paso N se procesa 1 de cada N frames (más rápido; N=2 alcanza para la tasa).
Con --brillo se mide, aparte, el brillo del cuadro entero vs. el de la zona de la
mano (caja de las muñecas): justifica medir la luz en la mano y no en todo el cuadro.

Uso:
    .venv/Scripts/python -m scripts.evaluar_mejora_luz                      # grilla por defecto
    .venv/Scripts/python -m scripts.evaluar_mejora_luz --conf 0.5 0.3
    .venv/Scripts/python -m scripts.evaluar_mejora_luz --brillo
"""
from __future__ import annotations

import argparse
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from core.mejora_luz import ESTRATEGIAS, brillo, caja_munecas, mejorar
from scripts.extraer_cenarec import EXTRACCION, VIDEOS, catalogo, transformar

REF_VARIANTE, REF_ESTRATEGIA, REF_CONF = "base", "ninguna", 0.5   # la luz normal de hoy
VARIANTES_DEF = ("base", "poca_luz_2", "poca_luz_3", "contraluz_3")


def _clave(variante, estrategia, conf, paso) -> str:
    return f"{variante}__{estrategia}__c{conf:.2f}__p{paso}"


def _cache(idw, variante, estrategia, conf, paso) -> Path:
    return EXTRACCION / "mejora" / _clave(variante, estrategia, conf, paso) / f"{int(idw):05d}.npz"


def extraer(ruta_video, variante, estrategia, conf, paso):
    """Corre el detector sobre el video con luz mala + mejora. Devuelve arrays (ver core.cuerpo.a_arrays)."""
    import cv2
    from core.cuerpo import DetectorCuerpo, a_arrays
    det = DetectorCuerpo(confianza=conf)
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
            if (i - 1) % paso:
                continue
            frame = transformar(frame, variante)
            frame = mejorar(frame, estrategia)
            if variante != "espejo":
                frame = cv2.flip(frame, 1)
            cuadros.append(det.procesar(frame, t))
    finally:
        cap.release()
        det.cerrar()
    return a_arrays(cuadros), fps


def _trabajo(args):
    idw, archivo, variante, estrategia, conf, paso, forzar = args
    destino = _cache(idw, variante, estrategia, conf, paso)
    if destino.exists() and not forzar:
        return idw, "cache"
    try:
        datos, fps = extraer(VIDEOS / archivo, variante, estrategia, conf, paso)
    except Exception as e:
        return idw, f"error: {e}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, fps=np.float64(fps), idw=np.int32(idw), **datos)
    tmp.replace(destino)
    return idw, "ok"


def tasa(idw, variante, estrategia, conf, paso) -> float:
    """Fracción de frames con al menos una mano detectada."""
    datos = np.load(_cache(idw, variante, estrategia, conf, paso))
    score = datos["score"]
    return float(np.mean(score.max(axis=1) > 0)) if len(score) else 0.0


def medir_brillo(etiquetas, cat, variantes, paso):
    """Brillo (luma 0-255) del cuadro entero vs. zona de la mano, por variante.

    Usa la pose ya detectada en base (umbral 0.5, mejora ninguna) para ubicar las
    muñecas; mide el brillo en ese recorte sobre el frame de cada variante.
    """
    import cv2
    from core.cuerpo import desde_arrays
    print("\nBrillo (luma 0-255): cuadro entero vs. zona de la mano (caja de las muñecas)")
    cab = f"{'variante':<28} {'cuadro':>8} {'mano':>8}"
    print(cab); print("-" * len(cab))
    for v in variantes:
        enteros, manos = [], []
        for e in etiquetas:
            idw, archivo = cat[e]["idw"], cat[e]["archivo"]
            ref = _cache(idw, REF_VARIANTE, REF_ESTRATEGIA, REF_CONF, paso)
            if not ref.exists():
                continue
            poses = [c.pose for c in desde_arrays(np.load(ref))]
            cap = cv2.VideoCapture(str(VIDEOS / archivo))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            i, k = 0, 0
            try:
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        break
                    i += 1
                    if (i - 1) % paso:
                        continue
                    f = transformar(frame, v)
                    if v != "espejo":
                        f = cv2.flip(f, 1)
                    alto, ancho = f.shape[:2]
                    pose = poses[k] if k < len(poses) else None
                    k += 1
                    enteros.append(brillo(f))
                    caja = caja_munecas(pose, ancho, alto)
                    if caja is not None:
                        manos.append(brillo(f, caja))
            finally:
                cap.release()
        c = np.mean(enteros) if enteros else 0.0
        m = np.mean(manos) if manos else 0.0
        print(f"{v:<28} {c:>8.1f} {m:>8.1f}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--etiquetas", nargs="*", help="solo estas palabras (por defecto, todas las descargadas)")
    p.add_argument("--variante", nargs="*", default=list(VARIANTES_DEF))
    p.add_argument("--estrategia", nargs="*", default=list(ESTRATEGIAS), choices=ESTRATEGIAS)
    p.add_argument("--conf", nargs="*", type=float, default=[0.5], help="umbrales de confianza a probar")
    p.add_argument("--paso", type=int, default=2, help="procesar 1 de cada N frames")
    p.add_argument("--procesos", type=int, default=4)
    p.add_argument("--forzar", action="store_true")
    p.add_argument("--brillo", action="store_true", help="además, medir brillo cuadro vs. zona de la mano")
    a = p.parse_args(argv)

    cat = catalogo()
    etiquetas = [e for e in (a.etiquetas or sorted(cat)) if e in cat]
    if not etiquetas:
        print("No hay videos. Bajalos con scripts.descargar_cenarec.", file=sys.stderr)
        return 1

    # base/ninguna/0.5 siempre, para la referencia de luz normal.
    combos = {(REF_VARIANTE, REF_ESTRATEGIA, REF_CONF)}
    for v in a.variante:
        for s in a.estrategia:
            for c in a.conf:
                combos.add((v, s, c))
    trabajos = [(cat[e]["idw"], cat[e]["archivo"], v, s, c, a.paso, a.forzar)
                for (v, s, c) in sorted(combos) for e in etiquetas]

    print(f"{len(etiquetas)} videos x {len(combos)} combinaciones = {len(trabajos)} pasadas "
          f"(1 de cada {a.paso} frames, reusa cache)...", flush=True)
    inicio = time.perf_counter()
    hechos, errores = 0, []
    with Pool(a.procesos) as pool:
        for idw, estado in pool.imap_unordered(_trabajo, trabajos):
            hechos += 1
            if estado not in ("ok", "cache"):
                errores.append((idw, estado))
            if hechos % 40 == 0 or hechos == len(trabajos):
                print(f"  [{hechos}/{len(trabajos)}]", flush=True)
    for idw, estado in errores:
        print(f"ERROR idw {idw}: {estado}", file=sys.stderr)

    ref = float(np.mean([tasa(cat[e]["idw"], REF_VARIANTE, REF_ESTRATEGIA, REF_CONF, a.paso) for e in etiquetas]))
    print(f"\nTasa de detección de manos (>=1) sobre {len(etiquetas)} videos. "
          f"Referencia (luz normal hoy) = {ref*100:.1f} %. Extracción en {time.perf_counter()-inicio:.0f} s.\n")
    cab = f"{'variante':<14} {'estrategia':<13} {'conf':>5} {'manos>=1':>9} {'% vs normal':>12}"
    print(cab); print("-" * len(cab))
    for v in a.variante:
        mejor = None
        filas = []
        for s in a.estrategia:
            for c in a.conf:
                t = float(np.mean([tasa(cat[e]["idw"], v, s, c, a.paso) for e in etiquetas]))
                vs = 100 * t / ref if ref else 0.0
                filas.append((s, c, t, vs))
                if mejor is None or vs > mejor[3]:
                    mejor = (s, c, t, vs)
        for s, c, t, vs in filas:
            estrella = " <--" if (s, c) == (mejor[0], mejor[1]) else ""
            ok = "" if v == "base" else ("  OK" if vs >= 90 else "")
            print(f"{v:<14} {s:<13} {c:>5.2f} {t*100:>8.1f}% {vs:>11.1f}%{ok}{estrella}")
        print("-" * len(cab))

    if a.brillo:
        medir_brillo(etiquetas, cat, a.variante, a.paso)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
