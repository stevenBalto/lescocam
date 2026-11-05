"""Mide en qué porcentaje de cuadros se detectan las DOS manos (problema 3).

Toma las palabras de dos manos de la base (manos = 2) y, para cada repetición,
cuenta los cuadros entre `inicio` y `fin` (la seña, sin el reposo) que tienen
0, 1 o 2 manos en la extracción guardada de CENAREC. No vuelve a correr MediaPipe:
usa data/dictionary/cenarec/extraccion/<variante>/<idw>.npz.

Meta del problema 3: ≥ 90 % de cuadros con ambas manos.

Uso:
    .venv/bin/python -m scripts.medir_dos_manos
    .venv/bin/python -m scripts.medir_dos_manos --variante lejos --peores 20
    .venv/bin/python -m scripts.medir_dos_manos --guardar hiloEquipo/medidas/fase1.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

CENAREC = Path("data/dictionary/cenarec")
DB = CENAREC / "senas_todas.db"
META = 0.90


def palabras_dos_manos(db: Path) -> dict[str, dict]:
    """{etiqueta: {"idw", "tramos": [(inicio, fin), ...]}} de las palabras con manos = 2."""
    con = sqlite3.connect(db)
    filas = con.execute("""SELECT p.etiqueta, p.idw, t.inicio, t.fin FROM palabras p
                           JOIN plantillas t ON t.palabra_id = p.id
                           WHERE p.manos = 2 AND p.idw IS NOT NULL ORDER BY p.etiqueta, t.repeticion""").fetchall()
    con.close()
    salida: dict[str, dict] = {}
    for etiqueta, idw, inicio, fin in filas:
        salida.setdefault(etiqueta, {"idw": idw, "tramos": []})["tramos"].append((inicio, fin))
    return salida


def contar(npz: Path, tramos: list[tuple[float, float]]) -> dict:
    """Cuadros con 0, 1 y 2 manos dentro de los tramos, y cuántos tienen las dos del mismo lado."""
    z = np.load(npz)
    t, lado = z["t"], z["lado"]
    dentro = np.zeros(len(t), dtype=bool)
    for inicio, fin in tramos:
        dentro |= (t >= inicio - 1e-6) & (t <= fin + 1e-6)
    n = (lado[dentro] >= 0).sum(axis=1)
    mismo = int(((lado[dentro, 0] >= 0) & (lado[dentro, 0] == lado[dentro, 1])).sum())
    return {"cuadros": int(dentro.sum()), "0": int((n == 0).sum()), "1": int((n == 1).sum()),
            "2": int((n == 2).sum()), "mismo_lado": mismo}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DB)
    ap.add_argument("--variante", default="base", help="carpeta de extraccion/ (base, lejos, cerca, 15fps, ...)")
    ap.add_argument("--peores", type=int, default=15, help="cuántas palabras peores mostrar")
    ap.add_argument("--guardar", type=Path, help="guardar el resultado en JSON")
    a = ap.parse_args(argv)

    if not a.db.exists():
        print(f"No existe {a.db}. Generala con construir_palabras --todas (ver hiloBackend/).", file=sys.stderr)
        return 1
    palabras = palabras_dos_manos(a.db)
    carpeta = CENAREC / "extraccion" / a.variante
    total = {"cuadros": 0, "0": 0, "1": 0, "2": 0, "mismo_lado": 0}
    por_palabra, faltan = {}, []
    for etiqueta, d in palabras.items():
        npz = carpeta / f"{d['idw']:05d}.npz"
        if not npz.exists():
            faltan.append(etiqueta)
            continue
        c = contar(npz, d["tramos"])
        por_palabra[etiqueta] = c
        for k in total:
            total[k] += c[k]

    if not total["cuadros"]:
        print("No hay cuadros para medir.", file=sys.stderr)
        return 1
    pct = {k: total[k] / total["cuadros"] for k in ("0", "1", "2")}
    fr = {e: c["2"] / c["cuadros"] for e, c in por_palabra.items() if c["cuadros"]}
    sobre_meta = sum(v >= META for v in fr.values())

    print(f"Variante: {a.variante} · palabras de dos manos: {len(por_palabra)}"
          + (f" (sin extracción: {len(faltan)})" if faltan else ""))
    print(f"Cuadros de seña: {total['cuadros']}")
    print(f"  ambas manos: {pct['2']:.1%}   una: {pct['1']:.1%}   ninguna: {pct['0']:.1%}")
    print(f"  las dos con el mismo lado (duplicado probable): {total['mismo_lado']}")
    print(f"Palabras con ≥ {META:.0%} de cuadros con ambas manos: {sobre_meta}/{len(fr)}")
    print(f"Mediana por palabra: {np.median(list(fr.values())):.1%}")
    print(f"\nMeta (≥ {META:.0%} de cuadros con ambas manos): {'CUMPLIDA' if pct['2'] >= META else 'no cumplida'}")
    if a.peores:
        print(f"\nPeores {a.peores}:")
        for e, v in sorted(fr.items(), key=lambda x: x[1])[:a.peores]:
            c = por_palabra[e]
            print(f"  {e:<22} {v:6.1%}  ({c['2']}/{c['cuadros']} cuadros; una: {c['1']}, ninguna: {c['0']})")

    if a.guardar:
        a.guardar.parent.mkdir(parents=True, exist_ok=True)
        a.guardar.write_text(json.dumps({"variante": a.variante, "palabras": len(por_palabra), "total": total,
                                         "porcentaje_ambas": round(pct["2"], 4), "sobre_meta": sobre_meta,
                                         "por_palabra": por_palabra}, ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8")
        print(f"\nGuardado en {a.guardar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
