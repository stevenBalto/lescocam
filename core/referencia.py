"""Qué es referencia oficial en signs.json y cómo cargarla.

Las tomas oficiales vienen de imágenes o videos de referencia (source "imagen:..."
o "video:..."). Las tomas de webcam ("webcam:<persona>") suman variedad, pero
nunca definen qué es correcto: el control de calidad compara solo contra las oficiales.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from core.clasificador import RUTA_SENAS, leer_signs, tomas_de
from core.landmarks import VECTOR_SIZE

FUENTES_OFICIALES = ("imagen:", "video:")


def es_oficial(toma: dict) -> bool:
    return str(toma.get("source", "")).startswith(FUENTES_OFICIALES)


def cargar_oficiales(ruta: Path | str = RUTA_SENAS) -> tuple[list[str], np.ndarray]:
    """(etiqueta de cada fila, matriz de vectores) solo de las tomas oficiales válidas.

    Si no hay ninguna devuelve ([], matriz vacía de forma (0, 63)).
    Lanza VersionIncompatible si el archivo no es de la versión actual.
    """
    datos = leer_signs(ruta)
    etiquetas, filas = [], []
    for etiqueta, entrada in datos.get("signs", {}).items():
        for toma in tomas_de(entrada):
            if not es_oficial(toma):
                continue
            vec = np.asarray(toma["vector"], dtype=np.float64).reshape(-1)
            if vec.shape[0] != VECTOR_SIZE or not np.all(np.isfinite(vec)) or not vec.any():
                continue
            etiquetas.append(etiqueta)
            filas.append(vec)
    return etiquetas, (np.vstack(filas) if filas else np.empty((0, VECTOR_SIZE)))
