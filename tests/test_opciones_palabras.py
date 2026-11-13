"""Opciones del motor de palabras: qué se ofrece cuando no se está seguro (decidir, ReconocedorPalabras, textos)."""

import os

import numpy as np
import pytest

from core import palabras as P
from core import senas_db
from core.movimiento import dtw
from core.reconocedor_palabras import ReconocedorPalabras
from tests.test_palabras import (ANCHO, CENTRO_X, FRAME, HOMBROS_Y, REPOSO, cuerpo, formas,  # noqa: F401
                                 palabra_cuadros, pose_img, reposo, sena)

FORMA = (P.MUESTRAS, P.COLUMNAS)


def unit(k):
    """Descriptor constante: la distancia DTW entre unit(a) y unit(b) es |a - b|."""
    return np.full(FORMA, k / np.sqrt(P.COLUMNAS))


def comparador(distancias, categorias=None, **kw):
    """Plantillas A, B, C... a esas distancias de unit(0) (la seña candidata)."""
    etiquetas = [chr(ord("A") + i) for i in range(len(distancias))]
    return P.ComparadorPalabras(etiquetas, [unit(d) for d in distancias], categorias=categorias,
                                prefiltro=None, **kw)


CANDIDATO = [unit(0.0)]


def test_distancia_sintetica_es_la_diferencia():
    assert dtw(unit(0.0), unit(1.5), P.BANDA) == pytest.approx(1.5)
    assert P.dtw_lote(unit(0.0), np.stack([unit(1.5)]))[0] == pytest.approx(1.5)


def test_constantes_por_defecto():
    assert P.UMBRAL_OPCIONES == 0.4 and P.OPCIONES == 3
    comp = comparador([1.0, 3.0])
    assert comp.umbral_opciones == P.UMBRAL_OPCIONES and comp.opciones == P.OPCIONES


# ---------------------------------------------------------------- decidir

def test_aceptada_no_da_opciones():
    d = comparador([0.5, 3.0, 3.5, 4.0]).decidir(CANDIDATO)
    assert d.palabra == "A" and d.opciones == []
    assert d.confianza == pytest.approx(0.9)


def test_ambigua_por_margen_da_tres_opciones_en_orden():
    # d2 = 1.1 < 1.18 x 1.0: no se acepta; confianza 0.8 >= 0.4
    d = comparador([1.5, 1.0, 2.0, 1.1]).decidir(CANDIDATO)
    assert d.palabra is None
    assert d.confianza == pytest.approx(0.8)
    assert d.opciones == ["B", "D", "A"]          # orden por distancia: 1.0, 1.1, 1.5; la de 2.0 no entra


def test_opciones_respeta_el_parametro_opciones():
    comp = comparador([1.0, 1.1, 1.5, 2.0], opciones=2)
    assert comp.decidir(CANDIDATO).opciones == ["A", "B"]


def test_confianza_bajo_el_umbral_de_opciones_no_da_nada():
    # d = 3.5 -> confianza 0.3 < 0.4; no pasa ni el umbral de aceptación
    d = comparador([3.5, 3.6, 3.7]).decidir(CANDIDATO)
    assert d.palabra is None and d.opciones == []
    assert d.confianza == pytest.approx(0.3)


def test_confianza_justo_en_el_umbral_de_opciones_si_da():
    # d = 3.0 -> confianza 0.4 (borde, se permite); sin margen suficiente ni umbral de aceptación
    d = comparador([3.0, 3.1, 3.2]).decidir(CANDIDATO)
    assert d.palabra is None and d.opciones == ["A", "B", "C"]


def test_umbral_de_opciones_configurable():
    assert comparador([3.0, 3.1, 3.2], umbral_opciones=0.5).decidir(CANDIDATO).opciones == []


def test_la_mejor_negativa_no_da_opciones():
    comp = comparador([0.5, 1.0, 1.1], categorias={"A": "letra"})
    d = comp.decidir(CANDIDATO)
    assert d.palabra is None and d.opciones == []
    assert d.confianza == pytest.approx(0.9)


def test_negativas_en_el_medio_se_saltan():
    comp = comparador([1.0, 1.05, 1.1, 1.2, 1.3], categorias={"B": "letra", "C": "letra"})
    d = comp.decidir(CANDIDATO)
    assert d.palabra is None
    assert d.opciones == ["A", "D", "E"]


def test_menos_de_tres_palabras_da_las_que_haya():
    comp = comparador([1.0, 1.1, 1.2], categorias={"C": "letra"})
    assert comp.decidir(CANDIDATO).opciones == ["A", "B"]
    solo = comparador([1.0], categorias=None)
    d = solo.decidir(CANDIDATO)
    # una sola plantilla: d2 = inf, se acepta (no hay duda)
    assert d.palabra == "A" and d.opciones == []
    # la segunda más cercana es una letra: el margen se mide contra ella y falla; queda una sola palabra
    una_palabra = comparador([1.0, 1.1], categorias={"B": "letra"}).decidir(CANDIDATO)
    assert una_palabra.palabra is None and una_palabra.opciones == ["A"]


def test_una_sola_opcion_si_solo_hay_una_palabra_ambigua_por_duracion():
    comp = comparador([1.0, 1.1], categorias={"B": "letra"}, duraciones=[1.0, 1.0])
    d = comp.decidir(CANDIDATO, duracion=0.1)
    assert d.palabra is None and d.opciones == ["A"]


def test_clasificar_es_igual_a_los_tres_primeros_campos_de_decidir():
    for dist in ([1.5, 1.0, 2.0, 1.1], [0.5, 3.0, 3.5], [3.5, 3.6]):
        comp = comparador(dist)
        d = comp.decidir(CANDIDATO)
        assert comp.clasificar(CANDIDATO) == (d.palabra, d.confianza, d.top)
        assert tuple(d)[:3] == (d.palabra, d.confianza, d.top)


def test_candidatos_vacios_o_none():
    comp = comparador([1.0, 2.0])
    assert comp.decidir([]) == P.Decision(None, 0.0, [], [])
    assert comp.decidir(None) == P.Decision(None, 0.0, [], [])
    assert comp.clasificar([]) == (None, 0.0, [])


def test_rechazo_por_duracion_corta_aun_da_opciones():
    # d1 = 1.0 con margen de sobra; pero la seña dura menos de 0.5 x 1.0 s de la plantilla
    comp = comparador([1.0, 3.0, 3.5, 4.0], duraciones=[1.0, 1.0, 1.0, 1.0])
    assert comp.decidir(CANDIDATO, duracion=1.0).palabra == "A"
    d = comp.decidir(CANDIDATO, duracion=0.3)
    assert d.palabra is None and d.opciones == ["A", "B", "C"]


def test_decision_es_namedtuple_con_los_campos():
    assert P.Decision._fields == ("palabra", "confianza", "top", "opciones")


def test_top_tiene_cinco_como_maximo_y_confianza_de_la_mejor():
    d = comparador([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]).decidir(CANDIDATO)
    assert len(d.top) == 5 and d.top[0] == ("A", pytest.approx(0.8))


# ---------------------------------------------------------------- ReconocedorPalabras

def _sintetico(formas_):
    etiquetas, desc = [], []
    for nombre, kw in (("ARCO-L", {"forma": "L"}), ("ARCO-B", {"forma": "B"}), ("DOS-Y", {"forma": "Y", "brazos": (0, 1)})):
        etiquetas.append(nombre)
        cuadros = palabra_cuadros(sena(formas_, **kw))
        desc.append(P.descriptor(cuadros, P.espejos_posibles(cuadros, "derecha")[0]))
    return P.ComparadorPalabras(etiquetas, desc)


def _correr(rec, flujo):
    for c in flujo:
        rec.actualizar(c, c.t)


def test_reconocedor_cuenta_senas_y_actualiza_opciones(formas):  # noqa: F811
    comp = _sintetico(formas)
    comp.umbral = 1.01                              # nunca se acepta (confianza <= 1) pero la confianza es alta
    rec = ReconocedorPalabras(comp)
    assert rec.senas == 0 and rec.opciones == []

    _correr(rec, reposo(0, 1.0) + sena(formas, 1.0, forma="L", duracion=0.9) + reposo(1.9, 1.0))
    assert rec.senas == 1
    assert rec.ultima[0] is None
    assert rec.opciones and rec.opciones[0] == "ARCO-L" and len(rec.opciones) <= P.OPCIONES

    _correr(rec, sena(formas, 3.0, forma="B", duracion=0.9) + reposo(3.9, 1.0))
    assert rec.senas == 2
    assert rec.opciones[0] == "ARCO-B"

    # Ahora se acepta: las opciones se vacían y la seña igual cuenta
    comp.umbral = P.UMBRAL
    _correr(rec, sena(formas, 5.0, forma="L", duracion=0.9) + reposo(5.9, 1.0))
    assert rec.senas == 3
    assert rec.ultima[0] == "ARCO-L" and rec.opciones == []


def test_reconocedor_terminar_clasifica_y_cuenta(formas):  # noqa: F811
    comp = _sintetico(formas)
    comp.umbral = 1.01
    rec = ReconocedorPalabras(comp)
    for c in reposo(0, 1.0) + sena(formas, 1.0, forma="L", duracion=0.9):
        rec.actualizar(c, c.t)
    assert rec.senas == 0
    rec.terminar()
    assert rec.senas == 1 and rec.opciones[0] == "ARCO-L"


# ---------------------------------------------------------------- textos_opciones y constantes

def _textos_opciones():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from desktop.motor import textos_opciones
    return textos_opciones


def test_textos_opciones_sin_repetidos_y_en_orden():
    t = _textos_opciones()
    assert t(["INFORMAR", "INFORMAR-2", "POR-FAVOR"]) == ["informar", "por favor"]
    assert t(["POR-FAVOR", "INFORMAR", "POR-FAVOR-2"]) == ["por favor", "informar"]
    assert t(["TIERRA(PLANETA)", "TIERRA", "CASA"]) == ["tierra", "casa"]
    assert t([]) == []


def test_constantes_trae_las_opciones():
    c = senas_db.constantes()
    assert c["UMBRAL_OPCIONES"] == P.UMBRAL_OPCIONES == 0.4
    assert c["OPCIONES"] == P.OPCIONES == 3
