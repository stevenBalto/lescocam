"""Qué es referencia oficial en signs.json y cómo cargarla.

Las tomas oficiales vienen de imágenes o videos de referencia (source "imagen:..."
o "video:..."). Las tomas de webcam ("webcam:<persona>") y las sintéticas
("sintetica:...", core/sinteticas.py) suman variedad, pero nunca definen qué es
correcto: el control de calidad compara solo contra las oficiales.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from core.clasificador import CATEGORIA_POR_DEFECTO, RUTA_SENAS, categoria_de, leer_signs, tomas_de
from core.landmarks import VECTOR_SIZE

FUENTES_OFICIALES = ("imagen:", "video:")


def es_oficial(toma: dict) -> bool:
    return str(toma.get("source", "")).startswith(FUENTES_OFICIALES)


def cargar_oficiales(ruta: Path | str = RUTA_SENAS,
                     categoria: Optional[str] = CATEGORIA_POR_DEFECTO) -> tuple[list[str], np.ndarray]:
    """(etiqueta de cada fila, matriz de vectores) solo de las tomas oficiales válidas.

    categoria: solo las señas de esa categoría ("letra" por defecto); None = todas.
    Si no hay ninguna devuelve ([], matriz vacía de forma (0, 63)).
    Lanza VersionIncompatible si el archivo no es de la versión actual.
    """
    datos = leer_signs(ruta)
    etiquetas, filas = [], []
    for etiqueta, entrada in datos.get("signs", {}).items():
        if categoria is not None and categoria_de(entrada) != categoria:
            continue
        for toma in tomas_de(entrada):
            if not es_oficial(toma):
                continue
            vec = np.asarray(toma["vector"], dtype=np.float64).reshape(-1)
            if vec.shape[0] != VECTOR_SIZE or not np.all(np.isfinite(vec)) or not vec.any():
                continue
            etiquetas.append(etiqueta)
            filas.append(vec)
    return etiquetas, (np.vstack(filas) if filas else np.empty((0, VECTOR_SIZE)))
