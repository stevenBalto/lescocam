import json

import numpy as np
import pytest

from core.clasificador import RUTA_SENAS, Clasificador, VersionIncompatible
from core.referencia import cargar_oficiales
from scripts.recorder import (ACEPTADA, DUDOSA, RECHAZADA, evaluar_toma, guardar_toma,
                              promediar_frames)


@pytest.fixture(scope="module")
def oficial():
    etiquetas, vectores = cargar_oficiales(RUTA_SENAS)
    return etiquetas, vectores, Clasificador.desde_tomas(etiquetas, vectores)


def test_toma_oficial_aceptada_y_rechazada_como_otra_letra(oficial):
    et, vec, clf = oficial
    va = vec[et.index("A")]
    assert evaluar_toma(va, "A", clf)[0] == ACEPTADA
    estado, msg, top = evaluar_toma(va, "B", clf)
    assert estado == RECHAZADA and "A" in msg and "B" in msg and len(top) == 3


def test_dudosa_si_no_alcanza_umbral(oficial):
    et, vec, _ = oficial
    clf = Clasificador.desde_tomas(et, vec, umbral=0.99)
    va = vec[et.index("A")] * 1.0
    # con umbral casi imposible, una A levemente alterada sigue siendo A pero no clara
    rng = np.random.default_rng(0)
    for s in (0.01, 0.02, 0.03):
        v = va + rng.normal(0, s, va.shape)
        est = evaluar_toma(v, "A", clf)[0]
        if est == DUDOSA:
            return
    pytest.fail("no se logró un caso dudoso")


def test_cargar_oficiales_ignora_webcam(tmp_path):
    v = [0.1] * 63
    datos = {"version": 3, "signs": {"A": {"takes": [
        {"vector": v, "source": "imagen:x/A"}, {"vector": v, "source": "webcam:ana"},
        {"vector": v, "source": "video:y"}]}}}
    ruta = tmp_path / "s.json"
    ruta.write_text(json.dumps(datos))
    et, m = cargar_oficiales(ruta)
    assert et == ["A", "A"] and m.shape == (2, 63)


def test_guardar_agrega_sin_tocar_las_demas(tmp_path):
    datos = {"version": 3, "signs": {
        "A": {"takes": [{"vector": [0.1] * 63, "samples": 1, "source": "imagen:x/A"}]},
        "B": {"takes": [{"vector": [0.2] * 63, "samples": 1, "source": "imagen:x/B"}]}}}
    ruta = tmp_path / "s.json"
    ruta.write_text(json.dumps(datos))
    guardar_toma(ruta, "A", np.full(63, 0.123456789), 28, "ana", (1280, 720))
    nuevo = json.loads(ruta.read_text())
    assert nuevo["signs"]["B"] == datos["signs"]["B"]
    assert nuevo["signs"]["A"]["takes"][0] == datos["signs"]["A"]["takes"][0]
    t = nuevo["signs"]["A"]["takes"][1]
    assert t["source"] == "webcam:ana" and t["frame"] == [1280, 720] and t["samples"] == 28
    assert t["vector"][0] == 0.123457
    assert not (tmp_path / "s.json.tmp").exists()


def test_promediar_rechaza_pocos_frames_y_movimiento(oficial):
    et, vec, _ = oficial
    a, b = vec[et.index("A")], vec[et.index("B")]
    assert promediar_frames([a] * 10 + [None] * 20, 30)[2] is not None
    assert "quieta" in promediar_frames([a, b] * 15, 30)[2]
    v, n, err = promediar_frames([a] * 30, 30)
    assert err is None and n == 30


def test_guardar_rechaza_signs_version_2(tmp_path):
    ruta = tmp_path / "s.json"
    original = json.dumps({"version": 2, "signs": {"A": {"takes": []}}})
    ruta.write_text(original)
    with pytest.raises(VersionIncompatible, match="migrar_v3"):
        guardar_toma(ruta, "A", np.full(63, 0.1), 30, "ana", (640, 480))
    assert ruta.read_text() == original


# ---------------------------------------------------------------- letras con movimiento

def _flujo_de(gesto, antes=0.7, despues=0.7, fps=30.0):
    from dataclasses import replace
    pre = [replace(gesto[0], t=i / fps, _forma=None) for i in range(int(antes * fps))]
    medio = [replace(c, t=antes + c.t - gesto[0].t, _forma=None) for c in gesto]
    fin = medio[-1].t
    post = [replace(gesto[-1], t=fin + (i + 1) / fps, _forma=None) for i in range(int(despues * fps))]
    cuadros = pre + medio + post
    return cuadros, [c.t for c in cuadros]


@pytest.fixture(scope="module")
def plantillas_mov():
    from core.movimiento import cuadros_de_toma, leer_movimientos
    datos = leer_movimientos()
    return {e: cuadros_de_toma(entrada["takes"][0]) for e, entrada in datos["signs"].items()}


def test_gesto_oficial_aceptado_y_rechazado_como_otra_letra(plantillas_mov):
    from scripts.recorder import evaluar_gesto, movimiento_oficial
    oficial = movimiento_oficial()
    cuadros, t = _flujo_de(plantillas_mov["LL"])
    assert evaluar_gesto(cuadros, t, "LL", oficial)[0] == ACEPTADA
    estado, msg, top, gesto = evaluar_gesto(cuadros, t, "RR", oficial)
    assert estado == RECHAZADA and "LL" in msg and gesto is not None


def test_gesto_sin_movimiento_se_rechaza(plantillas_mov):
    from scripts.recorder import evaluar_gesto, movimiento_oficial
    cuadros, t = _flujo_de(plantillas_mov["LL"][:1], antes=2.0, despues=0.0)
    estado, msg, _, gesto = evaluar_gesto(cuadros, t, "LL", movimiento_oficial())
    assert estado == RECHAZADA and gesto is None and "movimiento" in msg


def test_guardar_gesto_agrega_toma_webcam(tmp_path, plantillas_mov):
    import shutil

    from core.movimiento import RUTA_MOVIMIENTOS, leer_movimientos
    from scripts.recorder import guardar_gesto, movimiento_oficial
    ruta = tmp_path / "movimientos.json"
    shutil.copy(RUTA_MOVIMIENTOS, ruta)
    antes = len(leer_movimientos(ruta)["signs"]["J"]["takes"])
    toma = guardar_gesto(ruta, "J", plantillas_mov["J"], "prueba", (640, 480), 30.0)
    datos = leer_movimientos(ruta)
    assert len(datos["signs"]["J"]["takes"]) == antes + 1
    assert toma["source"] == "webcam:prueba" and toma["frame"] == [640, 480]
    # el control de calidad sigue usando solo las oficiales
    assert len(movimiento_oficial(ruta)._plantillas) == len(movimiento_oficial()._plantillas)
