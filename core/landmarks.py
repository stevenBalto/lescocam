"""Normalización de los 21 landmarks de MediaPipe Hands.

MediaPipe da x dividido por el ANCHO de la imagen, y dividido por el ALTO, y z
en la misma escala que x. Así la misma mano queda estirada distinto según la
proporción de la cámara (640x480, 1280x720, una imagen vertical...). Por eso,
antes de normalizar, los puntos se pasan a una escala igual en los tres ejes:

    x_px = x * ancho     y_px = y * alto     z_px = z * ancho

y recién ahí se normaliza. El vector resultante es invariante a:
  - proporción y resolución de la imagen (corrección de arriba)
  - posición en el cuadro  (se resta la muñeca, landmark 0)
  - escala / distancia a la cámara (se divide por la distancia muñeca -> MCP del dedo medio)
  - mano izquierda/derecha (la izquierda se espeja en X para parecerse a la derecha)

VERSION_VECTOR es la versión de este vector en signs.json: 3 = con corrección de
proporción. Los vectores de la versión 2 (sin corrección) no se pueden mezclar
con estos; se pasan con scripts/migrar_v3.py.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

NUM_LANDMARKS = 21
VECTOR_SIZE = NUM_LANDMARKS * 3
VERSION_VECTOR = 3

WRIST = 0
# Se usa la base (MCP) del dedo medio y no la punta: la punta cambia con la
# flexión del dedo y haría que la escala dependa de la seña misma.
MIDDLE_FINGER_MCP = 9

_MIN_SCALE = 1e-6


def normalize_landmarks(landmarks: Sequence, handedness: str = "Right", *, frame) -> np.ndarray:
    """Vector float32 de 63 valores (21 puntos x XYZ) a partir de landmarks de MediaPipe.

    landmarks: 21 elementos con .x/.y/.z (landmarks de MediaPipe) o filas (x, y, z),
        en coordenadas normalizadas de la imagen (x/ancho, y/alto, z en escala de x).
    handedness: "Left" o "Right" tal como lo reporta MediaPipe (la mano real
        de la persona, siempre que el frame se procese espejado tipo selfie).
    frame: (ancho, alto) en píxeles de la imagen que se le pasó a MediaPipe.
        Es obligatorio: sin él la misma mano da vectores distintos en cada cámara.

    Lanza ValueError si la mano es degenerada (escala ~0) o el frame no es válido.
    """
    return normalizar_puntos(corregir_proporcion(landmarks, frame), handedness)


def corregir_proporcion(landmarks: Sequence, frame) -> np.ndarray:
    """(21, 3) en píxeles: x * ancho, y * alto, z * ancho."""
    ancho, alto = _validar_frame(frame)
    pts = _to_array(landmarks)
    pts[:, 0] *= ancho
    pts[:, 1] *= alto
    pts[:, 2] *= ancho
    return pts


def normalizar_puntos(puntos: Sequence, handedness: str = "Right") -> np.ndarray:
    """Normaliza puntos que YA están en la misma escala en x, y, z (píxeles o un vector ya normalizado).

    Muñeca al origen, muñeca -> MCP del dedo medio = 1, la izquierda espejada en x.
    """
    pts = _to_array(puntos)

    pts = pts - pts[WRIST]  # traslación: muñeca en el origen

    scale = float(np.linalg.norm(pts[MIDDLE_FINGER_MCP]))
    if scale < _MIN_SCALE:
        raise ValueError("Mano degenerada: la distancia muñeca->dedo medio es ~0")
    pts = pts / scale  # escala: muñeca->MCP medio = 1

    if handedness.strip().lower() == "left":
        pts[:, 0] = -pts[:, 0]  # espejo: la izquierda se ve como una derecha

    return pts.astype(np.float32).reshape(-1)


def _validar_frame(frame) -> tuple[float, float]:
    try:
        ancho, alto = (float(v) for v in frame)
    except (TypeError, ValueError):
        raise ValueError(f"frame debe ser (ancho, alto) en píxeles, llegó {frame!r}") from None
    if not (np.isfinite(ancho) and np.isfinite(alto) and ancho > 0 and alto > 0):
        raise ValueError(f"frame debe ser (ancho, alto) positivos, llegó {frame!r}")
    return ancho, alto


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
