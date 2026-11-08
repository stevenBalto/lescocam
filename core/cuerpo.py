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

Recorte (opcional, `recorte=True`, problema 3): si en un frame falta una mano y
la pose ve esa muñeca, se busca la mano otra vez en un recorte cuadrado
alrededor de la muñeca (corrido hacia donde apunta el antebrazo) con un
HandLandmarker en modo IMAGE. De cerca MediaPipe encuentra manos que en el
cuadro entero se le escapan (juntas, cruzadas o pegadas al cuerpo). Se descarta
si cae encima de una mano ya detectada, y no se busca la mano de un brazo en
REPOSO (muñeca bien abajo de los hombros): el motor la ignora igual y buscarla
en cada cuadro bajaba la cámara de 30 a 19 fps. El formato de salida no cambia.
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

    def __init__(self, confianza: float = 0.5, recorte: bool = False):
        from mediapipe.tasks.python import BaseOptions, vision
        self._manos = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=Path(asegurar_modelo()).read_bytes()),
            running_mode=vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=confianza, min_hand_presence_confidence=confianza,
            min_tracking_confidence=confianza))
        self._pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=Path(asegurar_modelo_pose()).read_bytes()),
            running_mode=vision.RunningMode.VIDEO, num_poses=1))
        self._recorte = None
        if recorte:
            self._recorte = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_buffer=Path(asegurar_modelo()).read_bytes()),
                running_mode=vision.RunningMode.IMAGE, num_hands=2,
                min_hand_detection_confidence=confianza, min_hand_presence_confidence=confianza))
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
        if self._recorte is not None and pose is not None and len(manos) < 2:
            manos = buscar_en_recortes(self._recorte, imagen.numpy_view(), pose, manos)
        return CuadroCuerpo(float(t), (ancho, alto), manos, pose)

    def cerrar(self) -> None:
        self._manos.close()
        self._pose.close()
        if self._recorte is not None:
            self._recorte.close()


# Recorte: lado = RECORTE_LADO anchos de hombro; centro = muñeca + RECORTE_AVANCE * (muñeca - codo).
RECORTE_LADO = 1.1
RECORTE_AVANCE = 0.35
RECORTE_MIN_PX = 64
DUPLICADA = 0.35        # anchos de hombro: una mano con la muñeca así de cerca de otra es la misma
LEJOS_DE_MUNECA = 0.6   # anchos de hombro: la mano del recorte tiene que estar cerca de la muñeca buscada
REPOSO_Y = 0.85         # = core/palabras.Y_REPOSO: muñeca más abajo de los hombros que esto = brazo en reposo


def buscar_en_recortes(detector, rgb: np.ndarray, pose: np.ndarray, manos: list) -> list:
    """Agrega las manos que falten buscándolas en recortes alrededor de las muñecas de la pose.

    detector: HandLandmarker en modo IMAGE. rgb: el frame (alto, ancho, 3). Devuelve la lista
    de manos (como CuadroCuerpo.manos) con las encontradas al final; las de entrada no cambian.
    """
    import mediapipe as mp
    alto, ancho = rgb.shape[:2]
    escala = np.array([ancho, alto], dtype=np.float64)
    w = float(np.linalg.norm((pose[HOMBRO_IZQ, :2] - pose[HOMBRO_DER, :2]) * escala))
    if w < 20:
        return manos
    salida = list(manos)
    centro_y = float((pose[HOMBRO_IZQ, 1] + pose[HOMBRO_DER, 1]) / 2 * alto)
    munecas = lambda: [np.asarray(pts[0, :2], dtype=np.float64) * escala for pts, _, _ in salida]
    for mu, co in ((MUNECA_IZQ, CODO_IZQ), (MUNECA_DER, CODO_DER)):
        if len(salida) >= 2:
            break
        if pose[mu, 3] < 0.5:
            continue
        m = pose[mu, :2].astype(np.float64) * escala
        if not (0 <= m[0] < ancho and 0 <= m[1] < alto):
            continue
        if (m[1] - centro_y) / w > REPOSO_Y:
            continue   # brazo en reposo: no hace falta su mano
        if any(np.linalg.norm(m - x) < DUPLICADA * w for x in munecas()):
            continue   # esa muñeca ya tiene su mano
        c = pose[co, :2].astype(np.float64) * escala
        centro = m + RECORTE_AVANCE * (m - c)
        lado = int(min(max(RECORTE_LADO * w, RECORTE_MIN_PX), ancho, alto))
        x0 = int(np.clip(centro[0] - lado / 2, 0, ancho - lado))
        y0 = int(np.clip(centro[1] - lado / 2, 0, alto - lado))
        recorte = np.ascontiguousarray(rgb[y0:y0 + lado, x0:x0 + lado])
        r = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=recorte))
        mejor = None
        for lm, h in zip(r.hand_landmarks, r.handedness):
            pts = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float64)
            pts[:, 0] = (pts[:, 0] * lado + x0) / ancho
            pts[:, 1] = (pts[:, 1] * lado + y0) / alto
            pts[:, 2] = pts[:, 2] * lado / ancho
            wr = pts[0, :2] * escala
            if any(np.linalg.norm(wr - x) < DUPLICADA * w for x in munecas()):
                continue   # es una mano que ya estaba
            d = float(np.linalg.norm(wr - m))
            if d < LEJOS_DE_MUNECA * w and (mejor is None or d < mejor[0]):
                mejor = (d, pts.astype(np.float32), h[0].category_name, float(h[0].score))
        if mejor is not None:
            salida.append(mejor[1:])
    return salida


# ---------------------------------------------------------------- dibujo (ayuda visual en la app)

CARA = tuple(range(11))     # nariz, ojos, orejas y boca (puntos 0 a 10 de la pose)
CONEXIONES_CUERPO = ((HOMBRO_IZQ, HOMBRO_DER), (HOMBRO_IZQ, CODO_IZQ), (CODO_IZQ, MUNECA_IZQ),
                     (HOMBRO_DER, CODO_DER), (CODO_DER, MUNECA_DER), (BOCA_IZQ, BOCA_DER))
VISIBLE_MIN = 0.5


def dibujar_cuerpo(frame_bgr, pose: Optional[np.ndarray]) -> None:
    """Dibuja la cara (nariz, ojos, orejas, boca), hombros, codos y muñecas de la pose.

    Es solo para ver en vivo que la cámara encuentra la cara y los brazos: el motor de
    palabras usa la nariz y los hombros (core/palabras.py). Los puntos poco visibles no se dibujan.
    """
    if pose is None:
        return
    import cv2
    alto, ancho = frame_bgr.shape[:2]

    def punto(i):
        x, y, _, vis = pose[i]
        if not (np.isfinite(x) and np.isfinite(y)) or vis < VISIBLE_MIN:
            return None
        return int(x * ancho), int(y * alto)

    for a, b in CONEXIONES_CUERPO:
        pa, pb = punto(a), punto(b)
        if pa and pb:
            cv2.line(frame_bgr, pa, pb, (90, 200, 90), 2, cv2.LINE_AA)
    for i in CARA + (HOMBRO_IZQ, HOMBRO_DER, CODO_IZQ, CODO_DER, MUNECA_IZQ, MUNECA_DER):
        p = punto(i)
        if p:
            radio = 6 if i == NARIZ else 4
            color = (0, 215, 255) if i in CARA else (90, 200, 90)   # cara amarilla, brazos verdes (BGR)
            cv2.circle(frame_bgr, p, radio, color, -1, cv2.LINE_AA)


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
