"""Utilidades de scripts/evaluar_motor.py (sin el material de data/dictionary/)."""

import numpy as np
import pytest

from core.clasificador import cargar_tomas
from core.landmarks import normalize_landmarks
from scripts.evaluar_motor import Coseno, girar, rotacion, vector_con_camara


def test_girar_cero_grados_no_cambia_la_toma():
    _, vectores = cargar_tomas()
    assert girar(vectores[0], rotacion("yaw", 0)) == pytest.approx(vectores[0], abs=1e-5)


def test_girar_deja_la_mano_normalizada():
    _, vectores = cargar_tomas()
    pts = girar(vectores[0], rotacion("pitch", 45)).reshape(21, 3)
    assert pts[0] == pytest.approx([0, 0, 0])
    assert np.linalg.norm(pts[9]) == pytest.approx(1.0)


def test_vector_con_camara_no_depende_de_la_proporcion():
    puntos = np.random.default_rng(1).uniform(0.2, 0.8, size=(21, 3))
    mano = {"puntos": puntos.tolist(), "lado": "Left", "ancho": 612, "alto": 720}
    misma = vector_con_camara(mano, None)
    assert misma == pytest.approx(normalize_landmarks(puntos, "Left", frame=(612, 720)), abs=1e-6)
    # Con la corrección de proporción (version 3) otra cámara da el mismo vector.
    for camara in ((640, 480), (1280, 720)):
        assert vector_con_camara(mano, camara) == pytest.approx(misma, abs=1e-5)


def test_coseno_de_referencia_se_reconoce_a_si_mismo():
    etiquetas, vectores = cargar_tomas()
    top = Coseno(etiquetas, vectores).mejores(vectores[0], 2)
    assert top[0] == (etiquetas[0], pytest.approx(1.0))
