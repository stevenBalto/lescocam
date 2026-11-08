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

Extracción: por defecto la carpeta `recorte` (DetectorCuerpo(recorte=True), lo
que usa la app; problema 3). --extraccion base usa la de antes, sin recorte.

Hands-On (--handson): suma las plantillas de data/dictionary/handson/ (otra
persona, scripts/extraer_handson.py). Las palabras se juntan por `clave_palabra`
(mayúsculas, sin paréntesis ni número final: «aprovechar 2» y «APROVECHAR» son la
misma): si la palabra ya está en CENAREC se le agregan plantillas; si no, entra
como palabra nueva (solo con --todas; con la lista, solo las de la lista).

Uso:
    .venv/bin/python -m scripts.construir_palabras                    # palabras_iniciales.txt -> senas.db
    .venv/bin/python -m scripts.construir_palabras --handson          # + plantillas de Hands-On
    .venv/bin/python -m scripts.construir_palabras --todas \\
        --salida data/dictionary/cenarec/senas_todas.db                 # las 1072 (no se versiona)
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from core import palabras as P
from core import senas_db
from core.cuerpo import desde_arrays
from scripts import extraer_handson as H
from scripts.extraer_cenarec import CON_RECORTE, LISTA, catalogo, leer_lista, ruta_cache

PESOS_CRUDOS = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
PREFIJO_LETRA = "LETRA-"


def clave_palabra(texto: str) -> str:
    """Para juntar la misma palabra de fuentes distintas: «Café (bebida)», «CAFÉ», «café 2» -> «CAFÉ»;
    «por favor» y «POR-FAVOR» -> «POR-FAVOR»."""
    t = re.sub(r"\(.*?\)", "", texto).strip().upper()
    t = re.sub(r"[\s_-]+", "-", t)
    return re.sub(r"-?\d+$", "", t).strip("-")


def plantillas_de(ruta: Path, fuente: str, desde: int = 1) -> tuple[list, int, int]:
    """(plantillas, manos 1 o 2, cuántas repeticiones dio el Segmentador) de un video del cache."""
    reps, n = repeticiones(ruta)
    plantillas, manos = [], 1
    for k, s in enumerate(reps, desde):
        d, m = crudo(s)
        if d is None:
            continue
        manos = max(manos, m)
        plantillas.append({"repeticion": k, "fuente": fuente, "inicio": round(s[0].t, 3),
                           "fin": round(s[-1].t, 3), "crudo": d})
    return plantillas, manos, n


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
    p.add_argument("--extraccion", default=CON_RECORTE, help="carpeta de extraccion/ (recorte o base)")
    p.add_argument("--handson", action="store_true", help="sumar las plantillas de Hands-On")
    a = p.parse_args(argv)

    cat = catalogo()
    letras = sorted(e for e in cat if e.startswith(PREFIJO_LETRA))
    etiquetas = sorted(e for e in cat if not e.startswith(PREFIJO_LETRA)) if a.todas else leer_lista(a.lista)
    categorias = {e: "palabra" for e in etiquetas}
    if not a.sin_letras:
        categorias.update({e: "letra" for e in letras})
    entradas, cuentas, sin = [], Counter(), []
    for e in categorias:
        if e not in cat or not ruta_cache(cat[e]["idw"], a.extraccion).exists():
            sin.append(e)
            continue
        plantillas, manos, n = plantillas_de(ruta_cache(cat[e]["idw"], a.extraccion), f"cenarec:{cat[e]['archivo']}")
        cuentas[n] += 1
        if not plantillas:
            print(f"{e}: sin repeticiones", file=sys.stderr)
            continue
        if n != 2:
            print(f"{e}: el segmentador dio {n} repeticiones (se guardan {len(plantillas)})")
        entradas.append({"etiqueta": e, "categoria": categorias[e], "idw": cat[e]["idw"], "manos": manos,
                         "fuente": "cenarec", "plantillas": plantillas})

    if a.handson:
        # Misma palabra en las dos fuentes -> una sola palabra con las plantillas de las dos personas.
        por_clave = {}
        for x in entradas:
            if x["categoria"] == "palabra":
                por_clave.setdefault(clave_palabra(x["etiqueta"]), x)
        lista = {clave_palabra(e) for e in etiquetas}
        hcat = H.catalogo()
        sumadas = nuevas = sin_cache = 0
        for vid in sorted(hcat, key=lambda v: (hcat[v]["etiqueta"], v)):
            k = clave_palabra(hcat[vid]["etiqueta"])
            if not a.todas and k not in lista:
                continue
            ruta = H.ruta_cache(vid, a.extraccion)
            if not ruta.exists():
                sin_cache += 1
                continue
            x = por_clave.get(k)
            desde = 1 + max((t["repeticion"] for t in x["plantillas"]), default=0) if x else 1
            plantillas, manos, n = plantillas_de(ruta, f"handson:{hcat[vid]['archivo']}", desde)
            cuentas[n] += 1
            if not plantillas:
                print(f"{hcat[vid]['etiqueta']} (Hands-On {vid}): sin repeticiones", file=sys.stderr)
                continue
            if x is None:
                x = {"etiqueta": k, "categoria": "palabra", "idw": None, "manos": manos, "fuente": "handson",
                     "plantillas": []}
                entradas.append(x)
                por_clave[k] = x
                nuevas += 1
            else:
                sumadas += 1
                if x["fuente"] == "cenarec":
                    x["fuente"] = "cenarec+handson"
            x["plantillas"] += plantillas
            x["manos"] = max(x["manos"], manos)
        print(f"Hands-On: {sumadas} videos sumados a palabras que ya estaban, {nuevas} palabras nuevas"
              + (f", {sin_cache} sin extracción (scripts/extraer_handson.py)" if sin_cache else ""))
    if sin:
        print(f"Sin cache (correr scripts/extraer_cenarec.py): {', '.join(sin)}", file=sys.stderr)
    fuente = "Diccionario LESCO de CENAREC" + (" y diccionario de Hands-On LESCO" if a.handson else "")
    senas_db.escribir(a.salida, entradas, f"{fuente} (uso autorizado; videos no redistribuidos; extracción {a.extraccion})")
    total = sum(len(x["plantillas"]) for x in entradas)
    n_letras = sum(x["categoria"] == "letra" for x in entradas)
    print(f"{a.salida}: {len(entradas) - n_letras} palabras + {n_letras} letras negativas, {total} plantillas, "
          f"{a.salida.stat().st_size / 1024:.0f} KB. "
          f"Repeticiones por video: {dict(sorted(cuentas.items()))}; de dos manos: "
          f"{sum(x['manos'] == 2 for x in entradas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
