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


def test_aceptador_exige_frames_seguidos():
    aceptador = Aceptador(umbral=0.9, margen=0.02, frames=3)
    top = [("A", 0.97), ("B", 0.5)]
    assert aceptador.actualizar(top, 0.0) is None
    assert aceptador.actualizar(top, 0.1) is None
    assert aceptador.actualizar(top, 0.2) == "A"


def test_aceptador_no_repite_la_misma_letra_enseguida():
    aceptador = Aceptador(umbral=0.9, margen=0.02, frames=1, segundos_repetir=1.5)
    top = [("A", 0.97), ("B", 0.5)]
    assert aceptador.actualizar(top, 0.0) == "A"
    assert aceptador.actualizar(top, 0.5) is None
    assert aceptador.actualizar(top, 2.0) == "A"


def test_aceptador_descarta_si_el_margen_es_chico():
    aceptador = Aceptador(umbral=0.9, margen=0.05, frames=1)
    assert aceptador.actualizar([("A", 0.95), ("B", 0.94)], 0.0) is None
