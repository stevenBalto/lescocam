"""Reconocimiento ENTRE PERSONAS: plantillas de un diccionario, prueba con el otro.

CENAREC y Hands-On son dos personas distintas que hacen las mismas palabras.
Para las palabras que están en los dos (misma `clave_palabra`):
  - cenarec→handson: plantillas de TODAS las palabras de CENAREC, se prueba cada
    repetición de los videos de Hands-On;
  - handson→cenarec: al revés.
Es la prueba más cercana a "otra persona frente a la cámara" que tenemos sin
grabar (el banco de prueba es la otra). Sirve para decidir pesos del descriptor
(por ejemplo la cara, problema 3 fase 3) y comparar extracciones.

Métricas: top-1 / top-5 (la palabra correcta entre las más parecidas),
aceptadas bien / mal (el motor la dijo, pasando umbral y margen).

Uso:
    .venv/bin/python -m scripts.evaluar_fuentes
    .venv/bin/python -m scripts.evaluar_fuentes --caras 0 1 2          # comparar pesos de la cara
    .venv/bin/python -m scripts.evaluar_fuentes --extraccion base       # extracción sin recorte
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from core import palabras as P
from scripts import extraer_handson as H
from scripts.construir_palabras import PREFIJO_LETRA, clave_palabra, repeticiones
from scripts.evaluar_palabras import Resultado, fmt
from scripts.extraer_cenarec import CON_RECORTE, catalogo, ruta_cache


def _reps(args):
    clave, ruta = args
    try:
        return clave, repeticiones(ruta)[0]
    except Exception:
        return clave, []


def cargar(extraccion: str, procesos: int) -> tuple[dict, dict]:
    """({clave: [repeticiones]} de CENAREC, ídem de Hands-On) con las extracciones que existen."""
    cat = catalogo()
    trabajos_c = [(clave_palabra(e), ruta_cache(d["idw"], extraccion)) for e, d in cat.items()
                  if not e.startswith(PREFIJO_LETRA) and ruta_cache(d["idw"], extraccion).exists()]
    hcat = H.catalogo()
    trabajos_h = [(clave_palabra(d["etiqueta"]), H.ruta_cache(v, extraccion)) for v, d in hcat.items()
                  if H.ruta_cache(v, extraccion).exists()]
    salida = []
    for trabajos in (trabajos_c, trabajos_h):
        fuente: dict[str, list] = {}
        with Pool(procesos) as pool:
            for clave, reps in pool.imap_unordered(_reps, trabajos, chunksize=8):
                fuente.setdefault(clave, []).extend(reps)
        salida.append({k: v for k, v in fuente.items() if v})
    return salida[0], salida[1]


def comparador(plantillas: dict, pesos) -> P.ComparadorPalabras:
    etq, desc = [], []
    for clave, reps in plantillas.items():
        for s in reps:
            d = P.descriptor(s, P.espejos_posibles(s, "derecha")[0], pesos=pesos)
            if d is not None:
                etq.append(clave)
                desc.append(d)
    return P.ComparadorPalabras(etq, desc)


def probar(plantillas: dict, pruebas: dict, comunes: list, pesos) -> Resultado:
    comp = comparador(plantillas, pesos)
    res = Resultado()
    for clave in comunes:
        for s in pruebas[clave]:
            cand = P.descriptores(s, "auto", pesos=pesos)
            if not cand:
                res.agregar(clave, [], None)
                continue
            palabra, _, top = comp.clasificar(cand)
            res.agregar(clave, top, palabra)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extraccion", default=CON_RECORTE, help="carpeta de extracción (recorte o base)")
    ap.add_argument("--caras", nargs="*", type=float, help="pesos de la cara a comparar (por defecto el actual)")
    ap.add_argument("--procesos", type=int, default=max(1, min(6, (os.cpu_count() or 2) // 2)))
    ap.add_argument("--guardar", type=Path, help="guardar el resultado en JSON")
    a = ap.parse_args(argv)

    cenarec, handson = cargar(a.extraccion, a.procesos)
    comunes = sorted(set(cenarec) & set(handson))
    print(f"Extracción {a.extraccion}: CENAREC {len(cenarec)} palabras, Hands-On {len(handson)} palabras, "
          f"en las dos: {len(comunes)}")
    if not comunes:
        print("No hay palabras en común para probar.", file=sys.stderr)
        return 1
    base = P.pesos_completos()
    resultados = {}
    for cara in (a.caras if a.caras else [base[5]]):
        pesos = base[:5] + (cara,)
        for nombre, plant, prueba in (("cenarec→handson", cenarec, handson), ("handson→cenarec", handson, cenarec)):
            res = probar(plant, prueba, comunes, pesos)
            r = res.resumen()
            resultados[f"cara={cara} {nombre}"] = r
            print(f"cara={cara:<4} {nombre}: {fmt(r)}", flush=True)
            if cara == (a.caras or [base[5]])[0]:
                print("   confusiones:", ", ".join(f"{v}->{p} x{n}" for (v, p), n in res.confusiones(8)))
    if a.guardar:
        a.guardar.parent.mkdir(parents=True, exist_ok=True)
        a.guardar.write_text(json.dumps({"extraccion": a.extraccion, "comunes": len(comunes),
                                         "resultados": resultados}, ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8")
        print(f"Guardado en {a.guardar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
