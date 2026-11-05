"""Problema 4 (luz y contraste): mide la tasa de detección con poca luz y contraluz.

Arma el "banco de luz" sobre los videos descargados del CENAREC: por cada variante
de luz (poca_luz_1..3, contraluz_1..3) vuelve a extraer manos y cuerpo con
scripts.extraer_cenarec (reusa el cache si ya está) y mide, respecto de la luz
normal (base), cuánto se conserva la detección. Es el PUNTO DE PARTIDA de la fase 1:
todavía sin ninguna mejora (gamma/CLAHE/umbral), para saber qué tan mal se detecta.

Qué se mide por frame, a partir del cache de la extracción:
    manos>=1   hay al menos una mano (score > 0)
    2 manos    hay dos manos
    pose       hay cuerpo (pose de MediaPipe)
La tasa de un video es el promedio sobre sus frames; la de una variante es el
promedio sobre los videos (cada palabra pesa igual). "% vs base" es la tasa de la
variante dividida por la de base: la meta del problema es recuperar >= 90 %.

Uso:
    .venv/Scripts/python -m scripts.evaluar_luz                 # todos los videos descargados
    .venv/Scripts/python -m scripts.evaluar_luz --etiquetas HOLA GRACIAS
    .venv/Scripts/python -m scripts.evaluar_luz --forzar        # reextraer aunque haya cache
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from multiprocessing import Pool

import numpy as np

from scripts.extraer_cenarec import EXTRACCION, _trabajo, catalogo, ruta_cache

# base primero (referencia), después las variantes de luz en orden de severidad.
VARIANTES_LUZ = ("base",
                 "poca_luz_1", "poca_luz_2", "poca_luz_3",
                 "contraluz_1", "contraluz_2", "contraluz_3")

NOMBRE = {
    "base": "luz normal (base)",
    "poca_luz_1": "poca luz 1 (tenue)",
    "poca_luz_2": "poca luz 2 (oscuro)",
    "poca_luz_3": "poca luz 3 (casi a oscuras)",
    "contraluz_1": "contraluz 1 (suave)",
    "contraluz_2": "contraluz 2 (fuerte)",
    "contraluz_3": "contraluz 3 (ventana quemada)",
}


def tasas_video(idw: int, variante: str) -> tuple[float, float, float, int]:
    """(manos>=1, 2 manos, pose, n_frames) de un video ya extraído, como fracción de frames."""
    datos = np.load(ruta_cache(idw, variante))
    score = datos["score"]          # (n, 2): 0 = sin mano
    pose = datos["pose"]            # (n, 33, 4): NaN sin persona
    n = len(score)
    if n == 0:
        return 0.0, 0.0, 0.0, 0
    una = float(np.mean(score.max(axis=1) > 0))
    dos = float(np.mean((score[:, 0] > 0) & (score[:, 1] > 0)))
    cuerpo = float(np.mean(~np.isnan(pose[:, 0, 0])))
    return una, dos, cuerpo, n


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--etiquetas", nargs="*", help="solo estas palabras (por defecto, todas las descargadas)")
    p.add_argument("--variante", nargs="*", default=list(VARIANTES_LUZ),
                   help="variantes a medir (base debe estar para el % vs base)")
    p.add_argument("--procesos", type=int, default=4)
    p.add_argument("--forzar", action="store_true", help="reextraer aunque haya cache")
    a = p.parse_args(argv)

    cat = catalogo()
    etiquetas = a.etiquetas or sorted(cat)
    faltan = [e for e in etiquetas if e not in cat]
    if faltan:
        print(f"Sin video descargado: {', '.join(faltan)}", file=sys.stderr)
    etiquetas = [e for e in etiquetas if e in cat]
    if not etiquetas:
        print("No hay videos para medir. Bajalos con scripts.descargar_cenarec.", file=sys.stderr)
        return 1

    # 1) Asegurar la extracción de cada variante (reusa cache salvo --forzar).
    trabajos = [(cat[e]["idw"], e, cat[e]["archivo"], v, a.forzar)
                for v in a.variante for e in etiquetas]
    print(f"Extrayendo {len(etiquetas)} videos x {len(a.variante)} variantes "
          f"({len(trabajos)} pasadas, reusa cache)...", flush=True)
    inicio = time.perf_counter()
    hechos, errores = 0, []
    with Pool(a.procesos) as pool:
        for idw, etiqueta, seg, n, estado in pool.imap_unordered(_trabajo, trabajos):
            hechos += 1
            if estado not in ("ok", "cache"):
                errores.append((etiqueta, estado))
            if hechos % 20 == 0 or hechos == len(trabajos):
                print(f"  [{hechos}/{len(trabajos)}]", flush=True)
    for e, estado in errores:
        print(f"ERROR {e}: {estado}", file=sys.stderr)

    # 2) Medir la tasa por variante (promedio sobre los videos).
    resultados = {}
    for v in a.variante:
        unas, doses, cuerpos, frames = [], [], [], 0
        for e in etiquetas:
            if not ruta_cache(cat[e]["idw"], v).exists():
                continue
            una, dos, cuerpo, n = tasas_video(cat[e]["idw"], v)
            unas.append(una); doses.append(dos); cuerpos.append(cuerpo); frames += n
        resultados[v] = {
            "videos": len(unas),
            "frames": frames,
            "manos1": float(np.mean(unas)) if unas else 0.0,
            "manos2": float(np.mean(doses)) if doses else 0.0,
            "pose": float(np.mean(cuerpos)) if cuerpos else 0.0,
        }

    # 3) Tabla.
    base = resultados.get("base", {}).get("manos1", 0.0)
    print(f"\nTasa de detección sobre {len(etiquetas)} videos del CENAREC "
          f"(promedio por video). Extracción en {time.perf_counter() - inicio:.0f} s.\n")
    cab = f"{'variante':<32} {'manos>=1':>9} {'2 manos':>9} {'pose':>7} {'% vs base':>10}"
    print(cab)
    print("-" * len(cab))
    for v in a.variante:
        r = resultados[v]
        vs = 100 * r["manos1"] / base if base else 0.0
        marca = "" if v == "base" else ("  OK" if vs >= 90 else "  <90%")
        print(f"{NOMBRE.get(v, v):<32} {r['manos1']*100:>8.1f}% {r['manos2']*100:>8.1f}% "
              f"{r['pose']*100:>6.1f}% {vs:>9.1f}%{marca}")

    # 4) Guardar el detalle (en extraccion/, ignorado por git) para dejar reproducible el número.
    destino = EXTRACCION / "luz_baseline.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(
        {"videos": etiquetas, "base_manos1": base, "resultados": resultados},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDetalle en {destino}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
