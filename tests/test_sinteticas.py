"""Tomas sintéticas (core/sinteticas.py) y categorías de seña (letra / número)."""

import json

import numpy as np
import pytest

from core.clasificador import RUTA_SENAS, Clasificador, cargar_tomas, leer_signs, tomas_de
from core.rasgos import NUM_RASGOS, rasgos
from core.referencia import cargar_oficiales, es_oficial
from core.sinteticas import (FLEXION_MINIMA, MCP, PIP, PREFIJO, VARIANTES, aplicar, es_sintetica, filtrar,
                             generar, regenerar)
from scripts.recorder import ACEPTADA, clasificadores_oficiales, evaluar_toma


@pytest.fixture(scope="module")
def datos():
    return leer_signs(RUTA_SENAS)


@pytest.fixture(scope="module")
def oficiales():
    return cargar_oficiales(RUTA_SENAS, "letra")


def _toma(datos, etiqueta, prefijo):
    return next(t for t in datos["signs"][etiqueta]["takes"] if t["source"].startswith(prefijo))


def _angulo(pts, a, b, c):
    u, v = pts[b] - pts[a], pts[c] - pts[b]
    return np.degrees(np.arccos(np.clip(u @ v / np.linalg.norm(u) / np.linalg.norm(v), -1, 1)))


# ---------------------------------------------------------------- generador

def test_generar_es_determinista(oficiales):
    et, vec = oficiales
    a = generar(et, vec)
    b = generar(et, vec)
    assert a[0] == b[0] and a[2] == b[2]
    assert np.array_equal(a[1], b[1])


def test_las_sinteticas_de_signs_json_estan_al_dia(datos):
    """Si falla: correr .venv/bin/python -m scripts.generar_sinteticas --guardar."""
    nuevo = regenerar(datos)
    assert nuevo == datos


def test_regenerar_no_modifica_la_entrada_y_borra_las_viejas(datos):
    copia = json.loads(json.dumps(datos))
    copia["signs"]["A"]["takes"].append({"vector": [0.5] * 63, "source": PREFIJO + "vieja|imagen:x"})
    antes = json.dumps(copia)
    nuevo = regenerar(copia)
    assert json.dumps(copia) == antes
    assert nuevo == datos


def test_sinteticas_salen_solo_de_oficiales(datos):
    """Una seña con solo tomas de webcam no recibe sintéticas, y ninguna sale de webcam."""
    a = _toma(datos, "A", "imagen:")
    b = _toma(datos, "B", "imagen:")
    c = _toma(datos, "C", "imagen:")
    prueba = {"version": 3, "signs": {
        "A": {"takes": [a]}, "C": {"takes": [c]},
        "B": {"takes": [dict(b, source="webcam:ana")]}}}
    nuevo = regenerar(prueba)
    assert [t for t in nuevo["signs"]["B"]["takes"] if es_sintetica(t)] == []
    for entrada in nuevo["signs"].values():
        for t in entrada["takes"]:
            if es_sintetica(t):
                assert "|imagen:" in t["source"] and "webcam" not in t["source"]


def test_sinteticas_nunca_son_oficiales(datos):
    sinteticas = [t for e in datos["signs"].values() for t in e["takes"] if es_sintetica(t)]
    assert sinteticas, "signs.json debería tener sintéticas"
    assert not any(es_oficial(t) for t in sinteticas)
    for etiqueta, entrada in datos["signs"].items():
        assert all(es_oficial(t) for t in entrada["takes"] if not es_sintetica(t)
                   and not t["source"].startswith("webcam:"))
    et, _ = cargar_oficiales(RUTA_SENAS, None)
    n_oficiales = sum(es_oficial(t) for e in datos["signs"].values() for t in e["takes"])
    assert len(et) == n_oficiales


def test_recorder_no_usa_sinteticas_como_referencia(tmp_path, datos):
    """Una sintética de A con la forma de B no debe volver dudosa a una B bien hecha."""
    a, b, c = (_toma(datos, e, "imagen:") for e in "ABC")
    trampa = dict(b, source=PREFIJO + "flexion=MCP:+10|imagen:x/A#0")
    ruta = tmp_path / "s.json"
    ruta.write_text(json.dumps({"version": 3, "signs": {
        "A": {"takes": [a, trampa]}, "B": {"takes": [b]}, "C": {"takes": [c]}}}))
    oficial = clasificadores_oficiales(ruta)
    assert evaluar_toma(b["vector"], "B", oficial["B"])[0] == ACEPTADA


def test_filtro_descarta_la_que_se_parece_a_otra_sena(oficiales):
    et, vec = oficiales
    va, vb = vec[et.index("A")], vec[et.index("B")]
    ok = filtrar(et, vec, ["A", "A"], np.vstack([va, vb]), umbral=0.45, margen=0.25)
    assert list(ok) == [True, False]


def test_ninguna_sintetica_queda_mas_cerca_de_otra_letra(datos, oficiales):
    et, vec = oficiales
    clf = Clasificador.desde_tomas(et, vec)
    for etiqueta, entrada in datos["signs"].items():
        if entrada.get("categoria", "letra") != "letra":
            continue
        for t in entrada["takes"]:
            if es_sintetica(t):
                top = clf.mejores(t["vector"], 2)
                assert top[0][0] == etiqueta and top[0][1] - top[1][1] >= 0.25 - 1e-6, (etiqueta, t["source"])


def test_variantes_dejan_la_mano_normalizada(oficiales):
    _, vec = oficiales
    for variante in VARIANTES + (("giro", (30.0, 0.0, 0.0)), ("dedos", 1.1), ("palma", 0.9), ("pulgar", 1.1)):
        pts = aplicar(vec[0], variante).reshape(21, 3)
        assert pts[0] == pytest.approx([0, 0, 0])
        assert np.linalg.norm(pts[9]) == pytest.approx(1.0)


def test_flexion_dobla_solo_lo_doblado_y_no_pasa_de_recto(datos):
    pts = np.asarray(_toma(datos, "A", "imagen:")["vector"], float).reshape(21, 3)
    b = np.asarray(_toma(datos, "B", "imagen:")["vector"], float).reshape(21, 3)
    for dedo in ((5, 6), (9, 10), (13, 14), (17, 18)):
        antes = _angulo(pts, 0, *dedo)
        doblada = aplicar(pts.reshape(-1), ("flexion", (MCP,), 10.0)).reshape(21, 3)
        estirada = aplicar(pts.reshape(-1), ("flexion", (MCP,), -90.0)).reshape(21, 3)
        if antes >= FLEXION_MINIMA:
            assert _angulo(doblada, 0, *dedo) == pytest.approx(antes + 10, abs=1e-6)
            assert _angulo(estirada, 0, *dedo) == pytest.approx(0, abs=1e-4)
    # B: dedos rectos; las falanges casi rectas no se tocan
    for j in (6, 10, 14, 18):
        if _angulo(b, j - 1, j, j + 1) < FLEXION_MINIMA:
            nueva = aplicar(b.reshape(-1), ("flexion", (PIP,), 10.0)).reshape(21, 3)
            assert _angulo(nueva, j - 1, j, j + 1) == pytest.approx(_angulo(b, j - 1, j, j + 1), abs=1e-6)


def test_giro_solo_cambia_la_orientacion(oficiales):
    _, vec = oficiales
    r0, r1 = rasgos(vec[0]), rasgos(aplicar(vec[0], ("giro", (20.0, 10.0, 15.0))))
    assert r1[:NUM_RASGOS - 2] == pytest.approx(r0[:NUM_RASGOS - 2], abs=1e-9)
    assert not np.allclose(r1[NUM_RASGOS - 2:], r0[NUM_RASGOS - 2:])


def test_variante_desconocida():
    with pytest.raises(ValueError):
        aplicar([0.1] * 63, ("inventada", 1.0))


# ---------------------------------------------------------------- categorías

def test_por_defecto_el_clasificador_es_de_letras():
    clf = Clasificador()
    assert clf.categoria == "letra"
    assert not any(e.isdigit() for e in clf._etiquetas)
    assert {e for e in Clasificador(categoria="numero")._etiquetas} == {str(n) for n in range(1, 10)}


def test_numeros_no_aparecen_en_modo_letra(datos):
    letras = Clasificador()
    for n in range(1, 10):
        for t in datos["signs"][str(n)]["takes"]:
            assert not any(e.isdigit() for e, _ in letras.mejores(t["vector"], 50))
            assert letras.clasificar(t["vector"])[0] != str(n)


def test_dos_es_dos_en_modo_numero_y_nunca_en_modo_letra(datos):
    dos = _toma(datos, "2", "imagen:")["vector"]
    assert Clasificador(categoria="numero").clasificar(dos)[0] == "2"
    assert Clasificador().clasificar(dos)[0] in (None, "V")


def test_categoria_invalida():
    with pytest.raises(ValueError, match="categoria"):
        Clasificador(categoria="palabra")
    with pytest.raises(ValueError, match="categoria"):
        cargar_tomas(categoria="Letra")


def test_cargar_tomas_y_oficiales_filtran_por_categoria(datos):
    et_l, _ = cargar_tomas()
    et_n, _ = cargar_tomas(categoria="numero")
    assert set(et_l).isdisjoint(et_n)
    assert len(et_l) + len(et_n) == sum(len(tomas_de(e)) for e in datos["signs"].values())
    of_n, _ = cargar_oficiales(RUTA_SENAS, "numero")
    assert sorted(set(of_n)) == sorted(str(n) for n in range(1, 10))


def test_recorder_controla_cada_sena_contra_su_categoria():
    oficial = clasificadores_oficiales(RUTA_SENAS)
    assert oficial["2"] is not oficial["V"]
    assert {e for e, _ in oficial["2"].mejores([0.1] * 63, 50)} <= {str(n) for n in range(1, 10)}


def test_sinteticas_de_numeros_se_filtran_solo_contra_numeros(datos):
    """2 tiene la forma de V: si se filtrara contra letras no quedaría ninguna."""
    assert any(es_sintetica(t) for t in datos["signs"]["2"]["takes"])


def test_importar_imagenes_categoria_y_solo_numeros(tmp_path):
    from scripts.importar_imagenes import categoria_de_etiqueta, leer_imagenes

    for nombre in ("A.png", "CH.png", "2.png", "10.jpg", "nota.txt"):
        (tmp_path / nombre).write_bytes(b"")
    assert [p.name for p in leer_imagenes(tmp_path, False)] == ["A.png", "CH.png"]
    assert [p.name for p in leer_imagenes(tmp_path, True)] == ["10.jpg", "2.png", "A.png", "CH.png"]
    assert [p.name for p in leer_imagenes(tmp_path, False, solo_numeros=True)] == ["10.jpg", "2.png"]
    assert categoria_de_etiqueta("2") == "numero" and categoria_de_etiqueta("CH") == "letra"


def test_generar_sinteticas_en_prueba_no_escribe(tmp_path, datos):
    from scripts.generar_sinteticas import main

    ruta = tmp_path / "s.json"
    viejo = json.loads(json.dumps(datos))
    for e in viejo["signs"].values():
        e["takes"] = [t for t in e["takes"] if not es_sintetica(t)]
    ruta.write_text(json.dumps(viejo))
    assert main(["--signs", str(ruta)]) == 0
    assert json.loads(ruta.read_text()) == viejo
    assert main(["--signs", str(ruta), "--guardar"]) == 0
    assert json.loads(ruta.read_text()) == datos
