"""Motor de palabras v3: giro 180°, reposo relativo, aceptación (margen relativo, duración) y senas.db v3."""

import json
import sqlite3

import numpy as np
import pytest

from core import palabras as P
from core import senas_db
from core.cuerpo import CuadroCuerpo, NARIZ
from scripts import evaluar_banco, evaluar_palabras
from tests.test_palabras import (ANCHO, CENTRO_X, FRAME, HOMBROS_Y, REPOSO, cuerpo, formas,  # noqa: F401
                                 palabra_cuadros, pose_img, reposo, sena)


# ---------------------------------------------------------------- giro de 180°

def _girado(c: CuadroCuerpo) -> CuadroCuerpo:
    """El mismo cuerpo visto con la imagen girada 180°: (x, y) -> (1 - x, 1 - y)."""
    pose = c.pose.copy()
    pose[:, 0], pose[:, 1] = 1 - pose[:, 0], 1 - pose[:, 1]
    manos = []
    for pts, lado, score in c.manos:
        q = np.array(pts)
        q[:, 0], q[:, 1] = 1 - q[:, 0], 1 - q[:, 1]
        manos.append((q, lado, score))
    return CuadroCuerpo(c.t, c.frame, manos, pose)


def test_cabeza_abajo_nariz_arriba_o_abajo():
    pose = pose_img([REPOSO, REPOSO])
    assert not P.cabeza_abajo(pose)               # nariz arriba de los hombros
    pose[NARIZ, 1] = (HOMBROS_Y + 0.6 * ANCHO) / FRAME[1]
    assert P.cabeza_abajo(pose)                   # nariz debajo de los hombros
    pose[NARIZ, 1] = HOMBROS_Y / FRAME[1]
    assert not P.cabeza_abajo(pose)               # justo a la altura: no es estrictamente debajo


def test_cabeza_abajo_sin_nariz_visible():
    pose = pose_img([REPOSO, REPOSO])
    pose[NARIZ, 1] = (HOMBROS_Y + 0.6 * ANCHO) / FRAME[1]
    pose[NARIZ, 3] = P.VISIBILIDAD_MIN - 0.01
    assert not P.cabeza_abajo(pose)


def test_girar_180_no_toca_z_ni_visibilidad_ni_el_original():
    p = np.array([[0.2, 0.3, 0.5, 0.9], [0.75, 0.1, -0.2, 0.4]])
    original = p.copy()
    g = P._girar_180(p)
    assert np.allclose(g[:, 0], [0.8, 0.25]) and np.allclose(g[:, 1], [0.7, 0.9])
    assert np.array_equal(g[:, 2:], p[:, 2:])
    assert np.array_equal(p, original)
    assert np.allclose(P._girar_180(g), p)        # girar dos veces = identidad


def test_cuadro_girado_da_el_mismo_cuadro_palabra(formas):  # noqa: F811
    m = [(250.0, 100.0), (390.0, 120.0)]
    c = cuerpo(0.0, m, [formas["B"], formas["L"]])
    normal = P.cuadro_palabra(c)
    girado = P.cuadro_palabra(_girado(c))
    assert P.cabeza_abajo(_girado(c).pose) and not P.cabeza_abajo(c.pose)
    assert girado.ancho == pytest.approx(normal.ancho)
    assert np.allclose(girado.centro, normal.centro, atol=1e-3)
    assert np.allclose(girado.nariz, normal.nariz, atol=1e-3)
    for b in (0, 1):
        assert np.allclose(girado.muneca[b], normal.muneca[b], atol=1e-3)
        assert np.linalg.norm(girado.forma[b] - normal.forma[b]) < 1e-3   # no es un espejo: la mano no cambia de lado


def test_cuadro_nariz_arriba_no_se_gira():
    c = cuerpo(0.0, [(250.0, 100.0), (390.0, 120.0)], [None, None])
    assert np.allclose(P.cuadro_palabra(c).muneca[1], (390.0, 120.0), atol=1e-3)


def test_giro_sin_nariz_visible_no_cambia():
    c = cuerpo(0.0, [(250.0, 100.0), (390.0, 120.0)], [None, None])
    g = _girado(c)
    g.pose[NARIZ, 3] = 0.1                       # no se ve la cara: no se sabe que esta girado
    cp = P.cuadro_palabra(g)
    assert cp.nariz is None
    assert cp.centro[1] == pytest.approx(FRAME[1] - HOMBROS_Y, abs=1e-3)   # quedó como llegó, sin girar


def test_giro_apagado_no_gira(monkeypatch):
    c = cuerpo(0.0, [(250.0, 100.0), (390.0, 120.0)], [None, None])
    g = _girado(c)
    monkeypatch.setattr(P, "GIRAR_CABEZA_ABAJO", False)
    assert P.cuadro_palabra(g).centro[1] == pytest.approx(FRAME[1] - HOMBROS_Y, abs=1e-3)
    monkeypatch.setattr(P, "GIRAR_CABEZA_ABAJO", True)
    assert P.cuadro_palabra(g).centro[1] == pytest.approx(HOMBROS_Y, abs=1e-3)


# ---------------------------------------------------------------- reposo relativo

def _cuadro_alto(t, y_rel0, y_rel1):
    """CuadroPalabra con las muñecas a y_rel (anchos de hombro bajo los hombros); None = sin muñeca."""
    def m(y):
        return None if y is None else np.array([CENTRO_X, HOMBROS_Y + y * ANCHO])
    return P.CuadroPalabra(t, np.array([CENTRO_X, HOMBROS_Y]), ANCHO, [m(y_rel0), m(y_rel1)], [None, None])


def _copia(c):
    return P.CuadroPalabra(c.t, c.centro.copy(), c.ancho, [None if m is None else m.copy() for m in c.muneca],
                           list(c.forma))


def test_umbral_reposo_casos():
    assert P.umbral_reposo([]) == P.Y_REPOSO
    assert P.umbral_reposo([1.2] * 20) == P.Y_REPOSO                      # reposo normal: 1.05 -> recorta a 0.85
    assert P.umbral_reposo([0.6] * 20) == pytest.approx(P.Y_REPOSO_MIN)   # 0.45 -> sube al mínimo 0.5
    assert P.umbral_reposo([0.8] * 20) == pytest.approx(0.8 - P.DELTA_REPOSO)
    assert P.umbral_reposo([P.ABAJO] * 5) == P.Y_REPOSO
    # Percentil 90 sin interpolar: con 10 valores es el índice 8; un pico aislado no cuenta.
    assert P.umbral_reposo([0.7] * 9 + [-1.0]) == pytest.approx(0.7 - P.DELTA_REPOSO)
    assert P.umbral_reposo([-1.0] * 9 + [1.2]) == P.Y_REPOSO_MIN


def test_segmentador_pone_reposo_en_cada_cuadro():
    seg = P.Segmentador()
    c = _cuadro_alto(0.0, 1.2, 1.2)
    seg.actualizar(c, 0.0)
    assert c.reposo == (P.Y_REPOSO, P.Y_REPOSO)                       # reposo normal = mismo umbral que antes
    c2 = _cuadro_alto(0.1, 0.6, None)                                 # brazo 1 sin muñeca cuenta como ABAJO
    seg.actualizar(c2, 0.1)
    assert c2.reposo[1] == P.Y_REPOSO
    seg2 = P.Segmentador(relativo=False)
    c3 = _cuadro_alto(0.0, 0.6, 0.6)
    seg2.actualizar(c3, 0.0)
    assert c3.reposo is None


def test_ventana_de_reposo_olvida_lo_viejo():
    seg = P.Segmentador()
    for i in range(30):                                  # primero descansa alto (0.6)
        seg.actualizar(_cuadro_alto(i / 30, 0.6, 0.6), i / 30)
    c = _cuadro_alto(1.0, 0.6, 0.6)
    seg.actualizar(c, 1.0)
    assert c.reposo[0] == pytest.approx(P.Y_REPOSO_MIN)
    for i in range(1, 400):                              # luego descansa abajo más de VENTANA_REPOSO segundos
        t = 1.0 + i * 0.05
        seg.actualizar(_cuadro_alto(t, 1.3, 1.3), t)
    c = _cuadro_alto(1.0 + 400 * 0.05, 1.3, 1.3)
    seg.actualizar(c, c.t)
    assert c.reposo == (P.Y_REPOSO, P.Y_REPOSO)


def _flujo_reposo_alto():
    """Persona que descansa las muñecas a 0.6 anchos bajo los hombros (más arriba que Y_REPOSO) y hace una seña."""
    cuadros, fps = [], 30
    n_rep, n_sena = 2 * fps, fps
    for i in range(n_rep):
        cuadros.append(_cuadro_alto(i / fps, 0.6, 0.6))
    for i in range(n_sena):
        t = (n_rep + i) / fps
        cuadros.append(_cuadro_alto(t, 0.6, 0.6 - 1.4 * np.sin(np.pi * i / (n_sena - 1))))
    for i in range(5 * fps):
        cuadros.append(_cuadro_alto((n_rep + n_sena + i) / fps, 0.6, 0.6))
    return cuadros


def test_reposo_alto_antes_nunca_segmentaba_ahora_si():
    cuadros = _flujo_reposo_alto()
    tiempos = [c.t for c in cuadros]
    assert P.Y_REPOSO > 0.6
    assert P.segmentar([_copia(c) for c in cuadros], tiempos, relativo=False) == []   # una seña eterna, se descarta
    nuevo = P.segmentar([_copia(c) for c in cuadros], tiempos)
    assert len(nuevo) == 1
    assert 0.5 < nuevo[0][-1].t - nuevo[0][0].t < 2.0


def test_reposo_normal_segmenta_igual_con_o_sin_relativo(formas):  # noqa: F811
    cuerpos = reposo(0, 1.0) + sena(formas, 1.0) + reposo(2.0, 1.0)
    tiempos = [c.t for c in cuerpos]
    a = P.segmentar(palabra_cuadros(cuerpos), tiempos)
    b = P.segmentar(palabra_cuadros(cuerpos), tiempos, relativo=False)
    assert len(a) == len(b) == 1
    assert [c.t for c in a[0]] == [c.t for c in b[0]]
    assert a[0][0].reposo == (P.Y_REPOSO, P.Y_REPOSO)


def test_segmentador_sin_muneca_no_rompe():
    seg = P.Segmentador()
    for i in range(60):
        c = _cuadro_alto(i / 30, None, None)
        assert seg.actualizar(c, c.t) is None
        assert c.reposo == (P.Y_REPOSO, P.Y_REPOSO)       # fuera de cuadro = abajo del todo
    assert P.en_reposo(c)


def test_brazo_en_reposo_usa_el_umbral_del_cuadro():
    c = _cuadro_alto(0.0, 0.6, 0.6)
    assert not P.brazo_en_reposo(c, 0)                    # sin `reposo`: Y_REPOSO fijo
    c.reposo = (0.5, 0.5)
    assert P.brazo_en_reposo(c, 0)


# ---------------------------------------------------------------- aceptación

def _desc(valor=0.0, columna=0):
    d = np.zeros((P.MUESTRAS, P.COLUMNAS))
    d[:, columna] = valor
    return d


def test_constantes_v3():
    assert P.VERSION_DESCRIPTOR == 3
    assert P.DISTANCIA_MAX == 5.0 and P.UMBRAL == 0.5
    assert P.MARGEN == 1.18 and P.DURACION_RELATIVA_MIN == 0.5


def test_margen_relativo():
    comp = P.ComparadorPalabras(["A", "B"], [_desc(0.0), _desc(3.0)], prefiltro=None)
    d = comp.distancias(_desc(1.35))
    assert d["A"] == pytest.approx(1.35) and d["B"] == pytest.approx(1.65)
    assert comp.clasificar(_desc(1.35))[0] == "A"         # 1.65 / 1.35 = 1.22 >= 1.18
    assert comp.clasificar(_desc(1.41))[0] is None        # 1.59 / 1.41 = 1.13 < 1.18: ambigua
    assert comp.clasificar(_desc(0.0))[0] == "A"          # coincidencia exacta (d1 = 0): pasa
    flojo = P.ComparadorPalabras(["A", "B"], [_desc(0.0), _desc(3.0)], prefiltro=None, margen=1.0)
    assert flojo.clasificar(_desc(1.41))[0] == "A"


def test_umbral_de_distancia_max():
    comp = P.ComparadorPalabras(["A"], [_desc(0.0)], prefiltro=None)
    assert comp.clasificar(_desc(2.4))[0] == "A"          # confianza 0.52
    palabra, conf, _ = comp.clasificar(_desc(2.6))        # confianza 0.48 < UMBRAL
    assert palabra is None and conf == pytest.approx(0.48)
    assert float(P.confianza(P.DISTANCIA_MAX)) == 0.0 and float(P.confianza(10.0)) == 0.0


def test_duracion_de_una_sena():
    cuadros = _flujo_reposo_alto()[:31]
    assert P.duracion(cuadros) == pytest.approx(1.0)
    assert P.duracion([]) == 0.0 and P.duracion(cuadros[:1]) == 0.0
    assert P.duracion([None, cuadros[0], None, cuadros[30]]) == pytest.approx(1.0)


def test_duracion_corta_no_se_acepta():
    comp = P.ComparadorPalabras(["A", "B"], [_desc(0.0), _desc(9.0)], prefiltro=None, duraciones=[1.0, 1.0])
    assert comp.duracion_min == {"A": 1.0, "B": 1.0}
    cand = _desc(0.0)
    assert comp.clasificar(cand, duracion=1.0)[0] == "A"
    assert comp.clasificar(cand, duracion=0.5)[0] == "A"        # justo la mitad: se acepta
    palabra, conf, top = comp.clasificar(cand, duracion=0.49)   # menos de la mitad: no
    assert palabra is None and conf == 1.0 and top[0][0] == "A"
    assert comp.clasificar(cand, duracion=3.0)[0] == "A"        # más larga no se castiga


def test_duracion_none_no_aplica_el_control():
    comp = P.ComparadorPalabras(["A", "B"], [_desc(0.0), _desc(9.0)], prefiltro=None, duraciones=[1.0, 1.0])
    assert comp.clasificar(_desc(0.0))[0] == "A"
    assert comp.clasificar(_desc(0.0), duracion=None)[0] == "A"
    sin = P.ComparadorPalabras(["A", "B"], [_desc(0.0), _desc(9.0)], prefiltro=None)   # sin duraciones de plantillas
    assert sin.duracion_min == {}
    assert sin.clasificar(_desc(0.0), duracion=0.01)[0] == "A"


def test_duracion_usa_la_plantilla_mas_corta_de_la_palabra():
    comp = P.ComparadorPalabras(["A", "A", "B"], [_desc(0.0), _desc(0.0), _desc(9.0)], prefiltro=None,
                                duraciones=[2.0, 0.8, 1.0])
    assert comp.duracion_min["A"] == pytest.approx(0.8)
    assert comp.clasificar(_desc(0.0), duracion=0.39)[0] is None
    assert comp.clasificar(_desc(0.0), duracion=0.41)[0] == "A"


def test_duraciones_invalidas():
    with pytest.raises(ValueError):
        P.ComparadorPalabras(["A", "B"], [_desc(0.0), _desc(1.0)], duraciones=[1.0])
    # Duraciones None o <= 0 se ignoran (esa plantilla no limita).
    comp = P.ComparadorPalabras(["A", "A", "B"], [_desc(0.0)] * 2 + [_desc(9.0)], prefiltro=None,
                                duraciones=[None, 0.0, 1.0])
    assert "A" not in comp.duracion_min
    assert comp.clasificar(_desc(0.0), duracion=0.01)[0] == "A"


# ---------------------------------------------------------------- senas.db v3

def _db(tmp_path, nombre="senas.db"):
    ruta = tmp_path / nombre
    senas_db.escribir(ruta, [
        {"etiqueta": "A", "idw": 1, "manos": 1, "fuente": "prueba",
         "plantillas": [{"repeticion": 1, "fuente": "p", "inicio": 0.0, "fin": 1.5, "crudo": _desc(0.0)},
                        {"repeticion": 2, "fuente": "p", "inicio": 10.0, "fin": 10.8, "crudo": _desc(0.1)}]},
        {"etiqueta": "B", "idw": 2, "manos": 1, "fuente": "prueba",
         "plantillas": [{"repeticion": 1, "fuente": "p", "inicio": None, "fin": None, "crudo": _desc(30.0)}]}],
        "prueba")
    return ruta


def test_db_leer_devuelve_duraciones(tmp_path):
    datos = senas_db.leer(_db(tmp_path))
    assert [e for e, _ in datos["plantillas"]] == ["A", "A", "B"]
    assert datos["duraciones"][0] == pytest.approx(1.5) and datos["duraciones"][1] == pytest.approx(0.8)
    assert datos["duraciones"][2] is None                  # no guardó inicio/fin


def test_db_comparador_pasa_las_duraciones(tmp_path):
    ruta = _db(tmp_path)
    comp = senas_db.comparador(ruta)
    assert comp.duracion_min == {"A": pytest.approx(0.8)}   # B sin duración: sin control
    assert comp.clasificar(_desc(0.0), duracion=0.39)[0] is None
    assert comp.clasificar(_desc(0.0), duracion=0.41)[0] == "A"
    assert senas_db.comparador(ruta, etiquetas={"B"}).duracion_min == {}
    assert senas_db.comparador(ruta, duraciones=[None, None, None]).duracion_min == {}   # el kw gana


def test_db_meta_con_constantes_nuevas(tmp_path):
    meta = senas_db.leer(_db(tmp_path))["meta"]
    assert meta["version_descriptor"] == "3"
    const = json.loads(meta["constantes"])
    for n in ("GIRAR_CABEZA_ABAJO", "VENTANA_REPOSO", "PERCENTIL_REPOSO", "DELTA_REPOSO", "Y_REPOSO_MIN", "ABAJO",
              "DURACION_RELATIVA_MIN", "MARGEN", "DISTANCIA_MAX", "UMBRAL"):
        assert n in const, n
    assert const["DURACION_RELATIVA_MIN"] == 0.5 and const["MARGEN"] == 1.18
    assert const["DISTANCIA_MAX"] == 5.0 and const["UMBRAL"] == 0.5
    assert const["GIRAR_CABEZA_ABAJO"] is True and const["PERCENTIL_REPOSO"] == 90


def test_db_otra_version_es_incompatible(tmp_path):
    ruta = _db(tmp_path)
    for version in ("2", "1", "4"):
        con = sqlite3.connect(ruta)
        con.execute("UPDATE meta SET valor = ? WHERE clave = 'version_descriptor'", (version,))
        con.commit()
        con.close()
        with pytest.raises(senas_db.VersionIncompatible):
            senas_db.leer(ruta)
        with pytest.raises(senas_db.VersionIncompatible):
            senas_db.comparador(ruta)


def test_db_versionada_es_v3():
    assert senas_db.leer()["meta"]["version_descriptor"] == "3"


# ---------------------------------------------------------------- scripts

def test_evaluar_banco_pasa_la_duracion_a_clasificar(formas):  # noqa: F811
    visto = {}

    class Falso:
        categorias = {"X": "palabra"}

        def clasificar(self, cand, duracion=None):
            visto["duracion"] = duracion
            return "X", 0.9, []

        def mejores(self, cand, k):
            return [("X", 0.9)]

    cuerpos = reposo(0, 1.0) + sena(formas, 1.0, duracion=1.0) + reposo(2.0, 1.0)
    r = evaluar_banco.evaluar_cuadros(cuerpos, "X", Falso())
    assert r["hubo_sena"] and r["aceptada"] == "X"
    assert visto["duracion"] is not None and visto["duracion"] > P.DURACION_MIN
    assert visto["duracion"] == pytest.approx(r["duracion_s"], abs=0.01)


def test_evaluar_banco_sena_corta_para_la_plantilla_no_se_acepta(formas):  # noqa: F811
    cuerpos = reposo(0, 1.0) + sena(formas, 1.0, duracion=0.6) + reposo(1.6, 1.0)
    cp = [P.cuadro_palabra(c) for c in cuerpos]
    sn = P.segmentar(cp, [c.t for c in cuerpos])[0]
    d = P.descriptores(sn, "auto")[0]
    comp = P.ComparadorPalabras(["X", "Y"], [d, d + 50.0], duraciones=[P.duracion(sn) * 3, 1.0])
    r = evaluar_banco.evaluar_cuadros(cuerpos, "X", comp)
    assert r["hubo_sena"] and r["aceptada"] is None


def test_evaluar_palabras_extraccion_por_defecto_y_valores():
    assert evaluar_palabras.CON_RECORTE == "recorte"
    assert evaluar_palabras.RECORTE is True
    with pytest.raises(SystemExit):                       # argparse rechaza el valor antes de evaluar nada
        evaluar_palabras.main(["--extraccion", "otra"])
    assert evaluar_palabras.RECORTE is True


# ---------------------------------------------------------------- revisión: margen del giro y empate exacto

def _pose_nariz(dy: float):
    """Pose con los hombros a y = 0.5 y la nariz a 0.5 + dy (todo visible)."""
    pose = np.full((33, 4), 0.5, dtype=np.float64)
    pose[:, 3] = 1.0
    pose[P.HOMBRO_IZQ, :2] = (0.6, 0.5)
    pose[P.HOMBRO_DER, :2] = (0.4, 0.5)
    pose[P.NARIZ, :2] = (0.5, 0.5 + dy)
    return pose


def test_cabeza_abajo_exige_margen():
    assert P.MARGEN_CABEZA_ABAJO > 0
    assert not P.cabeza_abajo(_pose_nariz(-0.2))                              # de pie: nariz arriba
    assert not P.cabeza_abajo(_pose_nariz(0.0001))                            # casi a la altura: no gira
    assert not P.cabeza_abajo(_pose_nariz(P.MARGEN_CABEZA_ABAJO - 0.01))      # agachada: no gira
    assert P.cabeza_abajo(_pose_nariz(P.MARGEN_CABEZA_ABAJO + 0.01))
    assert P.cabeza_abajo(_pose_nariz(0.27))                                  # imagen girada (iPhone del banco)


def test_empate_exacto_no_se_acepta():
    d = np.zeros((4, 3))
    c = P.ComparadorPalabras(["X", "Y"], [d, d.copy()])
    assert c.clasificar([d])[0] is None            # dos palabras idénticas: no se sabe cuál
    c2 = P.ComparadorPalabras(["X", "Y"], [d, d + 1.0])
    assert c2.clasificar([d])[0] == "X"            # d1 = 0 y la otra lejos: se acepta
