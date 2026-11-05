"""Revisa el banco de prueba de una persona y deja constancia en hiloEquipo/banco/<nombre>.md.

Comprueba que estén las 30 palabras de su lista con todas sus tomas, que cada toma diga con qué cámara se
grabó y que no haya tomas de palabras ajenas. Si está completo mide el motor actual con sus tomas
(scripts/evaluar_banco.py) y escribe el registro: fecha, cámara, sistema, tomas, condiciones y resultado.
Cada persona escribe SOLO su archivo, así no hay conflictos al hacer push.

Uso:
    .venv/Scripts/python -m scripts.registrar_banco "Steven Baltodano"
    .venv/Scripts/python -m scripts.registrar_banco --estado        # quién ya terminó (las 4 personas)
"""
from __future__ import annotations

import argparse
import platform
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Optional

from core import banco


def revisar(persona: str, raiz: Path = banco.CARPETA, listas: Path = banco.LISTAS) -> dict:
    """Estado del banco de una persona frente a su lista."""
    lista = banco.leer_lista(banco.lista_de(persona, listas))
    tomas = banco.cargar_tomas(raiz, persona)
    por_palabra = Counter(t.etiqueta for t in tomas)
    faltan = {e: banco.TOMAS_POR_PALABRA - por_palabra[e] for e in lista if por_palabra[e] < banco.TOMAS_POR_PALABRA}
    return {
        "persona": banco.limpiar_persona(persona), "lista": lista, "tomas": tomas, "faltan": faltan,
        "ajenas": sorted(set(por_palabra) - set(lista)),
        "camaras": Counter(t.camara for t in tomas),
        "luz": Counter(t.luz for t in tomas), "distancia": Counter(t.distancia for t in tomas),
        "angulo": Counter(t.angulo for t in tomas),
        "esperadas": len(lista) * banco.TOMAS_POR_PALABRA,
    }


def completo(r: dict) -> bool:
    return not r["faltan"] and not r["ajenas"] and len(r["tomas"]) >= r["esperadas"] and "desconocida" not in r["camaras"]


def problemas(r: dict) -> list[str]:
    out = []
    if r["faltan"]:
        out.append("Faltan tomas: " + ", ".join(f"{e} ({n})" for e, n in r["faltan"].items()))
    if r["ajenas"]:
        out.append("Tomas de palabras que no son de tu lista: " + ", ".join(r["ajenas"]))
    if "desconocida" in r["camaras"]:
        out.append(f"{r['camaras']['desconocida']} tomas sin cámara. Grábalas con --camara-nombre.")
    return out


def _tabla(c: Counter) -> str:
    return ", ".join(f"{k}: {v}" for k, v in sorted(c.items())) or "-"


def registro_md(r: dict, metricas: Optional[dict], hoy: Optional[str] = None) -> str:
    m = metricas or {}
    resultado = ("| Métrica | Valor |\n|---|---|\n"
                 f"| top-1 | {m['top1']:.1%} |\n| top-3 | {m['top3']:.1%} |\n"
                 f"| dice la palabra correcta | {m['aceptada_bien']:.1%} |\n"
                 f"| aceptación errónea | {m['aceptacion_erronea']:.1%} |\n"
                 f"| calla | {m['no_dice_nada']:.1%} |\n| sin seña | {m['sin_sena']:.1%} |\n") if m else "(sin medir)\n"
    return (f"# Banco de prueba — {r['persona']}\n\n"
            f"- **Estado:** {'COMPLETO' if completo(r) else 'INCOMPLETO'}\n"
            f"- **Fecha:** {hoy or date.today().isoformat()}\n"
            f"- **Cámara:** {_tabla(r['camaras'])}\n"
            f"- **Sistema:** {platform.system()} {platform.release()}\n"
            f"- **Tomas:** {len(r['tomas'])} de {r['esperadas']} ({len(r['lista'])} palabras x {banco.TOMAS_POR_PALABRA})\n"
            f"- **Luz:** {_tabla(r['luz'])}\n- **Distancia:** {_tabla(r['distancia'])}\n- **Ángulo:** {_tabla(r['angulo'])}\n\n"
            f"## Palabras\n\n{', '.join(r['lista'])}\n\n"
            f"## Resultado del motor actual con estas tomas\n\n{resultado}\n"
            "Las tomas son solo de prueba: nunca plantillas ni entrenamiento. Datos en `data/banco/"
            f"{r['persona']}/`.\n")


def estado(raiz: Path = banco.CARPETA, listas: Path = banco.LISTAS, registros: Path = banco.REGISTROS) -> list[tuple]:
    """[(nombre de pila, tomas, esperadas, completo, tiene registro)] de las 4 personas."""
    filas = []
    for p in banco.PERSONAS:
        carpetas = sorted(c.name for c in raiz.iterdir() if c.is_dir() and c.name.split("-")[0] == p) if raiz.exists() else []
        if not carpetas:
            filas.append((p, 0, len(banco.leer_lista(banco.lista_de(p, listas))) * banco.TOMAS_POR_PALABRA, False, False))
            continue
        r = revisar(carpetas[0], raiz, listas)
        filas.append((p, len(r["tomas"]), r["esperadas"], completo(r), (registros / f"{carpetas[0]}.md").exists()))
    return filas


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("persona", nargs="?", help='tu nombre, igual que al grabar (p. ej. "Steven Baltodano")')
    ap.add_argument("--estado", action="store_true", help="mostrar quién ya terminó")
    a = ap.parse_args(argv)

    if a.estado:
        for p, n, esperadas, ok, reg in estado():
            print(f"{p:<10} {n:>3}/{esperadas}  {'COMPLETO' if ok else 'incompleto':<10} registro: {'sí' if reg else 'no'}")
        return 0
    if not a.persona:
        ap.error("falta tu nombre (o usa --estado)")
    try:
        r = revisar(a.persona)
    except ValueError as e:
        print(e)
        return 1
    if not completo(r):
        print(f"Todavía no está completo ({len(r['tomas'])}/{r['esperadas']} tomas):")
        for linea in problemas(r):
            print(f"  - {linea}")
        return 1
    from core import senas_db
    from scripts.evaluar_banco import evaluar_toma, metricas
    comparador = senas_db.comparador()
    metr = metricas([evaluar_toma(t, comparador) for t in r["tomas"]])
    banco.REGISTROS.mkdir(parents=True, exist_ok=True)
    ruta = banco.REGISTROS / f"{r['persona']}.md"
    ruta.write_text(registro_md(r, metr), encoding="utf-8")
    print(f"Completo: {len(r['tomas'])} tomas. Registro escrito en {ruta.relative_to(banco.RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
