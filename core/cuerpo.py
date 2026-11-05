"""Dos manos + cuerpo con MediaPipe (Tasks API) para el modo "palabra".

Las letras usan core/camara.Detector (una mano, modo IMAGE). Las palabras
necesitan las DOS manos y una referencia del cuerpo (hombros, codos, muñecas,
cara), así que este detector corre HandLandmarker (num_hands=2) y
PoseLandmarker (lite) en modo VIDEO (siguen la mano entre cuadros: más rápido y
más estable). Lo usan igual la extracción de los videos de CENAREC
(scripts/extraer_cenarec.py) y el reconocimiento en vivo, para que las
referencias y la cámara pasen exactamente por el mismo camino.

El frame tiene que llegar ESPEJADO (vista selfie), como en core/camara.py.

`CuadroCuerpo` guarda lo crudo de MediaPipe (coordenadas normalizadas de la
imagen); los rasgos de la seña se calculan en core/palabras.py.
"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from core.camara import asegurar_modelo

RAIZ = Path(__file__).resolve().parent.parent
RUTA_MODELO_POSE = RAIZ / "data" / "models" / "pose_landmarker_lite.task"
URL_MODELO_POSE = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)

NUM_POSE = 33
# Puntos de pose que usa el motor (índices de MediaPipe Pose).
NARIZ, OREJA_IZQ, OREJA_DER, BOCA_IZQ, BOCA_DER = 0, 7, 8, 9, 10
HOMBRO_IZQ, HOMBRO_DER, CODO_IZQ, CODO_DER, MUNECA_IZQ, MUNECA_DER = 11, 12, 13, 14, 15, 16
LADOS = {"Left": 0, "Right": 1}


@dataclass
class CuadroCuerpo:
    """Lo que dio MediaPipe en un frame (coordenadas normalizadas x/ancho, y/alto, z)."""
    t: float                                   # segundos
    frame: tuple                               # (ancho, alto) en píxeles
    manos: list = field(default_factory=list)  # [(puntos (21, 3), lado "Left"/"Right", score)]
    pose: Optional[np.ndarray] = None          # (33, 4): x, y, z, visibilidad; None sin persona


def asegurar_modelo_pose(ruta: Path = RUTA_MODELO_POSE) -> Path:
    """Descarga pose_landmarker_lite.task la primera vez (solo el modelo oficial de MediaPipe)."""
    if ruta.exists() and ruta.stat().st_size > 0:
        return ruta
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".part")
    urllib.request.urlretrieve(URL_MODELO_POSE, tmp)
    tmp.replace(ruta)
    return ruta


class DetectorCuerpo:
    """HandLandmarker (2 manos) + PoseLandmarker, modo VIDEO. Crear una vez y reusar."""

    def __init__(self, confianza: float = 0.5):
        from mediapipe.tasks.python import BaseOptions, vision
        self._manos = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=Path(asegurar_modelo()).read_bytes()),
            running_mode=vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=confianza, min_hand_presence_confidence=confianza,
            min_tracking_confidence=confianza))
        self._pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=Path(asegurar_modelo_pose()).read_bytes()),
            running_mode=vision.RunningMode.VIDEO, num_poses=1))
        self._ultimo_ms = -1

    def procesar(self, frame_bgr, t: float) -> CuadroCuerpo:
        """frame_bgr espejado; t en segundos, creciente (reloj monótono o tiempo del video)."""
        import cv2
        import mediapipe as mp
        alto, ancho = frame_bgr.shape[:2]
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        ms = max(int(round(t * 1000)), self._ultimo_ms + 1)   # MediaPipe exige marcas estrictamente crecientes
        self._ultimo_ms = ms
        rm = self._manos.detect_for_video(imagen, ms)
        rp = self._pose.detect_for_video(imagen, ms)
        manos = [(np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float32), h[0].category_name, float(h[0].score))
                 for lm, h in zip(rm.hand_landmarks, rm.handedness)]
        pose = None
        if rp.pose_landmarks:
            pose = np.array([[p.x, p.y, p.z, p.visibility] for p in rp.pose_landmarks[0]], dtype=np.float32)
        return CuadroCuerpo(float(t), (ancho, alto), manos, pose)

    def cerrar(self) -> None:
        self._manos.close()
        self._pose.close()


# ---------------------------------------------------------------- cache en arrays (npz)

def a_arrays(cuadros: list[CuadroCuerpo]) -> dict:
    """Lista de cuadros -> arrays para np.savez_compressed (NaN = no hay)."""
    n = len(cuadros)
    manos = np.full((n, 2, 21, 3), np.nan, dtype=np.float32)
    lado = np.full((n, 2), -1, dtype=np.int8)
    score = np.zeros((n, 2), dtype=np.float32)
    pose = np.full((n, NUM_POSE, 4), np.nan, dtype=np.float32)
    for i, c in enumerate(cuadros):
        for k, (pts, l, s) in enumerate(c.manos[:2]):
            manos[i, k], lado[i, k], score[i, k] = pts, LADOS.get(l, -1), s
        if c.pose is not None:
            pose[i] = c.pose
    t = np.array([c.t for c in cuadros], dtype=np.float64)
    frame = np.array(cuadros[0].frame if cuadros else (0, 0), dtype=np.int32)
    return {"t": t, "frame": frame, "manos": manos, "lado": lado, "score": score, "pose": pose}


def desde_arrays(datos) -> list[CuadroCuerpo]:
    """Inversa de a_arrays (acepta el dict o el np.load del .npz)."""
    datos = {k: np.asarray(datos[k]) for k in ("t", "frame", "manos", "lado", "score", "pose")}   # npz: leer una vez
    nombres = {v: k for k, v in LADOS.items()}
    frame = tuple(int(x) for x in datos["frame"])
    salida = []
    for i in range(len(datos["t"])):
        manos = [(datos["manos"][i, k].astype(np.float64), nombres[int(datos["lado"][i, k])], float(datos["score"][i, k]))
                 for k in range(2) if datos["lado"][i, k] >= 0]
        pose = datos["pose"][i]
        salida.append(CuadroCuerpo(float(datos["t"][i]), frame, manos,
                                   None if np.isnan(pose[0, 0]) else pose.astype(np.float64)))
    return salida
