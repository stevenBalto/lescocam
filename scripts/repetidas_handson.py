"""Busca palabras de Hands-On que son la misma seña que otra con otro nombre y arma
data/reference/repetidas_handson.json (lo usa construir_palabras para juntarlas en una sola).

Candidatas: textos parecidos (sin tildes, sin plural -s/-es, o una de las partes de una etiqueta con «/»,
p. ej. «FELIZ» y «FELIZ/CONTENTO/ALEGRE»). Se juntan solo si:
  * al menos una de las dos es SOLO de Hands-On (dos palabras de CENAREC nunca: CENAREC las separa
    a propósito, como NIÑO y NIÑO-2 o DULCE (SABOR) y DULCE (CARÁCTER));
  * la seña se parece tanto como dos repeticiones de la misma palabra: coseno medio entre plantillas
    >= UMBRAL con el modelo Slovo (misma palabra: mediana 0.80; dos palabras al azar: p99 0.54).
Si una palabra de Hands-On se parece a varias, va con la más parecida (CENAREC primero si empatan).

Necesita data/dictionary/senas_completa.db y los modelos de Slovo (data/dictionary/slovo/modelo/,
ignorados por git). El JSON sí se versiona: en las demás PCs basta con él.

Uso:
    .venv/Scripts/python -m scripts.repetidas_handson
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np

from core import palabras as P
from core import senas_db
from scripts import extraer_handson as H
from scripts.construir_palabras import REPETIDAS, clave_palabra, repeticiones
from scripts.extraer_cenarec import CON_RECORTE, catalogo, ruta_cache

UMBRAL = 0.70
MODELOS = ("embedding_slovo", "embedding_slovo_s1", "embedding_slovo_s2")
CARPETA_MODELOS = senas_db.RAIZ / "data" / "dictionary" / "slovo" / "modelo"


def texto_base(etiqueta: str) -> str:
    """«CÓMO-2» -> «como»; «PROFESORES» -> «profesor»; «ABUELOS» -> «abuelo»."""
    t = re.sub(r"\(.*?\)", "", unicodedata.normalize("NFC", etiqueta))
    t = re.sub(r"-?\d+$", "", t.strip())
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[\s_-]+", " ", t).strip()
    return " ".join(w[:-2] if w.endswith("es") and len(w) > 4 else w[:-1] if w.endswith("s") and len(w) > 3 else w
                    for w in t.split())


def candidatas(etiquetas) -> list[tuple[str, str]]:
    """Pares (a, b), a < b, con el mismo texto base o una parte de una etiqueta con «/»."""
    grupos = defaultdict(set)
    for e in etiquetas:
        grupos[texto_base(e)].add(e)
        if "/" in e:
            for parte in e.split("/"):
                grupos[texto_base(parte)].add(e)
    pares = set()
    for g in grupos.values():
        g = sorted(g)
        pares.update((g[i], g[j]) for i in range(len(g)) for j in range(i + 1, len(g)))
    return sorted(pares)


def elegir(pares_sim: list[tuple[float, str, str]], de_cenarec: set, umbral: float = UMBRAL) -> dict:
    """{etiqueta de Hands-On: etiqueta con la que se junta}. Nunca junta dos de CENAREC; sin cadenas ni ciclos."""
    mejor = {}
    for s, a, b in sorted(pares_sim, reverse=True):
        if s < umbral or (a in de_cenarec and b in de_cenarec):
            continue
        # se mueve la de Hands-On; si las dos son de Hands-On, queda el nombre con tilde y sin plural
        # («EXTRAÑAR» y no «EXTRANAR»), salvo que la otra ya tenga pareja
        if a in de_cenarec:
            origen, destino = b, a
        elif b in de_cenarec:
            origen, destino = a, b
        else:
            queda, sale = sorted((a, b), key=lambda x: (x.isascii(), x.endswith("S"), x))
            origen, destino = (sale, queda) if sale not in mejor else (queda, sale)
        if origen not in mejor:
            mejor[origen] = destino
    salida = {}
    for origen in mejor:
        destino, vistos = mejor[origen], {origen}
        while destino in mejor and destino not in vistos:   # A -> B -> C: A va a C
            vistos.add(destino)
            destino = mejor[destino]
        if destino != origen:
            salida[origen] = destino
    return salida


def _embeber_plantillas(etiquetas: set) -> tuple[np.ndarray, np.ndarray]:
    from scripts.entrada_modelo import entrada
    from scripts.entrenar_embedding import embeber
    from scripts.modelo_senas import cargar
    xs, etq = [], []

    def sumar(ruta, e):
        for s in repeticiones(ruta)[0]:
            d = entrada(s, P.espejos_posibles(s, "derecha")[0], True)
            if d is not None:
                xs.append(d), etq.append(e)

    cat, por_clave = catalogo(), {}
    for e in sorted(cat):
        if e in etiquetas and ruta_cache(cat[e]["idw"], CON_RECORTE).exists():
            por_clave.setdefault(clave_palabra(e), e)
            sumar(ruta_cache(cat[e]["idw"], CON_RECORTE), e)
    hcat = H.catalogo()
    for vid in sorted(hcat):
        k = clave_palabra(hcat[vid]["etiqueta"])
        e = por_clave.get(k, k)
        if e in etiquetas and H.ruta_cache(vid, CON_RECORTE).exists():
            sumar(H.ruta_cache(vid, CON_RECORTE), e)
    X = np.stack(xs).astype(np.float32)
    emb = np.mean([embeber(cargar(CARPETA_MODELOS / f"{m}.pt", "cpu"), X, "cpu") for m in MODELOS], axis=0)
    return emb / np.linalg.norm(emb, axis=1, keepdims=True), np.array(etq)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=senas_db.RUTA_DB_COMPLETA)
    p.add_argument("--umbral", type=float, default=UMBRAL)
    p.add_argument("--salida", type=Path, default=REPETIDAS)
    a = p.parse_args(argv)
    db = senas_db.leer(a.db)
    etiquetas = {e for e, d in db["palabras"].items() if d["categoria"] == "palabra"}
    de_cenarec = {e for e in etiquetas if e in catalogo()}
    pares = candidatas(etiquetas)
    emb, etq = _embeber_plantillas(etiquetas)
    por = defaultdict(list)
    for i, e in enumerate(etq):
        por[e].append(i)
    sims = [(float((emb[por[x]] @ emb[por[y]].T).mean()), x, y) for x, y in pares if por[x] and por[y]]
    juntar = elegir(sims, de_cenarec, a.umbral)
    detalle = {o: round(next(s for s, x, y in sims if {x, y} == {o, d}), 3) for o, d in juntar.items()}
    a.salida.write_text(json.dumps({
        "como": f"scripts/repetidas_handson.py, umbral {a.umbral} (coseno medio con {', '.join(MODELOS)})",
        "juntar": {clave_palabra(o): clave_palabra(d) for o, d in sorted(juntar.items())},
        "parecido": {o: detalle[o] for o in sorted(juntar)},
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(pares)} pares candidatos; se juntan {len(juntar)} -> {a.salida}")
    for o, d in sorted(juntar.items()):
        print(f"  {o} -> {d} ({detalle[o]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
