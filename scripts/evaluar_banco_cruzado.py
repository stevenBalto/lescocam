"""Mide el motor (DTW, sin modelo) usando de PLANTILLA las tomas del banco de OTRAS personas (problema 1, fase 5).

Con las 85 palabras grabadas por las 4 personas (ronda 2) cada toma se compara contra:

    cenarec   solo las plantillas de senas.db (lo que hace hoy el motor)
    equipo    solo las tomas de las otras personas
    todo      senas.db + las tomas de las otras personas

NUNCA contra tomas de la misma persona: se deja una persona afuera por ronda (su número es el de
alguien que el motor no vio nunca). --personas N usa solo N de las otras (todas las combinaciones,
promediadas) para ver cuánto aporta cada persona más.

Cada toma va por el mismo camino que scripts/evaluar_banco.py: Segmentador -> la seña más larga ->
descriptores (con las dos variantes de espejo si es de dos manos). Como plantilla, de una toma de dos
manos se guarda UNA variante: la más parecida a las plantillas de CENAREC de su palabra (la etiqueta
de una plantilla se conoce; la de la toma que se mide, no). Una toma sin seña no da plantilla.

Aceptar = las reglas del motor, sin ajustar nada con el banco: UMBRAL, MARGEN relativo y duración
mínima contra la plantilla más corta de la palabra (core/palabras.ComparadorPalabras.clasificar).
Con las tomas del equipo hay más plantillas por palabra, así que esa duración mínima baja y la regla
queda algo más permisiva que con CENAREC solo.

Se compara contra TODAS las plantillas (sin el prefiltro de 150 del motor en vivo): con "cenarec"
(170 plantillas) da lo mismo que scripts/evaluar_banco.py; con "todo" (~680) el motor en vivo podría
dar valores un poco distintos.

Uso:
    .venv/Scripts/python -m scripts.evaluar_banco_cruzado
    .venv/Scripts/python -m scripts.evaluar_banco_cruzado --personas 1 --json resultado.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

from core import banco
from core import palabras as P
from core import senas_db

FUENTES = ("cenarec", "equipo", "todo")


def describir(tomas: list) -> list[dict]:
    """Por toma: descriptores de la seña más larga (vacío si no hubo seña) y su duración."""
    filas = []
    for t in tomas:
        cp = [P.cuadro_palabra(c) for c in t.cuadros]
        senas = P.segmentar(cp, [c.t for c in t.cuadros])
        fila = {"persona": t.persona, "etiqueta": t.etiqueta, "archivo": t.ruta.name, "variantes": [], "duracion": 0.0}
        if senas:
            sena = max(senas, key=lambda s: s[-1].t - s[0].t)
            fila["variantes"], fila["duracion"] = P.descriptores(sena, "auto"), P.duracion(sena)
        filas.append(fila)
    return filas


def elegir_plantilla(fila: dict, base: dict) -> Optional[np.ndarray]:
    """La variante de la toma que sirve de plantilla: la más cercana a las de CENAREC de su palabra."""
    if not fila["variantes"]:
        return None
    ref = base.get(fila["etiqueta"])
    if ref is None or len(fila["variantes"]) == 1:
        return fila["variantes"][0]
    return min(fila["variantes"], key=lambda v: float(P.dtw_lote(v, ref).min()))


def comparador_para(filas: list[dict], personas: set, db: dict, fuente: str) -> Optional[P.ComparadorPalabras]:
    """Comparador con las plantillas de `fuente` usando las tomas de `personas`."""
    w = senas_db.pesos_columnas()
    etiquetas, plantillas, duraciones = [], [], []
    if fuente in ("cenarec", "todo"):
        for (e, crudo), dur in zip(db["plantillas"], db["duraciones"]):
            etiquetas.append(e), plantillas.append(crudo * w), duraciones.append(dur)
    if fuente in ("equipo", "todo"):
        for f in filas:
            if f["persona"] in personas and f["plantilla"] is not None:
                etiquetas.append(f["etiqueta"]), plantillas.append(f["plantilla"]), duraciones.append(f["duracion"])
    if not etiquetas:
        return None
    categorias = {e: d["categoria"] for e, d in db["palabras"].items()}
    return P.ComparadorPalabras(etiquetas, plantillas, categorias=categorias, prefiltro=None, duraciones=duraciones)


def medir_toma(f: dict, comparador: P.ComparadorPalabras) -> dict:
    """{'top': [3 palabras], 'dicha': palabra aceptada o None}; sin seña: top vacío."""
    if not f["variantes"]:
        return {"top": [], "dicha": None}
    dicha, _, _ = comparador.clasificar(f["variantes"], f["duracion"])
    dist = comparador.distancias(f["variantes"])
    top = [e for e, _ in sorted(dist.items(), key=lambda p: p[1]) if comparador.categorias[e] == "palabra"][:3]
    return {"top": top, "dicha": dicha}


def metricas(pares: list[tuple]) -> dict:
    """pares = [(etiqueta, resultado de medir_toma)]."""
    n = len(pares)
    if not n:
        return {"n": 0}
    cuenta = lambda cond: sum(1 for e, r in pares if cond(e, r)) / n
    return {"n": n,
            "top1": cuenta(lambda e, r: bool(r["top"]) and r["top"][0] == e),
            "top3": cuenta(lambda e, r: e in r["top"]),
            "aceptada_bien": cuenta(lambda e, r: r["dicha"] == e),
            "aceptacion_erronea": cuenta(lambda e, r: r["dicha"] not in (None, e)),
            "sin_sena": cuenta(lambda e, r: not r["top"])}


def evaluar(filas: list[dict], db: dict, fuente: str, n_otras: Optional[int] = None) -> dict:
    """Deja una persona afuera por ronda. n_otras: cuántas de las demás dan plantillas (None = todas);
    con menos que todas se promedian todas las combinaciones (cada toma pesa lo mismo)."""
    personas = sorted({f["persona"] for f in filas})
    por_persona, todos = defaultdict(list), []
    for p in personas:
        otras = [q for q in personas if q != p]
        k = len(otras) if n_otras is None else min(n_otras, len(otras))
        combos = [set(otras)] if fuente == "cenarec" else [set(c) for c in itertools.combinations(otras, k)]
        for combo in combos:
            comparador = comparador_para(filas, combo, db, fuente)
            if comparador is None:
                continue
            for f in filas:
                if f["persona"] == p:
                    r = medir_toma(f, comparador)
                    por_persona[p].append((f["etiqueta"], r))
                    todos.append((f["etiqueta"], r))
    return {"total": metricas(todos), "por_persona": {p: metricas(v) for p, v in por_persona.items()}}


def preparar(filas: list[dict], db: dict) -> None:
    """Agrega a cada fila su 'plantilla' (o None)."""
    w = senas_db.pesos_columnas()
    base = defaultdict(list)
    for e, crudo in db["plantillas"]:
        base[e].append(crudo * w)
    base = {e: np.stack(v) for e, v in base.items()}
    for f in filas:
        f["plantilla"] = elegir_plantilla(f, base)


def _linea(nombre: str, m: dict) -> str:
    if not m.get("n"):
        return f"{nombre:<24} (sin tomas)"
    return (f"{nombre:<24} top1 {m['top1']:6.1%}  top3 {m['top3']:6.1%}  dice bien {m['aceptada_bien']:6.1%}  "
            f"ERRÓNEA {m['aceptacion_erronea']:5.1%}  sin seña {m['sin_sena']:5.1%}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--banco", type=Path, default=banco.CARPETA)
    p.add_argument("--db", type=Path, default=senas_db.RUTA_DB)
    p.add_argument("--personas", type=int, help="cuántas de las otras personas dan plantillas (por defecto, todas)")
    p.add_argument("--json", type=Path)
    a = p.parse_args(argv)
    if a.personas is not None and a.personas < 1:
        p.error("--personas tiene que ser 1 o más")

    tomas = banco.cargar_tomas(a.banco)
    if not tomas:
        print(f"No hay tomas en {a.banco}")
        return 1
    db = senas_db.leer(a.db)
    filas = describir(tomas)
    preparar(filas, db)
    resumen = {}
    for fuente in FUENTES:
        r = evaluar(filas, db, fuente, a.personas)
        resumen[fuente] = r
        print(_linea(fuente, r["total"]))
        for persona, m in r["por_persona"].items():
            print(_linea("    " + persona, m))
    if a.json:
        a.json.write_text(json.dumps(resumen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
