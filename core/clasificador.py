"""Clasificador local por similitud de coseno contra las señas de referencia."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
RUTA_SENAS = RAIZ / "data" / "reference" / "signs.json"
UMBRAL = 0.92


def tomas_de(entrada: dict) -> list[dict]:
    """Tomas de una etiqueta. Formato viejo ({"vector": ...}) = una sola toma."""
    if "takes" in entrada:
        return list(entrada["takes"])
    if "vector" in entrada:
        return [entrada]
    return []


def cargar_tomas(ruta: Path | str = RUTA_SENAS) -> Tuple[list[str], np.ndarray]:
    """Carga signs.json -> (etiqueta de cada fila, matriz con una fila unitaria por toma)."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Grabá señas primero con scripts/recorder.py")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    etiquetas, filas = [], []
    for etiqueta, entrada in datos.get("signs", {}).items():
        for toma in tomas_de(entrada):
            vec = np.asarray(toma["vector"], dtype=np.float64)
            norma = np.linalg.norm(vec)
            if vec.ndim != 1 or not np.isfinite(norma) or norma == 0:
                continue
            etiquetas.append(etiqueta)
            filas.append(vec / norma)
    if not filas:
        raise ValueError(f"{ruta} no contiene señas válidas")
    return etiquetas, np.vstack(filas)


def mejor_por_etiqueta(etiquetas: list[str], sims: np.ndarray) -> list[Tuple[str, float]]:
    """Mejor similitud de cada etiqueta (su toma más parecida), de mayor a menor."""
    mejor: dict[str, float] = {}
    for etiqueta, s in zip(etiquetas, sims):
        if etiqueta not in mejor or s > mejor[etiqueta]:
            mejor[etiqueta] = float(s)
    return sorted(mejor.items(), key=lambda p: p[1], reverse=True)


class Clasificador:
    def __init__(self, ruta: Path | str = RUTA_SENAS, umbral: float = UMBRAL):
        if not 0.0 < umbral <= 1.0:
            raise ValueError("umbral debe estar en (0, 1]")
        self.umbral = umbral
        self._etiquetas, self._matriz = cargar_tomas(ruta)

    def mejores(self, vector, k: int = 2) -> list[Tuple[str, float]]:
        """Las k etiquetas más parecidas [(etiqueta, similitud), ...]. No aplica umbral.

        Lista vacía si el vector es inválido.
        """
        vec = np.asarray(vector, dtype=np.float64).reshape(-1)
        if vec.shape[0] != self._matriz.shape[1]:
            return []
        norma = np.linalg.norm(vec)
        if not np.isfinite(norma) or norma == 0:
            return []
        return mejor_por_etiqueta(self._etiquetas, self._matriz @ (vec / norma))[:k]

    def clasificar(self, vector) -> Tuple[Optional[str], float]:
        """(etiqueta, confianza). La etiqueta es None si no alcanza el umbral: nunca inventa."""
        top = self.mejores(vector, 1)
        if not top:
            return None, 0.0
        etiqueta, confianza = top[0]
        return (etiqueta if confianza >= self.umbral else None), confianza
