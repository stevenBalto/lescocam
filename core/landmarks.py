"""Normalización de los 21 landmarks de MediaPipe Hands.

El vector resultante es invariante a:
  - posición en el cuadro  (se resta la muñeca, landmark 0)
  - escala / distancia a la cámara (se divide por la distancia muñeca -> MCP del dedo medio)
  - mano izquierda/derecha (la izquierda se espeja en X para parecerse a la derecha)
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

NUM_LANDMARKS = 21
VECTOR_SIZE = NUM_LANDMARKS * 3

WRIST = 0
# Se usa la base (MCP) del dedo medio y no la punta: la punta cambia con la
# flexión del dedo y haría que la escala dependa de la seña misma.
MIDDLE_FINGER_MCP = 9

_MIN_SCALE = 1e-6


def normalize_landmarks(landmarks: Sequence, handedness: str = "Right") -> np.ndarray:
    """Devuelve un vector float32 de 63 valores (21 puntos x XYZ).

    landmarks: 21 elementos con .x/.y/.z (landmarks de MediaPipe) o filas (x, y, z).
    handedness: "Left" o "Right" tal como lo reporta MediaPipe (la mano real
        de la persona, siempre que el frame se procese espejado tipo selfie).

    Lanza ValueError si la mano es degenerada (escala ~0).
    """
    pts = _to_array(landmarks)

    pts = pts - pts[WRIST]  # traslación: muñeca en el origen

    scale = float(np.linalg.norm(pts[MIDDLE_FINGER_MCP]))
    if scale < _MIN_SCALE:
        raise ValueError("Mano degenerada: la distancia muñeca->dedo medio es ~0")
    pts = pts / scale  # escala: muñeca->MCP medio = 1

    if handedness.strip().lower() == "left":
        pts[:, 0] = -pts[:, 0]  # espejo: la izquierda se ve como una derecha

    return pts.astype(np.float32).reshape(-1)


def _to_array(landmarks: Sequence) -> np.ndarray:
    if len(landmarks) != NUM_LANDMARKS:
        raise ValueError(f"Se esperaban {NUM_LANDMARKS} landmarks, llegaron {len(landmarks)}")
    first = landmarks[0]
    if hasattr(first, "x"):
        pts = np.array([[p.x, p.y, p.z] for p in landmarks], dtype=np.float64)
    else:
        pts = np.asarray(landmarks, dtype=np.float64)
    if pts.shape != (NUM_LANDMARKS, 3):
        raise ValueError(f"Forma inválida de landmarks: {pts.shape}")
    return pts.copy()
