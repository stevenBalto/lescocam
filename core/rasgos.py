"""Rasgos de la forma de la mano a partir del vector de 63 de `landmarks.py`.

El vector guardado en signs.json es la mano tal como la ve la cámara: si la
persona gira la muñeca o pone la mano de lado, cambian casi todos sus valores
aunque la forma (qué dedos están doblados) sea la misma. Estos rasgos describen
la forma sin depender del giro y le suman, con poco peso, hacia dónde apunta la
mano, que sí distingue letras (Q y P apuntan abajo; G y H van horizontales).

Se calculan al cargar signs.json y en cada frame; el formato del archivo no
cambia. Solo usa operaciones simples (restas, normas, productos punto y cruz,
arcocoseno) para poder reimplementarlo igual en Dart.

Rasgos (31 valores, en este orden):
  - 15 ángulos de flexión: en cada dedo, el ángulo entre un hueso y el siguiente
    en sus 3 articulaciones, dividido por pi (0 = recto, 1 = doblado del todo).
  - 10 distancias entre las 5 puntas de los dedos, divididas por el tamaño de
    la palma.
  - 3 coordenadas de la punta del pulgar en el marco de la palma (x PESO_PULGAR):
    separa A/S/M/N/E/T, que solo cambian en dónde queda el pulgar.
  - 1 cruce índice/medio: x de la punta del índice menos x de la punta del medio
    en el marco de la palma (x PESO_CRUCE). Separados (V) ~ +1, juntos (U) ~ +0.2,
    cruzados (R) < 0.
  - 2 orientación gruesa: hacia dónde apunta la palma (muñeca -> nudillos) en el
    plano de la imagen, sin renormalizar (x PESO_ORIENTACION).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from core.landmarks import NUM_LANDMARKS, VECTOR_SIZE

WRIST = 0
INDEX_MCP, PINKY_MCP = 5, 17
INDEX_TIP, MIDDLE_TIP = 8, 12
THUMB_TIP = 4

# Cadena de cada dedo desde la muñeca: pulgar, índice, medio, anular, meñique.
DEDOS = ((0, 1, 2, 3, 4), (0, 5, 6, 7, 8), (0, 9, 10, 11, 12), (0, 13, 14, 15, 16), (0, 17, 18, 19, 20))
PUNTAS = (4, 8, 12, 16, 20)
PARES_PUNTAS = tuple((a, b) for i, a in enumerate(PUNTAS) for b in PUNTAS[i + 1:])

# Pesos elegidos con scripts/evaluar_motor.py (validación cruzada imagen <-> video
# y tomas giradas). Los ángulos y las distancias pesan 1.
PESO_PULGAR = 0.5
PESO_CRUCE = 1.0
PESO_ORIENTACION = 1.0

NUM_RASGOS = 15 + len(PARES_PUNTAS) + 3 + 1 + 2

_MIN = 1e-6


def marco_palma(pts: np.ndarray) -> Optional[np.ndarray]:
    """Base ortonormal de la palma (filas x, y, z) o None si es degenerada.

    y: de la muñeca hacia el medio de los nudillos del índice y el meñique.
    z: normal de la palma (producto cruz muñeca->índice x muñeca->meñique).
    x: completa la base (y x z).
    """
    u = pts[INDEX_MCP] - pts[WRIST]
    v = pts[PINKY_MCP] - pts[WRIST]
    y = u + v
    z = np.cross(u, v)
    ny, nz = np.linalg.norm(y), np.linalg.norm(z)
    if ny < _MIN or nz < _MIN:
        return None
    y, z = y / ny, z / nz
    x = np.cross(y, z)
    return np.stack([x, y, z])


def rasgos(vector) -> Optional[np.ndarray]:
    """Rasgos (NUM_RASGOS,) del vector normalizado de 63, o None si no sirve."""
    v = np.asarray(vector, dtype=np.float64).reshape(-1)
    if v.shape[0] != VECTOR_SIZE or not np.all(np.isfinite(v)):
        return None
    pts = v.reshape(NUM_LANDMARKS, 3)
    pts = pts - pts[WRIST]
    base = marco_palma(pts)
    if base is None:
        return None
    palma = (np.linalg.norm(pts[INDEX_MCP]) + np.linalg.norm(pts[PINKY_MCP])) / 2
    huesos = np.linalg.norm(np.diff(pts[list(DEDOS)], axis=1), axis=2)
    if palma < _MIN or huesos.min() < _MIN:
        return None
    local = pts @ base.T / palma          # puntos en el marco de la palma

    angulos = []
    for dedo in DEDOS:
        for i in range(1, 4):
            a = pts[dedo[i]] - pts[dedo[i - 1]]
            b = pts[dedo[i + 1]] - pts[dedo[i]]
            coseno = float(a @ b) / (np.linalg.norm(a) * np.linalg.norm(b))
            angulos.append(np.arccos(np.clip(coseno, -1.0, 1.0)) / np.pi)

    distancias = [np.linalg.norm(local[a] - local[b]) for a, b in PARES_PUNTAS]
    cruce = local[INDEX_TIP, 0] - local[MIDDLE_TIP, 0]

    return np.concatenate([
        angulos,
        distancias,
        local[THUMB_TIP] * PESO_PULGAR,
        [cruce * PESO_CRUCE],
        base[1, :2] * PESO_ORIENTACION,
    ])
