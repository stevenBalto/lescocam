"""Fase 5: puntos de la mano en CuadroPalabra, entrada del modelo y evaluación del banco (funciones puras)."""
import dataclasses
from types import SimpleNamespace

import numpy as np
import pytest

from core import palabras as P
from scripts import entrada_modelo as EM
from scripts import evaluar_banco_modelo as EB
from tests.test_palabras import FRAME, REPOSO, formas, mano_img, palabra_cuadros, sena  # noqa: F401


# ---------------------------------------------------------------- core/palabras: puntos

def test_puntos_mano_forma_y_espejo(formas):
    d = P.puntos_mano(mano_img(formas["L"], (400, 100), 1), 1, FRAME)
    i = P.puntos_mano(mano_img(formas["L"], (240, 100), 0), 0, FRAME)
    assert d.shape == (63,)
    assert np.allclose(d, i, atol=1e-6)      # el brazo 0 se espeja como "Left"


def test_cuadro_llena_puntos_solo_donde_hay_forma(formas):
    cs = palabra_cuadros(sena(formas, brazos=(1,)))
    c = cs[len(cs) // 2]
    assert c.puntos[1].shape == (63,) and c.puntos[0] is None
    assert c.forma[0] is None and c.forma[1] is not None


def test_descriptor_no_usa_puntos(formas):
    cs = palabra_cuadros(sena(formas, brazos=(0, 1)))
    sin = [dataclasses.replace(c, puntos=None) for c in cs]
    for espejo in (False, True):
        assert np.array_equal(P.descriptor(cs, espejo), P.descriptor(sin, espejo))


# ---------------------------------------------------------------- scripts/entrada_modelo

def test_entrada_una_mano_dominante_primero(formas):
    cs = palabra_cuadros(sena(formas, brazos=(1,)))
    e = EM.entradas(cs, "auto", False)
    assert [x for x, _ in e] == [False] and e[0][1].shape == (P.MUESTRAS, P.COLUMNAS)
    assert e[0][1].dtype == np.float32
    e = EM.entradas(cs, "auto", True)
    assert e[0][1].shape == (P.MUESTRAS, EM.COLUMNAS_CON_PUNTOS) and EM.COLUMNAS_CON_PUNTOS == 209
    pm = EM.descriptor_puntos(cs, False)
    assert pm.shape == (P.MUESTRAS, 126)
    assert np.any(pm[:, :63]) and not np.any(pm[:, 63:])      # no dominante inactiva = ceros
    assert np.allclose(e[0][1][:, P.COLUMNAS:], pm, atol=1e-6)


def test_entrada_espejo_dominante_es_brazo_0(formas):
    cs = palabra_cuadros(sena(formas, brazos=(0,)))
    e = EM.entradas(cs, "auto", True)
    assert [x for x, _ in e] == [True]
    pm = EM.descriptor_puntos(cs, True)
    assert np.any(pm[:, :63]) and not np.any(pm[:, 63:])
    esperado = np.array([c.puntos[0] for c in cs])
    assert np.allclose(pm[0, :63], esperado[0], atol=1e-6) and np.allclose(pm[-1, :63], esperado[-1], atol=1e-6)


def test_entrada_dos_manos_no_dominante_activa(formas):
    cs = palabra_cuadros(sena(formas, brazos=(0, 1)))
    assert [x for x, _ in EM.entradas(cs, "auto", False)] == [False, True]
    assert [x for x, _ in EM.entradas(cs, "derecha", False)] == [False]
    pm = EM.descriptor_puntos(cs, False)
    assert np.any(pm[:, :63]) and np.any(pm[:, 63:])


def test_no_dominante_bajo_fraccion_activa_en_ceros(formas):
    cs = palabra_cuadros(sena(formas, brazos=(1,)))
    # el brazo 0 sale del reposo solo una fraccion pequena de la seña
    n = int(len(cs) * (P.FRACCION_ACTIVA / 2))
    arriba = (REPOSO[0], REPOSO[1] - 120.0)
    for c in cs[:n]:
        c.muneca[0] = np.array(arriba)
        c.puntos[0] = np.ones(63)
    assert P.actividad(cs)[0] < P.FRACCION_ACTIVA
    pm = EM.descriptor_puntos(cs, False)
    assert not np.any(pm[:, 63:])


def test_entrada_none_con_pocos_cuadros_o_duracion_cero(formas):
    cs = palabra_cuadros(sena(formas, brazos=(1,)))
    assert EM.descriptor_puntos(cs[:1], False) is None
    assert EM.descriptor_puntos([None, cs[0], None], False) is None
    assert EM.entrada(cs[:1], False, True) is None
    mismo_t = [cs[0], dataclasses.replace(cs[1], t=cs[0].t)]
    assert EM.descriptor_puntos(mismo_t, False) is None
    assert EM.entrada(mismo_t, False, False) is None and EM.entrada(mismo_t, False, True) is None
    assert EM.entradas(mismo_t, "auto", True) == []


def test_plantillas_cenarec_si_hay_cache():
    try:
        from scripts.extraer_cenarec import CON_RECORTE, LISTA, catalogo, leer_lista, ruta_cache
        cat = catalogo()
        hay = any(e in cat and ruta_cache(cat[e]["idw"], CON_RECORTE).exists() for e in leer_lista(LISTA))
    except Exception:
        hay = False
    if not hay:
        pytest.skip("falta el cache de CENAREC")
    X, et = EM.plantillas_cenarec(True)
    assert X.shape[1:] == (P.MUESTRAS, EM.COLUMNAS_CON_PUNTOS) and len(X) == len(et)


# ---------------------------------------------------------------- scripts/evaluar_banco_modelo

def fake(duracion_min=None):
    et = ["hola", "gracias", "A"]
    cat = {"hola": "palabra", "gracias": "palabra", "A": "letra"}
    return SimpleNamespace(etiquetas=et, categorias=cat, es_palabra=np.array([cat[e] == "palabra" for e in et]),
                           comparador=SimpleNamespace(duracion_min=duracion_min or {}))


def dec(etiqueta="hola", mejor="hola", s1=2.0, ventaja=1.0, grupo=0, corta=False, hubo=True, top=None):
    d = {"etiqueta": etiqueta, "grupo": grupo, "persona": "p", "hubo_sena": hubo}
    if hubo:
        d.update(top=top or [mejor], mejor=mejor, s1=s1, ventaja=ventaja, corta=corta)
    return d


def test_grupo_de():
    assert EB.grupo_de("christian") == 0 and EB.grupo_de("steven") == 0
    assert EB.grupo_de("christian-iphone") == 0
    assert EB.grupo_de("reyman") == 1 and EB.grupo_de("johan-cam2") == 1
    assert EB.grupo_de("desconocido") == -1
    assert EB.grupo_de("christianx") == -1


def test_z_std_cero_sin_nan():
    r = EB.z(np.array([3.0, 3.0, 3.0]))
    assert np.all(np.isfinite(r)) and np.allclose(r, 0)
    r = EB.z(np.array([1.0, 2.0, 3.0]))
    assert r.mean() == pytest.approx(0) and r.std() == pytest.approx(1)


def test_combinar_pesos():
    p = {"modelo": np.array([1.0, 2.0, 4.0]), "dtw": np.array([5.0, 1.0, 0.0])}
    assert np.allclose(EB.combinar(p, 0), EB.z(p["dtw"]))
    assert np.allclose(EB.combinar(p, 1), EB.z(p["modelo"]))
    assert np.allclose(EB.combinar(p, 0.5), 0.5 * EB.z(p["modelo"]) + 0.5 * EB.z(p["dtw"]))


def test_corta():
    pu = fake({"hola": 1.0})
    assert EB._corta(pu, "hola", 0.4 * 1.0) is True
    assert EB._corta(pu, "hola", P.DURACION_RELATIVA_MIN * 1.0) is False
    assert EB._corta(pu, "gracias", 0.01) is False        # sin minimo conocido


def test_aceptada():
    pu = fake()
    assert EB.aceptada(dec(), pu, 1.0, 0.5) == "hola"
    assert EB.aceptada(dec(hubo=False), pu, 1.0, 0.5) is None
    assert EB.aceptada(dec(mejor="A"), pu, 1.0, 0.5) is None          # letra
    assert EB.aceptada(dec(corta=True), pu, 1.0, 0.5) is None
    assert EB.aceptada(dec(s1=0.5), pu, 1.0, 0.5) is None             # bajo umbral
    assert EB.aceptada(dec(ventaja=0.1), pu, 1.0, 0.5) is None        # ventaja chica
    assert EB.aceptada(dec(s1=1.0, ventaja=0.5), pu, 1.0, 0.5) == "hola"   # bordes inclusivos


def test_metricas():
    pu = fake()
    ds = [dec(),                                                          # bien, top1
          dec(etiqueta="hola", mejor="gracias", top=["gracias", "hola"]),  # mal aceptada, top3
          dec(etiqueta="hola", mejor="gracias", top=["gracias"], s1=0.1),  # no aceptada, fallo
          dec(hubo=False)]
    r = EB.metricas(ds, pu, 1.0, 0.5)
    assert r["n"] == 4 and r["top1"] == 0.25 and r["top3"] == 0.5
    assert r["aceptada_bien"] == 0.25 and r["aceptacion_erronea"] == 0.25
    assert EB.metricas(ds, pu)["aceptada_bien"] == 0          # umbral inf por defecto
    assert EB.metricas([], pu) == {"n": 0}


def _fila(dtw, modelo, etiqueta="hola"):
    return {"etiqueta": etiqueta, "grupo": 0, "persona": "p", "duracion": 1.0,
            "puntajes": {"dtw": np.array(dtw, float), "modelo": np.array(modelo, float)}}


def test_decisiones_coinciden():
    pu = fake()
    # etiquetas: hola, gracias, A
    f_si = _fila([5, 1, 0], [4, 1, 0])           # los dos y la suma eligen hola
    f_no = _fila([5, 1, 0], [0, 4, 1])           # dtw hola, modelo gracias
    f_suma = _fila([5, 4, 0], [0, 4, 1], "gracias")   # dtw hola, modelo gracias
    r = EB.decisiones([f_si, f_no, f_suma], pu, 0.5)
    assert r[0]["coinciden"] is True and r[0]["mejor"] == "hola"
    assert r[1]["coinciden"] is False
    assert r[2]["coinciden"] is False
    # con peso 0.5 la suma puede diferir de ambos aunque dtw y modelo coincidan entre si
    f_dif = _fila([3, 1, 2], [3, 1, 2])
    assert EB.decisiones([f_dif], pu, 0.5)[0]["coinciden"] is True
    sin = {"etiqueta": "hola", "grupo": 0, "persona": "p", "duracion": 0.0, "puntajes": None}
    assert EB.decisiones([sin], pu, 0.5)[0]["hubo_sena"] is False


def test_aceptada_coincidir():
    pu = fake()
    no = dec()
    no["coinciden"] = False
    assert EB.aceptada(no, pu, 1.0, 0.5, coincidir=True) is None
    assert EB.aceptada(no, pu, 1.0, 0.5, coincidir=False) == "hola"
    assert EB.aceptada(no, pu, 1.0, 0.5) == "hola"
    si = dec()
    si["coinciden"] = True
    assert EB.aceptada(si, pu, 1.0, 0.5, coincidir=True) == "hola"
    assert EB.aceptada(dec(), pu, 1.0, 0.5, coincidir=True) == "hola"    # clave ausente = True


def test_metricas_y_ajustar_con_coincidir():
    pu = fake()
    mal = dec(mejor="gracias", s1=3.0)
    mal["coinciden"] = False
    bien = dec(s1=2.0)
    bien["coinciden"] = True
    no_coincide_bien = dec(s1=2.0)
    no_coincide_bien["coinciden"] = False
    ds = [mal, bien, no_coincide_bien]
    r = EB.metricas(ds, pu, 1.0, 0.5, coincidir=True)
    assert r["aceptada_bien"] == pytest.approx(1 / 3) and r["aceptacion_erronea"] == 0
    r = EB.metricas(ds, pu, 1.0, 0.5, coincidir=False)
    assert r["aceptada_bien"] == pytest.approx(2 / 3) and r["aceptacion_erronea"] == pytest.approx(1 / 3)
    # ajustar con tope 0: sin coincidir el umbral tiene que subir sobre 3.0 para evitar el error;
    # con coincidir el error ya no cuenta y el umbral baja a 2.0
    assert EB.ajustar(ds, pu, 0.0, coincidir=True)[0] == pytest.approx(2.0)
    assert EB.metricas(ds, pu, *EB.ajustar(ds, pu, 0.0, coincidir=False), False)["aceptacion_erronea"] == 0


def test_ajustar_y_validaciones_sin_tomas():
    pu = fake()
    assert EB.ajustar([], pu, 0.01) == (np.inf, 0.0)
    assert EB._json({"u": np.inf, "l": [1.0, float("nan")], "n": 3}) == {"u": None, "l": [1.0, None], "n": 3}


def _persona(nombre, s1_bien, s1_mal):
    r = _mezcla(0, s1_bien, s1_mal)
    for d in r:
        d["persona"] = nombre
    return r


def test_validacion_por_persona_ajusta_solo_con_las_demas():
    pu = fake()
    # a y b: bien 2.0 / mal 1.0 -> umbral 2.0. c: bien 1.5 / mal 1.0 (si se usara c el umbral bajaria a 1.5)
    ds = _persona("a", 2.0, 1.0) + _persona("b", 2.0, 1.0) + _persona("c", 1.5, 1.0)
    r = EB.validacion_por_persona(ds, pu, 0.0)
    assert r["c"]["umbral"] == pytest.approx(2.0)                 # sale de a+b
    assert r["c"]["validacion"]["aceptada_bien"] == 0              # 2.0 rechaza las de 1.5
    assert r["a"]["umbral"] == pytest.approx(1.5)                  # sale de b+c, no de a
    assert r["a"]["validacion"]["aceptada_bien"] == 0.5
    for p in "abc":
        assert {"umbral", "margen", "validacion"} <= set(r[p])
    v = r["validacion_total"]
    assert v["n"] == len(ds) == 12
    assert v["aceptacion_erronea"] == 0
    assert v["aceptada_bien"] == pytest.approx(4 / 12)


def test_validacion_por_persona_con_coincidir():
    pu = fake()
    ds = _persona("a", 2.0, 1.0) + _persona("b", 2.0, 1.0)
    for d in ds:
        d["coinciden"] = d["mejor"] == "hola"
    r = EB.validacion_por_persona(ds, pu, 0.0, coincidir=True)
    assert r["validacion_total"]["n"] == 8 and r["validacion_total"]["aceptacion_erronea"] == 0
    assert r["a"]["umbral"] <= 2.0


def test_validacion_cruzada_sin_argumento_coincidir_igual():
    pu = fake()
    ds = _mezcla(0, 2.0, 1.0) + _mezcla(1, 1.8, 1.0)
    assert EB.validacion_cruzada(ds, pu, 0.0) == EB.validacion_cruzada(ds, pu, 0.0, coincidir=False)


def _mezcla(grupo, s1_bien, s1_mal):
    return [dec(grupo=grupo, s1=s1_bien), dec(grupo=grupo, s1=s1_bien),
            dec(grupo=grupo, mejor="gracias", s1=s1_mal), dec(grupo=grupo, mejor="gracias", s1=s1_mal)]


def test_ajustar_respeta_tope_erronea():
    pu = fake()
    ds = _mezcla(0, 2.0, 1.0)
    u, m = EB.ajustar(ds, pu, 0.0)
    assert u > 1.0 and EB.metricas(ds, pu, u, m)["aceptacion_erronea"] == 0
    assert EB.metricas(ds, pu, u, m)["aceptada_bien"] == 0.5
    # con tope alto conviene aceptar mas
    u2, m2 = EB.ajustar(ds, pu, 1.0)
    assert u2 <= 1.0
    # sin senas: nada que ajustar
    assert EB.ajustar([dec(hubo=False)], pu, 0.0)[0] == np.inf


def test_validacion_cruzada_usa_umbral_del_otro_grupo():
    pu = fake()
    ds = _mezcla(0, 2.0, 1.0) + _mezcla(1, 1.8, 1.0)
    r = EB.validacion_cruzada(ds, pu, 0.0)
    a, b = r["ajuste_christian+steven"], r["ajuste_reyman+johan"]
    assert a["umbral"] == pytest.approx(2.0) and b["umbral"] == pytest.approx(1.8)
    assert a["validacion"]["aceptada_bien"] == 0          # 2.0 rechaza las de 1.8
    assert b["validacion"]["aceptada_bien"] == 0.5        # 1.8 acepta las de 2.0
    v = r["validacion_total"]
    assert v["n"] == 8 and v["aceptada_bien"] == pytest.approx(2 / 8) and v["aceptacion_erronea"] == 0
