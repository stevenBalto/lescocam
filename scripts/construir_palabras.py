"""Arma data/reference/senas.db con las plantillas de las palabras de CENAREC.

Lee el cache de scripts/extraer_cenarec.py (no vuelve a correr MediaPipe), corta
cada video en sus repeticiones con el mismo Segmentador del modo en vivo
(core/palabras.py) y guarda cada repetición como plantilla (core/senas_db.py).

Además entran las letras deletreadas de CENAREC (LETRA-A ... LETRA-Ñ) con
categoría "letra": son plantillas NEGATIVAS (si una seña se parece más a una
letra que a cualquier palabra, el modo palabra no dice nada). --sin-letras las saca.

Si un video no da exactamente 2 repeticiones:
  - más de 2: se quedan las 2 más largas (las otras suelen ser un amague);
  - 1: se guarda esa sola;
  - 0: la palabra no entra (se avisa).

Uso:
    .venv/bin/python -m scripts.construir_palabras                    # palabras_iniciales.txt -> senas.db
    .venv/bin/python -m scripts.construir_palabras --todas \\
        --salida data/dictionary/cenarec/senas_todas.db                 # las 1072 (no se versiona)
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from core import palabras as P
from core import senas_db
from core.cuerpo import desde_arrays
from scripts.extraer_cenarec import LISTA, catalogo, leer_lista, ruta_cache

PESOS_CRUDOS = (1.0, 1.0, 1.0, 1.0, 1.0)
PREFIJO_LETRA = "LETRA-"


def cargar_video(ruta: Path) -> tuple[list, list]:
    """(CuadroPalabra o None por frame, tiempos) desde un .npz del cache."""
    datos = np.load(ruta)
    cuerpo = desde_arrays(datos)
    return [P.cuadro_palabra(c) for c in cuerpo], [c.t for c in cuerpo]


def repeticiones(ruta: Path) -> tuple[list, int]:
    """(repeticiones elegidas en orden de tiempo, cuántas dio el Segmentador)."""
    cuadros, tiempos = cargar_video(ruta)
    senas = P.segmentar(cuadros, tiempos)
    elegidas = senas
    if len(senas) > 2:
        largas = sorted(senas, key=lambda s: s[-1].t - s[0].t, reverse=True)[:2]
        elegidas = sorted(largas, key=lambda s: s[0].t)
    return elegidas, len(senas)


def crudo(sena: list) -> tuple[np.ndarray, int]:
    """(descriptor SIN pesos de la referencia, manos 1 o 2). La persona de CENAREC es diestra."""
    espejo = P.espejos_posibles(sena, "derecha")[0]
    d = P.descriptor(sena, espejo, pesos=PESOS_CRUDOS)
    return d, (2 if d is not None and d[0, -1] > 0 else 1)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lista", type=Path, default=LISTA)
    p.add_argument("--todas", action="store_true", help="todos los videos con cache")
    p.add_argument("--salida", type=Path, default=senas_db.RUTA_DB)
    p.add_argument("--sin-letras", action="store_true", help="no agregar las letras deletreadas como negativas")
    a = p.parse_args(argv)

    cat = catalogo()
    letras = sorted(e for e in cat if e.startswith(PREFIJO_LETRA))
    etiquetas = sorted(e for e in cat if not e.startswith(PREFIJO_LETRA)) if a.todas else leer_lista(a.lista)
    categorias = {e: "palabra" for e in etiquetas}
    if not a.sin_letras:
        categorias.update({e: "letra" for e in letras})
    entradas, cuentas, sin = [], Counter(), []
    for e in categorias:
        if e not in cat or not ruta_cache(cat[e]["idw"]).exists():
            sin.append(e)
            continue
        reps, n = repeticiones(ruta_cache(cat[e]["idw"]))
        cuentas[n] += 1
        plantillas, manos = [], 1
        for k, s in enumerate(reps, 1):
            d, m = crudo(s)
            if d is None:
                continue
            manos = max(manos, m)
            plantillas.append({"repeticion": k, "fuente": f"cenarec:{cat[e]['archivo']}", "inicio": round(s[0].t, 3),
                               "fin": round(s[-1].t, 3), "crudo": d})
        if not plantillas:
            print(f"{e}: sin repeticiones", file=sys.stderr)
            continue
        if n != 2:
            print(f"{e}: el segmentador dio {n} repeticiones (se guardan {len(plantillas)})")
        entradas.append({"etiqueta": e, "categoria": categorias[e], "idw": cat[e]["idw"], "manos": manos,
                         "fuente": "cenarec", "plantillas": plantillas})
    if sin:
        print(f"Sin cache (correr scripts/extraer_cenarec.py): {', '.join(sin)}", file=sys.stderr)
    senas_db.escribir(a.salida, entradas, "Diccionario LESCO de CENAREC (uso autorizado; videos no redistribuidos)")
    total = sum(len(x["plantillas"]) for x in entradas)
    n_letras = sum(x["categoria"] == "letra" for x in entradas)
    print(f"{a.salida}: {len(entradas) - n_letras} palabras + {n_letras} letras negativas, {total} plantillas, "
          f"{a.salida.stat().st_size / 1024:.0f} KB. "
          f"Repeticiones por video: {dict(sorted(cuentas.items()))}; de dos manos: "
          f"{sum(x['manos'] == 2 for x in entradas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
