"""core/camara.elegir_mano: qué mano lee el modo letras."""
from types import SimpleNamespace

import pytest

pytest.importorskip("mediapipe")

from core.camara import elegir_mano


def _mano(x, lado):
    return ([SimpleNamespace(x=x, y=0.5, z=0.0)] * 21, lado)


def test_cualquiera_es_la_primera():
    manos = [_mano(0.3, "Left"), _mano(0.7, "Right")]
    assert elegir_mano(manos, None) is manos[0]


def test_lee_solo_la_dominante():
    izq, der = _mano(0.3, "Left"), _mano(0.7, "Right")
    assert elegir_mano([izq, der], "Right") is der
    assert elegir_mano([izq, der], "Left") is izq


def test_si_solo_se_ve_la_otra_no_lee_nada():
    assert elegir_mano([_mano(0.3, "Left")], "Right") is None
    assert elegir_mano([], "Right") is None


def test_las_dos_marcadas_igual_usa_el_lado_de_la_imagen():
    a, b = _mano(0.3, "Right"), _mano(0.7, "Right")
    assert elegir_mano([a, b], "Right") is b
    a, b = _mano(0.3, "Left"), _mano(0.7, "Left")
    assert elegir_mano([a, b], "Left") is a
