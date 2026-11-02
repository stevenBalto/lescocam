"""Corrección de proporción de imagen (signs.json version 3) y migración desde la version 2."""

import json
from types import SimpleNamespace

import numpy as np
import pytest

from core.clasificador import (RUTA_SENAS, Clasificador, VersionIncompatible, cargar_tomas,
                               escribir_signs, leer_signs)
from core.landmarks import VERSION_VECTOR, corregir_proporcion, normalizar_puntos, normalize_landmarks
from core.referencia import cargar_oficiales
from scripts.migrar_v3 import main as migrar_main
from scripts.migrar_v3 import migrar_datos, migrar_vector

CAMARAS = [(640, 480), (1280, 720), (612, 720), (137, 269), (480, 640)]


def _mano_en_pixeles(semilla=0):
    """Una mano inventada en píxeles (x, y, z en la misma escala), muñeca en (300, 250)."""
    rng = np.random.default_rng(semilla)
    pts = rng.uniform(-60, 60, size=(21, 3))
    pts[0] = 0
    pts[9] = [5, -90, -10]                  # muñeca -> MCP medio bien definida
    return pts + [300, 250, 0]


def _vista_por(pixeles, camara):
    """Lo que daría MediaPipe con esa cámara: x/ancho, y/alto, z/ancho."""
    ancho, alto = camara
    return pixeles / [ancho, alto, ancho]


@pytest.mark.parametrize("lado", ["Right", "Left"])
def test_la_misma_mano_da_el_mismo_vector_en_cualquier_camara(lado):
    pixeles = _mano_en_pixeles()
    esperado = normalizar_puntos(pixeles, lado)
    for camara in CAMARAS:
        vector = normalize_landmarks(_vista_por(pixeles, camara), lado, frame=camara)
        assert vector == pytest.approx(esperado, abs=1e-5), camara


def test_sin_corregir_la_proporcion_el_vector_cambia_con_la_camara():
    """Lo que pasaba en la version 2: por eso existe la corrección."""
    pixeles = _mano_en_pixeles()
    a = normalizar_puntos(_vista_por(pixeles, (640, 480)), "Right")
    b = normalizar_puntos(_vista_por(pixeles, (1280, 720)), "Right")
    assert np.abs(a - b).max() > 0.05


def test_corregir_proporcion_escala_z_con_el_ancho():
    pts = np.full((21, 3), 0.5)
    corregidos = corregir_proporcion(pts, (640, 480))
    assert corregidos[0] == pytest.approx([320, 240, 320])


def test_frame_es_obligatorio():
    pts = _vista_por(_mano_en_pixeles(), (640, 480))
    with pytest.raises(TypeError):
        normalize_landmarks(pts, "Right")
    for malo in (None, (640,), (0, 480), (640, -1), ("a", "b"), (float("nan"), 480)):
        with pytest.raises(ValueError):
            normalize_landmarks(pts, "Right", frame=malo)


@pytest.mark.parametrize("lado", ["Right", "Left"])
@pytest.mark.parametrize("camara", CAMARAS)
def test_migrar_v2_coincide_con_reprocesar(lado, camara):
    """v3 calculado desde el vector v2 guardado == v3 calculado desde los landmarks originales."""
    landmarks = _vista_por(_mano_en_pixeles(semilla=3), camara)
    v2 = np.round(normalizar_puntos(landmarks, lado), 6)        # como quedó guardado en signs.json v2
    reprocesado = normalize_landmarks(landmarks, lado, frame=camara)
    assert migrar_vector(v2, camara) == pytest.approx(reprocesado, abs=1e-4)


def _v2(tomas):
    return {"version": 2, "signs": {"A": {"takes": tomas}}}


def _toma_v2(source, frame=None, semilla=0):
    camara = frame or (612, 720)
    t = {"vector": [round(float(x), 6) for x in
                    normalizar_puntos(_vista_por(_mano_en_pixeles(semilla), camara), "Right")],
         "samples": 3, "recorded_at": "2026-11-01T00:00:00+00:00", "source": source}
    if frame:
        t["frame"] = list(frame)
    return t


def test_migrar_datos_usa_frame_video_e_imagen():
    datos = _v2([_toma_v2("webcam:ana", (640, 480)), _toma_v2("video:x.mp4"), _toma_v2("imagen:dic/A")])
    tamanos = {"imagen:dic/A": (137, 269)}
    nuevo = migrar_datos(datos, lambda t: tuple(t["frame"]) if "frame" in t
                         else (612, 720) if t["source"].startswith("video:") else tamanos.get(t["source"]))
    assert nuevo["version"] == VERSION_VECTOR
    tomas = nuevo["signs"]["A"]["takes"]
    assert [t["frame"] for t in tomas] == [[640, 480], [612, 720], [137, 269]]
    assert all(t["samples"] == 3 and "recorded_at" in t and "source" in t for t in tomas)
    assert tomas[0]["vector"] == pytest.approx(
        list(normalizar_puntos(_mano_en_pixeles(0), "Right")), abs=1e-4)


def test_migrar_falla_entera_si_falta_un_tamano():
    datos = _v2([_toma_v2("webcam:ana", (640, 480)), _toma_v2("otra:cosa")])
    with pytest.raises(ValueError, match="otra:cosa"):
        migrar_datos(datos, lambda t: tuple(t["frame"]) if "frame" in t else None)


def test_migrar_main_hace_respaldo_y_escribe_v3(tmp_path, capsys):
    ruta = tmp_path / "signs.json"
    original = json.dumps(_v2([_toma_v2("webcam:ana", (640, 480)), _toma_v2("video:x.mp4")]))
    ruta.write_text(original)
    assert migrar_main(["--signs", str(ruta)]) == 0                 # sin --guardar no toca nada
    assert ruta.read_text() == original
    assert migrar_main(["--signs", str(ruta), "--guardar"]) == 0
    assert (tmp_path / "signs.v2.json.bak").read_text() == original
    assert leer_signs(ruta)["version"] == VERSION_VECTOR
    assert not (tmp_path / "signs.json.tmp").exists()
    assert migrar_main(["--signs", str(ruta), "--guardar"]) == 0     # ya es v3: no hace nada
    assert "ya está en version 3" in capsys.readouterr().out


def test_migrar_main_no_escribe_si_falta_un_tamano(tmp_path):
    ruta = tmp_path / "signs.json"
    original = json.dumps(_v2([_toma_v2("otra:cosa")]))
    ruta.write_text(original)
    assert migrar_main(["--signs", str(ruta), "--guardar"]) == 1
    assert ruta.read_text() == original
    assert not list(tmp_path.glob("*.bak"))


def test_la_carga_rechaza_version_2(tmp_path):
    ruta = tmp_path / "signs.json"
    ruta.write_text(json.dumps(_v2([_toma_v2("imagen:dic/A")])))
    for cargar in (Clasificador, cargar_tomas, cargar_oficiales):
        with pytest.raises(VersionIncompatible, match="migrar_v3"):
            cargar(ruta)


def test_no_se_escribe_un_signs_viejo(tmp_path):
    with pytest.raises(VersionIncompatible):
        escribir_signs(tmp_path / "s.json", {"version": 2, "signs": {}})
    assert not (tmp_path / "s.json").exists()


def test_signs_real_es_version_3_y_cada_toma_tiene_frame():
    datos = leer_signs(RUTA_SENAS)
    for etiqueta, entrada in datos["signs"].items():
        for toma in entrada["takes"]:
            ancho, alto = toma["frame"]
            assert ancho > 0 and alto > 0, etiqueta


def test_detector_corrige_con_el_tamano_del_frame(monkeypatch):
    """Detector.procesar toma (ancho, alto) del propio frame: no se le puede pasar uno equivocado."""
    from core import camara

    pixeles = _mano_en_pixeles()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)                # alto x ancho
    vista = _vista_por(pixeles, (640, 480))
    puntos = [SimpleNamespace(x=x, y=y, z=z) for x, y, z in vista]
    resultado = SimpleNamespace(hand_landmarks=[puntos],
                                handedness=[[SimpleNamespace(category_name="Right")]])
    detector = camara.Detector.__new__(camara.Detector)
    detector._detector = SimpleNamespace(detect=lambda imagen: resultado)
    mano = detector.procesar(frame)
    assert mano.frame == (640, 480)
    assert mano.vector == pytest.approx(normalizar_puntos(pixeles, "Right"), abs=1e-5)
