"""Recorte de core/cuerpo.buscar_en_recortes con un detector falso (sin MediaPipe real)."""
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("mediapipe")

from core.cuerpo import CODO_DER, CODO_IZQ, HOMBRO_DER, HOMBRO_IZQ, MUNECA_DER, MUNECA_IZQ, buscar_en_recortes

ANCHO, ALTO = 640, 360


def _pose():
    """Persona de frente: hombros a 0.4 y 0.6 de x, muñecas a la altura del pecho."""
    pose = np.zeros((33, 4), dtype=np.float32)
    pose[:, 3] = 1.0
    pose[HOMBRO_IZQ, :2] = (0.40, 0.40)
    pose[HOMBRO_DER, :2] = (0.60, 0.40)
    pose[CODO_IZQ, :2] = (0.38, 0.60)
    pose[CODO_DER, :2] = (0.62, 0.60)
    pose[MUNECA_IZQ, :2] = (0.42, 0.55)
    pose[MUNECA_DER, :2] = (0.58, 0.55)
    return pose


class _Falso:
    """Devuelve una mano con la muñeca en (0.5, 0.5) del recorte y guarda los recortes pedidos."""

    def __init__(self, manos=1):
        self.recortes, self.manos = [], manos

    def detect(self, imagen):
        self.recortes.append(imagen.numpy_view().shape)
        lm = [SimpleNamespace(x=0.5, y=0.5, z=-0.1) for _ in range(21)]
        h = [SimpleNamespace(category_name="Left", score=0.9)]
        return SimpleNamespace(hand_landmarks=[lm] * self.manos, handedness=[h] * self.manos)


def _mano_en(x, y):
    pts = np.zeros((21, 3), dtype=np.float32)
    pts[:, :2] = (x, y)
    return (pts, "Right", 0.9)


def test_encuentra_la_mano_que_falta_y_la_ubica_en_el_cuadro():
    rgb = np.zeros((ALTO, ANCHO, 3), dtype=np.uint8)
    det = _Falso()
    salida = buscar_en_recortes(det, rgb, _pose(), [_mano_en(0.58, 0.55)])   # falta la del brazo IZQ
    assert len(salida) == 2 and len(det.recortes) == 1
    nueva = salida[1][0]
    muneca = np.array([0.42, 0.55]) * (ANCHO, ALTO)
    # Centro del recorte: muñeca corrida hacia donde apunta el antebrazo; cerca de la muñeca de la pose.
    assert np.linalg.norm(nueva[0, :2] * (ANCHO, ALTO) - muneca) < 0.6 * 0.2 * ANCHO
    lado = det.recortes[0][0]
    assert det.recortes[0][:2] == (lado, lado)


def test_no_duplica_una_mano_que_ya_estaba():
    rgb = np.zeros((ALTO, ANCHO, 3), dtype=np.uint8)
    pose = _pose()
    pose[MUNECA_IZQ, :2] = (0.57, 0.55)   # manos juntas: las dos muñecas casi en el mismo lugar
    pose[MUNECA_DER, :2] = (0.58, 0.55)
    salida = buscar_en_recortes(_Falso(), rgb, pose, [_mano_en(0.58, 0.55)])
    assert len(salida) == 1


def test_sin_muneca_visible_no_busca():
    rgb = np.zeros((ALTO, ANCHO, 3), dtype=np.uint8)
    pose = _pose()
    pose[MUNECA_IZQ, 3] = 0.1
    det = _Falso()
    salida = buscar_en_recortes(det, rgb, pose, [_mano_en(0.58, 0.55)])
    assert len(salida) == 1 and det.recortes == []


def test_brazo_en_reposo_no_busca():
    rgb = np.zeros((ALTO, ANCHO, 3), dtype=np.uint8)
    pose = _pose()
    pose[CODO_IZQ, :2] = (0.39, 0.75)
    pose[MUNECA_IZQ, :2] = (0.40, 0.90)   # brazo izquierdo colgando: muy abajo de los hombros
    det = _Falso()
    salida = buscar_en_recortes(det, rgb, pose, [_mano_en(0.58, 0.55)])
    assert len(salida) == 1 and det.recortes == []


def test_dibujar_cuerpo_pinta_cara_y_brazos_y_tolera_sin_pose():
    from core.cuerpo import dibujar_cuerpo
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    dibujar_cuerpo(frame, None)
    assert frame.sum() == 0
    pose = _pose()
    dibujar_cuerpo(frame, pose)
    assert frame.sum() > 0


def test_dibujar_cuerpo_salta_puntos_poco_visibles():
    from core.cuerpo import dibujar_cuerpo
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    pose = _pose()
    pose[:, 3] = 0.1
    dibujar_cuerpo(frame, pose)
    assert frame.sum() == 0
