"""Entrada del modelo de señas: descriptor v3 crudo (83) y, opcional, los puntos de la mano (2 x 63).

Los puntos (CuadroPalabra.puntos, core/palabras.puntos_mano) son los 21 landmarks normalizados de
cada mano, en la MISMA grilla de tiempo y con la MISMA regla que el descriptor: dominante primero
(con espejo la dominante es el brazo 0; sus puntos ya vienen espejados como "Left"), la no
dominante en 0 si no sale del reposo FRACCION_ACTIVA de la seña, huecos interpolados.

Columnas: 83 (sin puntos) o 83 + 126 = 209 (con puntos).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from core import palabras as P
from scripts.construir_palabras import PESOS_CRUDOS, repeticiones

PUNTOS = 63
COLUMNAS_CON_PUNTOS = P.COLUMNAS + 2 * PUNTOS


def descriptor_puntos(cuadros, espejo: bool = False, muestras: int = P.MUESTRAS) -> Optional[np.ndarray]:
    """(muestras, 126): puntos de la dominante y de la no dominante (0 si no cuenta). None si no alcanza."""
    cuadros = [c for c in cuadros if c is not None]
    if len(cuadros) < 2:
        return None
    t = np.array([c.t for c in cuadros])
    if t[-1] - t[0] <= 0:
        return None
    grilla = np.linspace(t[0], t[-1], muestras)
    dom, nod = (0, 1) if espejo else (1, 0)
    fuera = P.actividad(cuadros)
    bloques = []
    for b in (dom, nod):
        f = P._interpolar(t, [c.puntos[b] if c.puntos else None for c in cuadros], grilla, PUNTOS)
        if f is None or (b == nod and fuera[b] < P.FRACCION_ACTIVA):
            f = np.zeros((muestras, PUNTOS))
        bloques.append(f)
    return np.concatenate(bloques, axis=1)


def entrada(cuadros, espejo: bool, con_puntos: bool) -> Optional[np.ndarray]:
    d = P.descriptor(cuadros, espejo, pesos=PESOS_CRUDOS)
    if d is None:
        return None
    if con_puntos:
        pm = descriptor_puntos(cuadros, espejo)
        if pm is None:
            return None
        d = np.concatenate([d, pm], axis=1)
    return d.astype(np.float32)


def entradas(cuadros, mano: str = "auto", con_puntos: bool = False) -> list[tuple[bool, np.ndarray]]:
    """[(espejo, entrada)] de las variantes a probar (como core/palabras.descriptores)."""
    salida = []
    for e in P.espejos_posibles(cuadros, mano):
        d = entrada(cuadros, e, con_puntos)
        if d is not None:
            salida.append((e, d))
    return salida


def plantillas_cenarec(con_puntos: bool) -> tuple[np.ndarray, np.ndarray]:
    """(X, etiquetas) de las palabras de la lista inicial desde el cache de extracción (como
    scripts/construir_palabras: repeticiones del Segmentador, la persona de CENAREC es diestra)."""
    from scripts.extraer_cenarec import CON_RECORTE, LISTA, catalogo, leer_lista, ruta_cache
    cat = catalogo()
    xs, etiquetas = [], []
    for e in leer_lista(LISTA):
        if e not in cat or not ruta_cache(cat[e]["idw"], CON_RECORTE).exists():
            continue
        reps, _ = repeticiones(ruta_cache(cat[e]["idw"], CON_RECORTE))
        for s in reps:
            d = entrada(s, P.espejos_posibles(s, "derecha")[0], con_puntos)
            if d is not None:
                xs.append(d)
                etiquetas.append(e)
    return np.stack(xs), np.array(etiquetas)
