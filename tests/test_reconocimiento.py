"""Clasificador y aceptador de letras del motor (core/)."""

import json

import numpy as np
import pytest

from core.aceptador import Aceptador
from core.clasificador import RUTA_SENAS, Clasificador, cargar_tomas


def test_cada_sena_de_referencia_se_reconoce_a_si_misma():
    datos = json.loads(RUTA_SENAS.read_text(encoding="utf-8"))
    clasificador = Clasificador()
    for etiqueta, entrada in datos["signs"].items():
        for toma in entrada["takes"]:
            reconocida, confianza = clasificador.clasificar(toma["vector"])
            assert reconocida == etiqueta
            assert confianza == pytest.approx(1.0)


def test_un_vector_ajeno_no_se_clasifica():
    etiquetas, matriz = cargar_tomas()
    ruido = np.random.default_rng(0).normal(size=matriz.shape[1])
    assert Clasificador(umbral=0.99).clasificar(ruido)[0] is None


def test_vector_invalido_devuelve_vacio():
    clasificador = Clasificador()
    assert clasificador.mejores([0.0] * 63) == []
    assert clasificador.mejores([1.0, 2.0]) == []


def test_aceptador_exige_tiempo_seguido():
    aceptador = Aceptador(umbral=0.9, margen=0.02, segundos=0.4, frames_minimos=1)
    top = [("A", 0.97), ("B", 0.5)]
    assert aceptador.actualizar(top, 10.0) is None
    assert aceptador.actualizar(top, 10.2) is None
    assert aceptador.actualizar(top, 10.4) == "A"


@pytest.mark.parametrize("fps", [15, 30, 60])
def test_aceptador_tarda_lo_mismo_con_cualquier_fps(fps):
    aceptador = Aceptador(umbral=0.9, margen=0.02, segundos=0.4, frames_minimos=4)
    top = [("A", 0.97), ("B", 0.5)]
    for n in range(100):
        if aceptador.actualizar(top, n / fps) == "A":
            assert n / fps == pytest.approx(0.4, abs=1.01 / fps)
            return
    pytest.fail("no aceptó nunca")


def test_aceptador_pide_frames_minimos_aunque_pase_el_tiempo():
    aceptador = Aceptador(umbral=0.9, margen=0.02, segundos=0.4, frames_minimos=4)
    top = [("A", 0.97), ("B", 0.5)]
    assert aceptador.actualizar(top, 0.0) is None
    assert aceptador.actualizar(top, 1.0) is None   # la cámara se trabó: 2 frames no alcanzan
    assert aceptador.actualizar(top, 1.1) is None
    assert aceptador.actualizar(top, 1.2) == "A"


def test_aceptador_reinicia_el_tiempo_si_cambia_la_letra():
    aceptador = Aceptador(umbral=0.9, margen=0.02, segundos=0.4, frames_minimos=1)
    a, b = [("A", 0.97), ("B", 0.5)], [("B", 0.97), ("A", 0.5)]
    aceptador.actualizar(a, 0.0)
    aceptador.actualizar(b, 0.25)
    assert aceptador.actualizar(b, 0.5) is None     # 0.25 s de B: todavía no
    assert aceptador.actualizar(b, 0.75) == "B"


def test_aceptador_no_repite_la_misma_letra_enseguida():
    aceptador = Aceptador(umbral=0.9, margen=0.02, segundos=0.0, frames_minimos=1, segundos_repetir=1.5)
    top = [("A", 0.97), ("B", 0.5)]
    assert aceptador.actualizar(top, 0.0) == "A"
    assert aceptador.actualizar(top, 0.5) is None
    assert aceptador.actualizar(top, 2.0) == "A"


def test_aceptador_descarta_si_el_margen_es_chico():
    aceptador = Aceptador(umbral=0.9, margen=0.05, segundos=0.0, frames_minimos=1)
    assert aceptador.actualizar([("A", 0.95), ("B", 0.94)], 0.0) is None
