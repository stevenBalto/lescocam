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
