"""Mide el motor de palabras actual contra el banco de prueba (data/banco/).

Cada toma pasa por el mismo camino que en vivo: Segmentador -> descriptores ->
ComparadorPalabras con TODAS las plantillas de senas.db (85 palabras + letras
negativas), no solo las 30 del banco. Si el segmentador encuentra varias señas
en la toma, se evalúa la más larga; si no encuentra ninguna, la toma cuenta como
fallo ("sin seña").

Métricas (sobre todas las tomas):
  top-1 / top-3   la palabra pedida está entre las 1 / 3 más parecidas (solo palabras)
  aceptada bien   el motor dijo la palabra pedida (pasa umbral y margen)
  aceptación errónea   el motor dijo OTRA palabra con seguridad (la meta pide <= 2 %)
  no dice nada    ni bien ni mal: no pasó umbral/margen o no hubo seña

Uso:
    .venv/Scripts/python -m scripts.evaluar_banco                    # todo el banco
    .venv/Scripts/python -m scripts.evaluar_banco --persona christian-paniagua
    .venv/Scripts/python -m scripts.evaluar_banco --detalle          # una línea por toma
    .venv/Scripts/python -m scripts.evaluar_banco --json resultado.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from core import banco
from core import palabras as P
from core import senas_db

TOP_K = 3
MEJORES = 10   # candidatos a pedir al comparador antes de filtrar solo palabras


def evaluar_cuadros(cuadros: list, etiqueta: str, comparador: P.ComparadorPalabras) -> dict:
    """Resultado de unos cuadros de cuerpo (CuadroCuerpo): palabra aceptada (o None), top de palabras, si hubo seña.

    Agrega `fuera_reposo_s` (segundos con algún brazo fuera de reposo) y `duracion_s` de la seña evaluada,
    para explicar por qué no hubo seña (muy corta < DURACION_MIN o muy larga >= DURACION_MAX)."""
    cp = [P.cuadro_palabra(c) for c in cuadros]
    tiempos = [c.t for c in cuadros]
    senas = P.segmentar(cp, tiempos)
    dt = (tiempos[-1] - tiempos[0]) / max(len(tiempos) - 1, 1) if len(tiempos) > 1 else 0.0
    fuera = sum(1 for x in cp if x is not None and not P.en_reposo(x)) * dt
    base = {"etiqueta": etiqueta, "senas": len(senas), "fuera_reposo_s": round(fuera, 2), "duracion_s": 0.0}
    vacio = {**base, "hubo_sena": False, "aceptada": None, "confianza": 0.0, "top": []}
    if not senas:
        return vacio
    sena = max(senas, key=lambda s: s[-1].t - s[0].t)
    base["duracion_s"] = round(sena[-1].t - sena[0].t, 2)
    candidatos = P.descriptores(sena, "auto")
    if not candidatos:
        return vacio
    aceptada, conf, _ = comparador.clasificar(candidatos, duracion=P.duracion(sena))
    top = [(e, c) for e, c in comparador.mejores(candidatos, MEJORES) if comparador.categorias.get(e) == "palabra"]
    return {**base, "hubo_sena": True, "aceptada": aceptada, "confianza": float(conf), "top": top[:5]}


def evaluar_toma(toma: banco.Toma, comparador: P.ComparadorPalabras) -> dict:
    """evaluar_cuadros de una toma del banco, con sus metadatos."""
    r = evaluar_cuadros(toma.cuadros, toma.etiqueta, comparador)
    return {**r, "persona": toma.persona, "camara": toma.camara, "luz": toma.luz, "distancia": toma.distancia, "angulo": toma.angulo,
            "archivo": toma.ruta.name}


def resumen_toma(r: dict) -> tuple[str, str]:
    """(texto corto para pantalla, color: 'ok' | 'mal' | 'nada')."""
    if not r["hubo_sena"]:
        f = r["fuera_reposo_s"]
        if f == 0:
            return "motor: no vio manos levantadas (sube las manos mas arriba, que se vean)", "mal"
        if f >= P.DURACION_MAX:
            return f"motor: sin sena, manos fuera de reposo {f:.1f}s (max {P.DURACION_MAX:.0f}s): hazla mas rapido", "mal"
        return f"motor: sin sena, solo {f:.1f}s con manos arriba (min {P.DURACION_MIN}s)", "mal"
    top = ", ".join(f"{e}={c:.2f}" for e, c in r["top"][:3])
    if r["aceptada"] == r["etiqueta"]:
        return f"motor: {r['aceptada']} OK ({r['confianza']:.2f}) dur {r['duracion_s']}s", "ok"
    if r["aceptada"]:
        return f"motor dijo OTRA: {r['aceptada']} | {top}", "mal"
    return f"motor no se decide | {top}", "nada"


def metricas(filas: list[dict]) -> dict:
    n = len(filas)
    if not n:
        return {"n": 0}
    top1 = sum(1 for f in filas if f["top"] and f["top"][0][0] == f["etiqueta"])
    top3 = sum(1 for f in filas if f["etiqueta"] in [e for e, _ in f["top"][:TOP_K]])
    bien = sum(1 for f in filas if f["aceptada"] == f["etiqueta"])
    mal = sum(1 for f in filas if f["aceptada"] is not None and f["aceptada"] != f["etiqueta"])
    sin_sena = sum(1 for f in filas if not f["hubo_sena"])
    return {"n": n, "top1": top1 / n, "top3": top3 / n, "aceptada_bien": bien / n, "aceptacion_erronea": mal / n,
            "no_dice_nada": (n - bien - mal) / n, "sin_sena": sin_sena / n}


def agrupar(filas: list[dict], clave: str) -> dict:
    grupos: dict = defaultdict(list)
    for f in filas:
        grupos[f[clave]].append(f)
    return {k: metricas(v) for k, v in sorted(grupos.items())}


def confusiones(filas: list[dict], k: int = 8) -> list[tuple]:
    """(pedida, aceptada o mejor del top, veces) de las tomas cuyo top-1 no es la pedida."""
    c = Counter()
    for f in filas:
        if f["top"] and f["top"][0][0] != f["etiqueta"]:
            c[(f["etiqueta"], f["aceptada"] or f["top"][0][0] + " (sin aceptar)")] += 1
    return [(a, b, n) for (a, b), n in c.most_common(k)]


def _linea(nombre: str, m: dict) -> str:
    if not m["n"]:
        return f"{nombre:<22} sin tomas"
    return (f"{nombre:<22} n={m['n']:<4} top1 {m['top1']:6.1%}  top3 {m['top3']:6.1%}  "
            f"bien {m['aceptada_bien']:6.1%}  ERRÓNEA {m['aceptacion_erronea']:5.1%}  "
            f"calla {m['no_dice_nada']:6.1%}  sin seña {m['sin_sena']:5.1%}")


def imprimir(filas: list[dict]) -> dict:
    total = metricas(filas)
    print(f"== banco de prueba: {total['n']} tomas, {len({f['persona'] for f in filas})} firmante(s), "
          f"{len({f['etiqueta'] for f in filas})} palabras ==")
    print(_linea("TOTAL", total))
    for titulo, clave in (("por persona", "persona"), ("por cámara", "camara"), ("por luz", "luz"), ("por distancia", "distancia"),
                          ("por ángulo", "angulo")):
        print(f"\n-- {titulo}")
        for k, m in agrupar(filas, clave).items():
            print(_linea(k, m))
    por_palabra = agrupar(filas, "etiqueta")
    peores = sorted(por_palabra.items(), key=lambda p: (p[1]["top1"], p[1]["aceptada_bien"]))[:8]
    print("\n-- palabras con peor top-1")
    for k, m in peores:
        print(_linea(k, m))
    conf = confusiones(filas)
    if conf:
        print("\n-- confusiones más repetidas (pedida -> lo que dijo / lo más parecido)")
        for a, b, n in conf:
            print(f"  {a} -> {b}: {n}x")
    return {"total": total, "persona": agrupar(filas, "persona"), "camara": agrupar(filas, "camara"), "luz": agrupar(filas, "luz"),
            "distancia": agrupar(filas, "distancia"), "angulo": agrupar(filas, "angulo"), "palabra": por_palabra,
            "confusiones": confusiones(filas, 20)}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--persona", help="solo esta persona (carpeta de data/banco/)")
    ap.add_argument("--banco", type=Path, default=banco.CARPETA)
    ap.add_argument("--db", type=Path, default=senas_db.RUTA_DB)
    ap.add_argument("--detalle", action="store_true", help="una línea por toma")
    ap.add_argument("--json", type=Path, help="guardar el resumen en este archivo")
    a = ap.parse_args(argv)

    tomas = banco.cargar_tomas(a.banco, a.persona)
    if not tomas:
        print(f"No hay tomas en {a.banco}. Grabar: .venv/Scripts/python -m scripts.grabar_banco \"Tu Nombre\"")
        return 1
    comparador = senas_db.comparador(a.db)
    filas = [evaluar_toma(t, comparador) for t in tomas]
    if a.detalle:
        for f in filas:
            ok = "OK " if f["aceptada"] == f["etiqueta"] else ("MAL" if f["aceptada"] else "-- ")
            top = ", ".join(f"{e}={c:.2f}" for e, c in f["top"][:3]) or "sin seña"
            print(f"{ok} {f['persona']:<12} {f['etiqueta']:<16} {f['luz']}/{f['distancia']}/{f['angulo']} | {top}")
        print()
    resumen = imprimir(filas)
    if a.json:
        a.json.write_text(json.dumps(resumen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"\nResumen guardado en {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
