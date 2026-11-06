"""Prueba configuraciones del detector de dos manos sobre una muestra (problema 3, fase 2).

Para cada configuración re-extrae una muestra de palabras de DOS manos de
CENAREC y compara contra la extracción actual ("base"):
  - % de cuadros de seña con ambas manos (como scripts/medir_dos_manos.py);
  - reconocimiento: cada palabra de la muestra se prueba con una repetición
    contra la otra (de la misma configuración), mezcladas con las plantillas
    base de todas las demás palabras de dos manos. Así se ve si detectar más
    manos ayuda o empeora.

La extracción queda en data/dictionary/cenarec/extraccion/det_<config>/ (ignorado).

Uso:
    .venv/bin/python -m scripts.probar_deteccion                     # 50 palabras, todas las configs
    .venv/bin/python -m scripts.probar_deteccion --muestra 80 --config conf03 recorte
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from multiprocessing import Pool

import numpy as np

from core import palabras as P
from scripts import evaluar_palabras as E
from scripts.extraer_cenarec import VIDEOS, catalogo, extraer_video, ruta_cache
from scripts.medir_dos_manos import DB, contar, palabras_dos_manos

CONFIGS = {
    "conf03": {"confianza": 0.3},
    "recorte": {"recorte": True},
    "conf03_recorte": {"confianza": 0.3, "recorte": True},
    # recorte sin buscar la mano de un brazo en reposo (det_recorte quedó con la versión anterior)
    "recorte_v2": {"recorte": True},
}
SEMILLA = 7


def _extraer(args):
    idw, archivo, config = args
    destino = ruta_cache(idw, f"det_{config}")
    if destino.exists():
        return 0.0
    from core.cuerpo import DetectorCuerpo
    inicio = time.perf_counter()
    det = DetectorCuerpo(**CONFIGS[config])
    try:
        datos, fps = extraer_video(VIDEOS / archivo, "base", detector=det)
    finally:
        det.cerrar()
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, fps=np.float64(fps), idw=np.int32(idw), **datos)
    tmp.replace(destino)
    return time.perf_counter() - inicio


def senas(datos: dict) -> dict:
    """etiqueta -> repeticiones segmentadas (como evaluar_palabras)."""
    return {e: E.elegir_reps(P.segmentar(c, t)) for e, (c, t) in datos.items()}


def reconocer(muestra_senas: dict, resto: dict) -> dict:
    res = E.Resultado()
    todas = {**resto, **muestra_senas}
    for ref in (0, 1):
        comp = E.comparador(todas, ref)
        for e, reps in muestra_senas.items():
            if len(reps) > 1 - ref:
                E.probar(comp, e, reps[1 - ref], res)
    return res.resumen()


def cobertura(variante: str, palabras: dict, muestra: list) -> float:
    tot = {"cuadros": 0, "2": 0}
    for e in muestra:
        d = palabras[e]
        c = contar(ruta_cache(d["idw"], variante), d["tramos"])
        tot["cuadros"] += c["cuadros"]
        tot["2"] += c["2"]
    return tot["2"] / tot["cuadros"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--muestra", type=int, default=50)
    ap.add_argument("--config", nargs="*", choices=list(CONFIGS), default=list(CONFIGS))
    ap.add_argument("--procesos", type=int, default=max(1, min(6, (os.cpu_count() or 2) // 2)))
    a = ap.parse_args(argv)

    palabras = palabras_dos_manos(DB)
    cat = catalogo()
    candidatas = sorted(e for e in palabras if e in cat)
    muestra = sorted(random.Random(SEMILLA).sample(candidatas, min(a.muestra, len(candidatas))))
    print(f"Muestra: {len(muestra)} palabras de dos manos (semilla {SEMILLA})")

    for config in a.config:
        trabajos = [(cat[e]["idw"], cat[e]["archivo"], config) for e in muestra]
        inicio = time.perf_counter()
        with Pool(a.procesos) as pool:
            tiempos = list(pool.imap_unordered(_extraer, trabajos))
        nuevos = [x for x in tiempos if x]
        print(f"  extraído {config}: {len(nuevos)} videos en {time.perf_counter() - inicio:.0f} s"
              + (f" ({np.mean(nuevos):.1f} s por video)" if nuevos else " (ya estaba)"))

    resto_etq = [e for e in candidatas if e not in set(muestra)]
    resto = senas(E.cargar(resto_etq, "base", a.procesos))
    print(f"Plantillas base del resto: {len(resto)} palabras\n")

    print(f"{'config':<16} {'ambas manos':>12} {'top-1':>7} {'top-5':>7} {'bien':>7} {'mal':>6}")
    for variante in ["base"] + [f"det_{c}" for c in a.config]:
        cob = cobertura(variante, palabras, muestra)
        r = reconocer(senas(E.cargar(muestra, variante, a.procesos)), resto)
        print(f"{variante:<16} {cob:12.1%} {r['top1']:7.1%} {r['top5']:7.1%} {r['bien']:7.1%} {r['mal']:6.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
