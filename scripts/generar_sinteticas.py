"""Recalcula las tomas sintéticas de signs.json a partir de las tomas OFICIALES.

Borra todas las tomas "sintetica:..." y las vuelve a generar con la lista fija
de core/sinteticas.py (sin azar: con las mismas oficiales sale lo mismo). Los
importadores ya lo hacen al guardar; esto sirve después de editar signs.json a
mano o de cambiar VARIANTES.

Uso:
    .venv/bin/python -m scripts.generar_sinteticas            # muestra qué haría
    .venv/bin/python -m scripts.generar_sinteticas --guardar
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from core.clasificador import RUTA_SENAS, categoria_de, escribir_signs, leer_signs, tomas_de
from core.referencia import es_oficial
from core.sinteticas import VARIANTES, es_sintetica, nombre, regenerar


def contar(datos: dict) -> dict:
    """categoría -> (oficiales, sintéticas, sintéticas por seña)."""
    salida: dict = {}
    for etiqueta, entrada in datos["signs"].items():
        fila = salida.setdefault(categoria_de(entrada), [0, 0, Counter()])
        tomas = tomas_de(entrada)
        fila[0] += sum(es_oficial(t) for t in tomas)
        fila[1] += sum(es_sintetica(t) for t in tomas)
        fila[2][etiqueta] = sum(es_sintetica(t) for t in tomas)
    return salida


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--signs", type=Path, default=RUTA_SENAS)
    parser.add_argument("--guardar", action="store_true", help="escribir en signs.json (sin esto solo muestra)")
    args = parser.parse_args(argv)

    datos = leer_signs(args.signs)
    nuevo = regenerar(datos)
    print("Variantes: " + ", ".join(nombre(v) for v in VARIANTES))
    for categoria, (of, sin, por) in contar(nuevo).items():
        esperadas = of * len(VARIANTES)
        print(f"  {categoria}: {of} oficiales → {sin}/{esperadas} sintéticas "
              f"({esperadas - sin} descartadas por parecerse a otra seña)")
        oficiales = {e: sum(es_oficial(t) for t in tomas_de(nuevo['signs'][e])) for e in por}
        flojas = [f"{e} {n}/{oficiales[e] * len(VARIANTES)}" for e, n in por.items()
                  if n < oficiales[e] * len(VARIANTES)]
        if flojas:
            print("    con descartes: " + ", ".join(flojas))
    antes = len(json.dumps(datos, indent=2, ensure_ascii=False)) + 1
    despues = len(json.dumps(nuevo, indent=2, ensure_ascii=False)) + 1
    print(f"Peso de signs.json: {antes / 1024:.0f} KB → {despues / 1024:.0f} KB")
    if nuevo == datos:
        print("Las sintéticas ya estaban al día.")
        return 0
    if not args.guardar:
        print("Prueba sin guardar. Agregá --guardar para escribir en signs.json.")
        return 0
    escribir_signs(args.signs, nuevo)
    print(f"Guardado en {args.signs}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
