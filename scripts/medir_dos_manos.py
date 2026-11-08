"""Mide en qué porcentaje de cuadros se detectan las DOS manos (problema 3).

Toma las palabras de dos manos de la base (manos = 2) y, para cada repetición,
cuenta los cuadros entre `inicio` y `fin` (la seña, sin el reposo) que tienen
0, 1 o 2 manos en la extracción guardada. No vuelve a correr MediaPipe:
usa data/dictionary/cenarec/extraccion/<variante>/<idw>.npz (o handson/extraccion/...).

Meta del problema 3: ≥ 90 % de cuadros con ambas manos.

Uso:
    .venv/bin/python -m scripts.medir_dos_manos
    .venv/bin/python -m scripts.medir_dos_manos --variante lejos --peores 20
    .venv/bin/python -m scripts.medir_dos_manos --guardar hiloEquipo/medidas/fase1.json
    .venv/bin/python -m scripts.medir_dos_manos --db data/dictionary/senas_todas_fuentes.db \
        --fuente handson --variante recorte --brazos-arriba     # Hands-On, solo cuadros con 2 brazos arriba
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


HANDSON = Path("data/dictionary/handson")


def videos_dos_manos(db: Path, fuente: str = "cenarec") -> dict[str, dict]:
    """{nombre: {"npz": función(variante) -> ruta, "tramos": [...]}} de cada VIDEO de una palabra de dos manos.

    fuente: "cenarec", "handson" o "todas" (sale del campo `fuente` de cada plantilla: "cenarec:<archivo>",
    "handson:<archivo>"). Con Hands-On una palabra puede tener varios videos: se mide cada uno.
    """
    con = sqlite3.connect(db)
    filas = con.execute("""SELECT p.etiqueta, p.idw, t.fuente, t.inicio, t.fin FROM palabras p
                           JOIN plantillas t ON t.palabra_id = p.id
                           WHERE p.manos = 2 ORDER BY p.etiqueta, t.repeticion""").fetchall()
    con.close()
    salida: dict[str, dict] = {}
    for etiqueta, idw, origen, inicio, fin in filas:
        tipo, _, archivo = (origen or "").partition(":")
        if fuente != "todas" and tipo != fuente:
            continue
        if tipo == "cenarec" and idw is not None:
            nombre, npz = etiqueta, (lambda v, i=idw: CENAREC / "extraccion" / v / f"{int(i):05d}.npz")
        elif tipo == "handson":
            vid = Path(archivo).stem.rsplit("_", 1)[-1]
            nombre, npz = f"{etiqueta} [Hands-On {vid}]", (lambda v, i=vid: HANDSON / "extraccion" / v / f"{i}.npz")
        else:
            continue
        salida.setdefault(nombre, {"npz": npz, "tramos": []})["tramos"].append((inicio, fin))
    return salida


ASPECTO = 16 / 9      # CENAREC (640x360) y Hands-On (960x540): la pose viene en coordenadas 0..1
REPOSO_Y = 0.85       # = core/cuerpo.REPOSO_Y


def brazos_arriba(pose: np.ndarray) -> np.ndarray:
    """Cuadros en que la pose ve las DOS muñecas dentro de la imagen y fuera del reposo.

    Sirve para medir el detector y no la seña: si la persona hace la palabra con una sola mano
    (en Hands-On algunas palabras de dos manos de CENAREC se hacen con una) o tiene una mano
    abajo, fuera del cuadro, ese cuadro no cuenta.
    """
    hx, hy = pose[:, [11, 12], 0] * ASPECTO, pose[:, [11, 12], 1]
    ancho = np.hypot(hx[:, 0] - hx[:, 1], hy[:, 0] - hy[:, 1])
    centro = hy.mean(axis=1)
    m = pose[:, [15, 16]]
    with np.errstate(invalid="ignore", divide="ignore"):
        ok = (m[..., 1] < 0.98) & (m[..., 3] > 0.5) & ((m[..., 1] - centro[:, None]) / ancho[:, None] < REPOSO_Y)
    return ok.all(axis=1) & (ancho > 0)


def contar(npz: Path, tramos: list[tuple[float, float]], solo_arriba: bool = False) -> dict:
    """Cuadros con 0, 1 y 2 manos dentro de los tramos, y cuántos tienen las dos del mismo lado.

    solo_arriba: contar solo los cuadros con los dos brazos levantados (brazos_arriba)."""
    z = np.load(npz)
    t, lado = z["t"], z["lado"]
    dentro = np.zeros(len(t), dtype=bool)
    for inicio, fin in tramos:
        dentro |= (t >= inicio - 1e-6) & (t <= fin + 1e-6)
    if solo_arriba:
        dentro &= brazos_arriba(z["pose"])
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
    ap.add_argument("--fuente", default="cenarec", choices=("cenarec", "handson", "todas"),
                    help="videos de qué diccionario medir (la base tiene que tener sus plantillas)")
    ap.add_argument("--brazos-arriba", action="store_true",
                    help="contar solo cuadros en que la pose ve los dos brazos levantados (mide el detector, no la seña)")
    a = ap.parse_args(argv)

    if not a.db.exists():
        print(f"No existe {a.db}. Generala con construir_palabras --todas (ver hiloBackend/).", file=sys.stderr)
        return 1
    palabras = videos_dos_manos(a.db, a.fuente)
    total = {"cuadros": 0, "0": 0, "1": 0, "2": 0, "mismo_lado": 0}
    por_palabra, faltan = {}, []
    for etiqueta, d in palabras.items():
        npz = d["npz"](a.variante)
        if not npz.exists():
            faltan.append(etiqueta)
            continue
        c = contar(npz, d["tramos"], a.brazos_arriba)
        por_palabra[etiqueta] = c
        for k in total:
            total[k] += c[k]

    if not total["cuadros"]:
        print("No hay cuadros para medir.", file=sys.stderr)
        return 1
    pct = {k: total[k] / total["cuadros"] for k in ("0", "1", "2")}
    fr = {e: c["2"] / c["cuadros"] for e, c in por_palabra.items() if c["cuadros"]}
    sobre_meta = sum(v >= META for v in fr.values())

    print(f"Fuente: {a.fuente} · variante: {a.variante} ·" + (" solo con los dos brazos arriba ·" if a.brazos_arriba else "") + f" videos de palabras de dos manos: {len(por_palabra)}"
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
        a.guardar.write_text(json.dumps({"fuente": a.fuente, "db": str(a.db), "brazos_arriba": a.brazos_arriba, "variante": a.variante, "palabras": len(por_palabra), "total": total,
                                         "porcentaje_ambas": round(pct["2"], 4), "sobre_meta": sobre_meta,
                                         "por_palabra": por_palabra}, ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8")
        print(f"\nGuardado en {a.guardar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
