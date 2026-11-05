"""Cámara web + detección de mano con MediaPipe (Tasks API)."""
from __future__ import annotations

import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

from core.landmarks import normalize_landmarks

RAIZ = Path(__file__).resolve().parent.parent
RUTA_MODELO = RAIZ / "data" / "models" / "hand_landmarker.task"
URL_MODELO = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)

CONEXIONES = [(c.start, c.end) for c in vision.HandLandmarksConnections.HAND_CONNECTIONS]


@dataclass
class Mano:
    puntos: list        # 21 NormalizedLandmark (x, y en [0,1] del frame)
    lado: str           # "Left" | "Right" (la mano real de la persona)
    vector: object      # np.ndarray (63,) normalizado, o None si la mano es degenerada
    frame: tuple        # (ancho, alto) en píxeles del frame procesado


def asegurar_modelo(ruta: Path = RUTA_MODELO) -> Path:
    """Descarga hand_landmarker.task la primera vez."""
    if ruta.exists() and ruta.stat().st_size > 0:
        return ruta
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".part")
    urllib.request.urlretrieve(URL_MODELO, tmp)
    tmp.replace(ruta)
    return ruta


def abrir_camara(indice: int = 0) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(indice, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(indice)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"No se pudo abrir la cámara {indice}")
    return cap


def leer_espejado(cap: cv2.VideoCapture):
    """Lee un frame y lo espeja (vista selfie). Devuelve None si falla."""
    ok, frame = cap.read()
    if not ok:
        return None
    return cv2.flip(frame, 1)


class Detector:
    """Detecta una mano por frame y devuelve puntos + vector normalizado."""

    def __init__(self, confianza_deteccion: float = 0.6, confianza_seguimiento: float = 0.5):
        opciones = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=Path(asegurar_modelo()).read_bytes()),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=confianza_deteccion,
            min_hand_presence_confidence=confianza_deteccion,
            min_tracking_confidence=confianza_seguimiento,
        )
        self._detector = vision.HandLandmarker.create_from_options(opciones)

    def procesar(self, frame_bgr) -> Optional[Mano]:
        """frame_bgr debe estar espejado (vista selfie) para que Left/Right sea correcto.

        El tamaño (ancho, alto) para corregir la proporción se toma del propio frame:
        es exactamente la imagen que ve MediaPipe, así que no se puede pasar uno equivocado.
        """
        alto, ancho = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        resultado = self._detector.detect(imagen)
        if not resultado.hand_landmarks:
            return None
        puntos = resultado.hand_landmarks[0]
        lado = resultado.handedness[0][0].category_name
        try:
            vector = normalize_landmarks(puntos, lado, frame=(ancho, alto))
        except ValueError:
            vector = None
        return Mano(puntos, lado, vector, (ancho, alto))

    def cerrar(self) -> None:
        self._detector.close()


# Colores por dedo (BGR) como en el prototipo: pulgar, índice, medio, anular, meñique.
_COLORES_DEDOS = [(40, 150, 255), (230, 130, 40), (110, 190, 60), (200, 90, 170), (120, 60, 220)]


def dibujar_mano(frame_bgr, mano: Mano) -> None:
    """Dibuja los 21 puntos y sus conexiones sobre el frame."""
    alto, ancho = frame_bgr.shape[:2]
    pts = [(int(p.x * ancho), int(p.y * alto)) for p in mano.puntos]
    for a, b in CONEXIONES:
        cv2.line(frame_bgr, pts[a], pts[b], (215, 215, 215), 2, cv2.LINE_AA)
    for i, p in enumerate(pts):
        color = (255, 255, 255) if i == 0 else _COLORES_DEDOS[(i - 1) // 4]
        cv2.circle(frame_bgr, p, 5, color, -1, cv2.LINE_AA)
