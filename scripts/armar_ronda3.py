"""Arma las listas de la ronda 3 del banco (problema 1, fase 5): todo el vocabulario, 1 toma por palabra.

Cada una de las 4 personas graba TODAS las palabras del vocabulario completo (CENAREC + Hands-On) menos
las 85 que ya grabó en las rondas 1 y 2. Así cada palabra queda con 4 personas distintas, que es lo que
subió la precisión en el banco (más personas por palabra, no más tomas de la misma persona).

El orden se baraja distinto para cada persona (semilla fija por nombre): el cansancio y las condiciones
de cada tanda no caen siempre sobre las mismas palabras.

Entrada: data/dictionary/senas_completa.db (core/senas_db.RUTA_DB_COMPLETA) y palabras_iniciales.txt.
Salida: data/reference/ronda3/<nombre>.txt (versionado). Las tomas van a data/ronda3/<persona>/.

Uso:
    .venv/Scripts/python -m scripts.armar_ronda3
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np

from core import banco, senas_db

LISTAS = banco.RAIZ / "data" / "reference" / "ronda3"
TOMAS = banco.RAIZ / "data" / "ronda3"
INICIALES = banco.RAIZ / "data" / "reference" / "palabras_iniciales.txt"


def palabras_ronda3(vocabulario: list[str], ya_grabadas: set[str]) -> list[str]:
    """Las palabras del vocabulario que no están en el banco, ordenadas (sin repetir)."""
    return sorted(set(vocabulario) - set(ya_grabadas))


def orden_de(persona: str, palabras: list[str]) -> list[str]:
    """Barajado fijo para esa persona (mismo nombre -> mismo orden en cualquier PC)."""
    semilla = int.from_bytes(hashlib.sha256(persona.encode("utf-8")).digest()[:8], "little")
    rng = np.random.default_rng(semilla)
    return [palabras[i] for i in rng.permutation(len(palabras))]


def escribir(persona: str, palabras: list[str], carpeta: Path = LISTAS) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{persona}.txt"
    cabecera = [
        f"# Ronda 3 del banco ({persona}): {len(palabras)} palabras, 1 toma cada una (problema 1, fase 5).",
        "# Todo el vocabulario (CENAREC + Hands-On) menos las 85 de las rondas 1 y 2. Orden barajado por persona.",
        "# Generado por scripts/armar_ronda3.py: no editar a mano (el número de cada toma es su línea aquí).",
        "",
    ]
    ruta.write_text("\n".join(cabecera + palabras) + "\n", encoding="utf-8")
    return ruta


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", type=Path, default=senas_db.RUTA_DB_COMPLETA)
    p.add_argument("--salida", type=Path, default=LISTAS)
    a = p.parse_args(argv)
    if not a.db.exists():
        print(f"No existe {a.db}. Armarla con:\n  .venv/Scripts/python -m scripts.construir_palabras --todas "
              f"--handson --salida {a.db}")
        return 1
    db = senas_db.leer(a.db)
    vocab = [e for e, d in db["palabras"].items() if d["categoria"] == "palabra"]
    palabras = palabras_ronda3(vocab, set(banco.leer_lista(INICIALES)))
    for persona in banco.PERSONAS:
        ruta = escribir(persona, orden_de(persona, palabras), a.salida)
        print(f"{ruta}: {len(palabras)} palabras")
    return 0


if __name__ == "__main__":
    sys.exit(main())
