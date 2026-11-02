"""Clasificador local: compara la forma de la mano con las señas de referencia.

Cada toma de signs.json (vector de 63) se pasa a rasgos de forma (`core/rasgos.py`)
una sola vez al cargar. En cada frame se calculan los rasgos de la mano y la
distancia euclídea a cada toma; la confianza es 1 - distancia / DISTANCIA_MAX
(1 = idéntica, 0 = a DISTANCIA_MAX o más). De cada letra cuenta su toma más cercana.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from core.landmarks import VECTOR_SIZE, VERSION_VECTOR
from core.rasgos import rasgos

RAIZ = Path(__file__).resolve().parent.parent
RUTA_SENAS = RAIZ / "data" / "reference" / "signs.json"

# Escala de la confianza: entre letras distintas la distancia típica es 1.3-3.3;
# la misma letra hecha por otra persona queda en 0.3-1.1.
DISTANCIA_MAX = 2.0
# Confianza mínima = distancia máxima 1.1. Elegido con scripts/evaluar_motor.py.
UMBRAL = 0.45


class VersionIncompatible(ValueError):
    """signs.json tiene vectores de otra versión de la normalización."""


def leer_signs(ruta: Path | str = RUTA_SENAS) -> dict:
    """Lee signs.json y exige la versión actual del vector (VERSION_VECTOR).

    Los vectores de versiones distintas no son comparables entre sí: un archivo
    viejo se rechaza con un error claro en vez de reconocer mal en silencio.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Grabá señas primero con scripts/recorder.py")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    version = datos.get("version") if isinstance(datos, dict) else None
    if version != VERSION_VECTOR:
        raise VersionIncompatible(
            f"{ruta} es version {version} y el motor usa version {VERSION_VECTOR} "
            f"(con corrección de proporción de imagen). Corré: .venv/bin/python -m scripts.migrar_v3")
    if not isinstance(datos.get("signs"), dict):
        raise ValueError(f"{ruta} no tiene la clave 'signs'")
    return datos


def signs_vacio() -> dict:
    return {"version": VERSION_VECTOR, "signs": {}}


def escribir_signs(ruta: Path | str, datos: dict) -> None:
    """Escribe aparte y reemplaza: si se corta a la mitad, el original queda intacto."""
    ruta = Path(ruta)
    if datos.get("version") != VERSION_VECTOR:
        raise VersionIncompatible(f"Solo se escribe signs.json version {VERSION_VECTOR}")
    tmp = ruta.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(ruta)


def tomas_de(entrada: dict) -> list[dict]:
    """Tomas de una etiqueta. Formato viejo ({"vector": ...}) = una sola toma."""
    if "takes" in entrada:
        return list(entrada["takes"])
    if "vector" in entrada:
        return [entrada]
    return []


def cargar_tomas(ruta: Path | str = RUTA_SENAS) -> Tuple[list[str], np.ndarray]:
    """Carga signs.json -> (etiqueta de cada fila, matriz con el vector de 63 de cada toma).

    Se saltan las tomas inválidas (largo distinto de 63, valores no finitos o vector nulo).
    Lanza VersionIncompatible si el archivo no es de la versión actual.
    """
    datos = leer_signs(ruta)
    etiquetas, filas = [], []
    for etiqueta, entrada in datos.get("signs", {}).items():
        for toma in tomas_de(entrada):
            vec = np.asarray(toma["vector"], dtype=np.float64).reshape(-1)
            if vec.shape[0] != VECTOR_SIZE or not np.all(np.isfinite(vec)) or not vec.any():
                continue
            etiquetas.append(etiqueta)
            filas.append(vec)
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


def confianza(distancia):
    """1 - distancia / DISTANCIA_MAX, recortada a [0, 1]."""
    return np.clip(1.0 - np.asarray(distancia) / DISTANCIA_MAX, 0.0, 1.0)


class Clasificador:
    def __init__(self, ruta: Path | str = RUTA_SENAS, umbral: float = UMBRAL):
        if not 0.0 < umbral <= 1.0:
            raise ValueError("umbral debe estar en (0, 1]")
        self.umbral = umbral
        self._preparar(*cargar_tomas(ruta))

    @classmethod
    def desde_tomas(cls, etiquetas: list[str], vectores, umbral: float = UMBRAL) -> "Clasificador":
        """Clasificador con tomas dadas en memoria (para evaluar sin escribir signs.json)."""
        if not 0.0 < umbral <= 1.0:
            raise ValueError("umbral debe estar en (0, 1]")
        nuevo = cls.__new__(cls)
        nuevo.umbral = umbral
        nuevo._preparar(list(etiquetas), np.asarray(vectores, dtype=np.float64))
        return nuevo

    def _preparar(self, etiquetas: list[str], vectores: np.ndarray) -> None:
        """Precalcula los rasgos de cada toma (una vez, fuera del bucle de la cámara)."""
        self._etiquetas, filas = [], []
        for etiqueta, vec in zip(etiquetas, vectores):
            r = rasgos(vec)
            if r is not None:
                self._etiquetas.append(etiqueta)
                filas.append(r)
        if not filas:
            raise ValueError("No hay señas válidas")
        self._rasgos = np.vstack(filas)

    def mejores(self, vector, k: int = 2) -> list[Tuple[str, float]]:
        """Las k etiquetas más parecidas [(etiqueta, confianza), ...]. No aplica umbral.

        Lista vacía si el vector es inválido.
        """
        r = rasgos(vector)
        if r is None:
            return []
        distancias = np.linalg.norm(self._rasgos - r, axis=1)
        return mejor_por_etiqueta(self._etiquetas, confianza(distancias))[:k]

    def clasificar(self, vector) -> Tuple[Optional[str], float]:
        """(etiqueta, confianza). La etiqueta es None si no alcanza el umbral: nunca inventa."""
        top = self.mejores(vector, 1)
        if not top:
            return None, 0.0
        etiqueta, conf = top[0]
        return (etiqueta if conf >= self.umbral else None), conf
