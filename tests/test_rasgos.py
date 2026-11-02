"""Rasgos de forma de la mano (core/rasgos.py) y su uso en el clasificador."""

import json

import numpy as np
import pytest

from core.aceptador import Aceptador
from core.clasificador import RUTA_SENAS, UMBRAL, Clasificador, cargar_tomas
from core.landmarks import normalizar_puntos
from core.rasgos import NUM_RASGOS, PESO_ORIENTACION, rasgos

FORMA = slice(0, NUM_RASGOS - 2)        # todo menos la orientación gruesa
ORIENTACION = slice(NUM_RASGOS - 2, NUM_RASGOS)


def _rotacion(yaw=0.0, pitch=0.0, roll=0.0):
    y, p, r = np.radians([yaw, pitch, roll])
    ry = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    rp = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    rr = np.array([[np.cos(r), -np.sin(r), 0], [np.sin(r), np.cos(r), 0], [0, 0, 1]])
    return rr @ rp @ ry


def _girar(vector, **angulos):
    pts = np.asarray(vector, dtype=np.float64).reshape(21, 3) @ _rotacion(**angulos).T
    return normalizar_puntos(pts, "Right")


def _tomas():
    datos = json.loads(RUTA_SENAS.read_text(encoding="utf-8"))
    for etiqueta, entrada in datos["signs"].items():
        for toma in entrada["takes"]:
            yield etiqueta, toma


def test_rasgos_tienen_el_largo_documentado():
    _, vectores = cargar_tomas()
    r = rasgos(vectores[0])
    assert r.shape == (NUM_RASGOS,)
    assert np.all(np.isfinite(r))


@pytest.mark.parametrize("angulos", [{"yaw": 40}, {"pitch": -35}, {"roll": 90}, {"yaw": 25, "pitch": 20, "roll": -60}])
def test_la_forma_no_depende_del_giro(angulos):
    _, vectores = cargar_tomas()
    for vec in vectores[::7]:
        assert rasgos(_girar(vec, **angulos))[FORMA] == pytest.approx(rasgos(vec)[FORMA], abs=1e-4)


def test_la_orientacion_distingue_mano_hacia_abajo():
    _, vectores = cargar_tomas()
    arriba = rasgos(vectores[0])[ORIENTACION]
    abajo = rasgos(_girar(vectores[0], roll=180))[ORIENTACION]
    assert np.linalg.norm(arriba - abajo) == pytest.approx(2 * np.linalg.norm(arriba), rel=1e-3)
    assert np.linalg.norm(arriba) <= PESO_ORIENTACION + 1e-9


@pytest.mark.parametrize("vector", [
    [0.0] * 63,
    [1.0, 2.0],
    [float("nan")] * 63,
    list(np.repeat(np.linspace(0, 1, 21)[:, None], 3, axis=1).reshape(-1)),  # todos los puntos en una recta
])
def test_rasgos_de_mano_degenerada_es_none(vector):
    assert rasgos(vector) is None


def test_cada_toma_se_reconoce_de_costado():
    """Mano girada 30° a cada lado (yaw): sigue siendo la misma letra."""
    clasificador = Clasificador()
    for etiqueta, toma in _tomas():
        for yaw in (-30, 30):
            reconocida, _ = clasificador.clasificar(_girar(toma["vector"], yaw=yaw))
            assert reconocida == etiqueta, (etiqueta, yaw)


def _cruzada(ref, consulta):
    datos = json.loads(RUTA_SENAS.read_text(encoding="utf-8"))
    etiquetas, vectores, consultas = [], [], []
    for etiqueta, entrada in datos["signs"].items():
        for toma in entrada["takes"]:
            fuente = toma.get("source", "").split(":")[0]
            if fuente == ref:
                etiquetas.append(etiqueta)
                vectores.append(toma["vector"])
            elif fuente == consulta:
                consultas.append((etiqueta, toma["vector"]))
    return Clasificador.desde_tomas(etiquetas, vectores), consultas


@pytest.mark.parametrize("ref,consulta", [("imagen", "video"), ("video", "imagen")])
def test_validacion_cruzada_por_fuente(ref, consulta):
    """Top-1 con las tomas de la otra persona como referencia (con coseno daba 56% y 68%)."""
    clasificador, consultas = _cruzada(ref, consulta)
    aciertos = sum(clasificador.mejores(v, 1)[0][0] == e for e, v in consultas)
    assert aciertos / len(consultas) >= 0.8


@pytest.mark.parametrize("ref,consulta", [("imagen", "video"), ("video", "imagen")])
def test_validacion_cruzada_no_inventa(ref, consulta):
    """Con el umbral y el margen del aceptador, ninguna toma de la otra persona pasa como otra letra."""
    clasificador, consultas = _cruzada(ref, consulta)
    aceptador = Aceptador()
    for etiqueta, vector in consultas:
        top = clasificador.mejores(vector, 2)
        if aceptador._valida(top) is not None:
            assert top[0][0] == etiqueta


def test_aceptador_usa_el_umbral_del_clasificador():
    assert Aceptador().umbral == UMBRAL == Clasificador().umbral


def test_desde_tomas_valida_umbral():
    _, vectores = cargar_tomas()
    with pytest.raises(ValueError):
        Clasificador.desde_tomas(["A"], vectores[:1], umbral=0.0)
