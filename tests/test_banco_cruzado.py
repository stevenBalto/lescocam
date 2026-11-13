"""Pruebas de scripts/evaluar_banco_cruzado.py con datos sintéticos (sin banco ni senas.db reales)."""
import numpy as np
import pytest

from core import palabras as P
from scripts import evaluar_banco_cruzado as E

FORMA = (P.MUESTRAS, P.COLUMNAS)


def unit(k):
    """Descriptor constante: la distancia DTW entre unit(a) y unit(b) es |a - b|."""
    return np.full(FORMA, k / np.sqrt(P.COLUMNAS))


def fila(persona, etiqueta, k, plantilla="igual", duracion=1.0):
    variantes = [] if k is None else [unit(k)]
    if plantilla == "igual":
        plantilla = variantes[0] if variantes else None
    return {"persona": persona, "etiqueta": etiqueta, "archivo": "x.json", "variantes": variantes,
            "duracion": duracion, "plantilla": plantilla}


def db_de(*items):
    """items: (etiqueta, valor k)."""
    return {"plantillas": [(e, unit(k)) for e, k in items], "duraciones": [1.0] * len(items),
            "palabras": {e: {"categoria": "palabra"} for e, _ in items}}


DB_VACIA = {"plantillas": [], "duraciones": [], "palabras": {}}


# ---------------------------------------------------------------- elegir_plantilla

def test_elegir_sin_variantes():
    assert E.elegir_plantilla({"variantes": [], "etiqueta": "X"}, {}) is None


def test_elegir_una_variante():
    v = unit(1)
    assert E.elegir_plantilla({"variantes": [v], "etiqueta": "X"}, {"X": np.stack([unit(9)])}) is v


def test_elegir_dos_variantes_la_mas_cercana_a_la_base():
    a, b = unit(0), unit(3)
    base = {"X": np.stack([unit(3.1)])}
    assert E.elegir_plantilla({"variantes": [a, b], "etiqueta": "X"}, base) is b
    base = {"X": np.stack([unit(0.1)])}
    assert E.elegir_plantilla({"variantes": [a, b], "etiqueta": "X"}, base) is a


def test_elegir_etiqueta_sin_base_la_primera():
    a, b = unit(0), unit(3)
    assert E.elegir_plantilla({"variantes": [a, b], "etiqueta": "Z"}, {"X": np.stack([unit(3)])}) is a


# ---------------------------------------------------------------- comparador_para

def _etiquetas(c):
    return sorted(c._etiquetas)


def test_comparador_cenarec_solo_db():
    filas = [fila("A", "X", 0), fila("B", "Y", 1)]
    c = E.comparador_para(filas, {"B"}, db_de(("D", 5)), "cenarec")
    assert _etiquetas(c) == ["D"]


def test_comparador_equipo_solo_personas_pedidas():
    filas = [fila("A", "XA", 0), fila("B", "XB", 1), fila("C", "XC", 2)]
    c = E.comparador_para(filas, {"B", "C"}, db_de(("D", 5)), "equipo")
    assert _etiquetas(c) == ["XB", "XC"]
    assert "XA" not in c._etiquetas and "D" not in c._etiquetas


def test_comparador_todo_ambas():
    filas = [fila("A", "XA", 0), fila("B", "XB", 1)]
    c = E.comparador_para(filas, {"B"}, db_de(("D", 5)), "todo")
    assert _etiquetas(c) == ["D", "XB"]


def test_comparador_sin_plantillas_none():
    assert E.comparador_para([fila("A", "X", 0)], {"B"}, DB_VACIA, "equipo") is None
    assert E.comparador_para([], set(), DB_VACIA, "cenarec") is None


def test_comparador_ignora_plantilla_none():
    filas = [fila("B", "X", None), fila("B", "Y", 1)]
    c = E.comparador_para(filas, {"B"}, DB_VACIA, "equipo")
    assert _etiquetas(c) == ["Y"]
    assert E.comparador_para([fila("B", "X", None)], {"B"}, DB_VACIA, "equipo") is None


# ---------------------------------------------------------------- medir_toma

def _comp():
    return P.ComparadorPalabras(["X", "Y"], [unit(0), unit(4)], prefiltro=None)


def test_medir_toma_sin_variantes():
    assert E.medir_toma(fila("A", "X", None), _comp()) == {"top": [], "dicha": None}


def test_medir_toma_identica_a_plantilla():
    r = E.medir_toma(fila("A", "X", 0), _comp())
    assert r["top"][0] == "X"
    assert r["top"] == ["X", "Y"]
    assert r["dicha"] == "X"


def test_medir_toma_ambigua_no_se_acepta_pero_top_si():
    r = E.medir_toma(fila("A", "X", 2), _comp())  # equidistante: margen no pasa
    assert r["dicha"] is None
    assert set(r["top"]) == {"X", "Y"}


# ---------------------------------------------------------------- metricas

def test_metricas_vacia():
    assert E.metricas([]) == {"n": 0}


def test_metricas_cuentas():
    pares = [
        ("X", {"top": ["X", "Y", "Z"], "dicha": "X"}),     # top1, top3, bien
        ("X", {"top": ["Y", "X", "Z"], "dicha": "Y"}),     # top3, errónea
        ("X", {"top": ["Y", "Z", "W"], "dicha": None}),    # nada
        ("X", {"top": [], "dicha": None}),                 # sin seña
    ]
    m = E.metricas(pares)
    assert m["n"] == 4
    assert m["top1"] == pytest.approx(0.25)
    assert m["top3"] == pytest.approx(0.5)
    assert m["aceptada_bien"] == pytest.approx(0.25)
    assert m["aceptacion_erronea"] == pytest.approx(0.25)
    assert m["sin_sena"] == pytest.approx(0.25)


# ---------------------------------------------------------------- evaluar

def test_evaluar_nunca_usa_plantillas_de_la_misma_persona():
    # Con la propia plantilla (misma persona) cada toma acertaría; sin ella falla.
    filas = [fila("A", "X", 0), fila("B", "Y", 1)]
    r = E.evaluar(filas, DB_VACIA, "equipo")
    assert r["total"]["n"] == 2
    assert r["total"]["top1"] == 0.0
    assert r["por_persona"]["A"]["top1"] == 0.0
    assert r["por_persona"]["B"]["top1"] == 0.0


def test_evaluar_equipo_acierta_con_otra_persona():
    filas = [fila("A", "X", 0), fila("B", "X", 0.1)]
    r = E.evaluar(filas, DB_VACIA, "equipo")
    assert r["total"]["top1"] == 1.0


def test_evaluar_n_otras_promedia_combinaciones():
    filas = [fila("A", "X", 0), fila("B", "X", 0), fila("C", "X", 0)]
    todas = E.evaluar(filas, DB_VACIA, "equipo")
    una = E.evaluar(filas, DB_VACIA, "equipo", n_otras=1)
    assert todas["total"]["n"] == 3
    assert una["total"]["n"] == 6          # 3 tomas x 2 combinaciones
    assert una["por_persona"]["A"]["n"] == 2


def test_evaluar_n_otras_tampoco_usa_plantillas_de_la_misma_persona():
    # Cada palabra solo la tiene una persona: si alguna combinación usara su propia toma, acertaría.
    filas = [fila("A", "X", 0), fila("B", "Y", 1), fila("C", "Z", 2)]
    for fuente in ("equipo", "todo"):
        r = E.evaluar(filas, DB_VACIA, fuente, n_otras=1)
        assert r["total"]["n"] == 6 and r["total"]["top1"] == 0.0, fuente


def test_main_rechaza_personas_menor_que_uno():
    with pytest.raises(SystemExit):
        E.main(["--personas", "0"])


def test_evaluar_cenarec_no_depende_de_n_otras():
    filas = [fila("A", "X", 0), fila("B", "X", 0), fila("C", "X", 0)]
    db = db_de(("X", 0))
    a = E.evaluar(filas, db, "cenarec")
    b = E.evaluar(filas, db, "cenarec", n_otras=1)
    assert a["total"]["n"] == b["total"]["n"] == 3
    assert a == b


def test_evaluar_sin_plantillas_no_mide():
    r = E.evaluar([fila("A", "X", 0)], DB_VACIA, "equipo")
    assert r["total"] == {"n": 0}


# ---------------------------------------------------------------- preparar

def test_preparar_agrega_plantilla():
    filas = [
        {"persona": "A", "etiqueta": "X", "variantes": [unit(0)], "duracion": 1.0},
        {"persona": "A", "etiqueta": "X", "variantes": [], "duracion": 0.0},
        {"persona": "A", "etiqueta": "Q", "variantes": [unit(1), unit(2)], "duracion": 1.0},
    ]
    E.preparar(filas, db_de(("X", 0)))
    assert all("plantilla" in f for f in filas)
    assert filas[0]["plantilla"] is filas[0]["variantes"][0]
    assert filas[1]["plantilla"] is None
    assert filas[2]["plantilla"] is filas[2]["variantes"][0]  # etiqueta sin base: la primera
