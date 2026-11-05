"""Banco de prueba de palabras: guardado, carga, retoma y métricas (sin cámara ni MediaPipe)."""
import numpy as np
import pytest

from core import banco
from core.cuerpo import CuadroCuerpo
from scripts import evaluar_banco, grabar_banco


def _cuadros(n=5, con_pose=True):
    pose = np.full((33, 4), 0.5, dtype=np.float32) if con_pose else None
    mano = (np.random.default_rng(0).random((21, 3)).astype(np.float32), "Right", 0.9)
    return [CuadroCuerpo(i / 30, (640, 480), [mano], pose) for i in range(n)]


def test_limpiar_persona():
    assert banco.limpiar_persona("Christian Paniagua Castro") == "christian-paniagua-castro"
    assert banco.limpiar_persona("  Ñandú/../x ") == "nandu..x".replace(".", "")
    assert banco.limpiar_persona("???") == "anonimo"


def test_guardar_y_cargar_ida_y_vuelta(tmp_path):
    ruta = banco.guardar_toma(_cuadros(), "NIÑO", 12, "Ana Ruiz", "baja", "lejos", "lado", tmp_path)
    assert ruta.parent.name == "ana-ruiz" and ruta.name == "12_NINO_1.npz"
    [t] = banco.cargar_tomas(tmp_path)
    assert (t.etiqueta, t.persona, t.luz, t.distancia, t.angulo) == ("NIÑO", "ana-ruiz", "baja", "lejos", "lado")
    assert len(t.cuadros) == 5 and t.cuadros[0].manos[0][1] == "Right" and t.cuadros[0].frame == (640, 480)


def test_no_pisa_tomas_y_cuenta(tmp_path):
    for _ in range(3):
        banco.guardar_toma(_cuadros(), "HOLA", 1, "ana", "buena", "media", "frente", tmp_path)
    assert banco.contar_tomas("ana", 1, tmp_path) == 3
    assert banco.contar_tomas("ana", 2, tmp_path) == 0
    assert banco.contar_tomas("otra", 1, tmp_path) == 0
    assert sorted(p.name for p in (tmp_path / "ana").glob("*.npz")) == ["01_HOLA_1.npz", "01_HOLA_2.npz", "01_HOLA_3.npz"]


def test_condicion_invalida_y_toma_vacia(tmp_path):
    with pytest.raises(ValueError):
        banco.guardar_toma(_cuadros(), "HOLA", 1, "ana", "oscura", "media", "frente", tmp_path)
    with pytest.raises(ValueError):
        banco.guardar_toma([], "HOLA", 1, "ana", "buena", "media", "frente", tmp_path)


def test_cobertura_cuerpo():
    assert banco.cobertura_cuerpo(_cuadros(4, con_pose=False)) == 0.0
    assert banco.cobertura_cuerpo(_cuadros(4)) == 1.0
    assert banco.cobertura_cuerpo(_cuadros(2) + _cuadros(2, con_pose=False)) == 0.5
    assert banco.cobertura_cuerpo([]) == 0.0


def test_listas_de_las_cuatro_personas():
    from collections import Counter
    from scripts.extraer_cenarec import leer_lista
    iniciales = set(leer_lista())
    todas = {p: banco.leer_lista(banco.lista_de(p)) for p in banco.PERSONAS}
    for p, lista in todas.items():
        assert len(lista) == 30 and len(set(lista)) == 30, p
        assert set(lista) <= iniciales, p
    cuenta = Counter(e for l in todas.values() for e in l)
    nucleo = {e for e, n in cuenta.items() if n == 4}
    assert len(nucleo) == 12                                   # las graban los 4
    assert all(n == 1 for e, n in cuenta.items() if e not in nucleo)   # lo demás, una sola persona
    assert iniciales - set(cuenta) == {"LESCO"}                # la reserva
    for p in ("steven", "reyman", "johan"):                    # tandas de 10: 4 del núcleo + 6 propias
        for t in range(3):
            tanda = todas[p][t * 10:(t + 1) * 10]
            assert sum(e in nucleo for e in tanda) == 4, (p, t)


def test_lista_de_por_nombre_de_pila():
    assert banco.lista_de("Steven Baltodano").name == "steven.txt"
    assert banco.lista_de("Johan Morales Chacón").name == "johan.txt"
    assert banco.lista_de("reyman").name == "reyman.txt"
    assert banco.lista_de("Christian Paniagua Castro").name == "christian.txt"
    with pytest.raises(ValueError):
        banco.lista_de("Pedro Perez")
    with pytest.raises(ValueError):
        banco.lista_de("Stevenson")   # empieza igual, no es el nombre de pila


def test_plan_por_tandas():
    assert banco.plan_de(0)[0] == ("buena", "media", "frente") and banco.plan_de(0)[2] == 1
    assert banco.plan_de(9)[2] == 1 and banco.plan_de(10)[2] == 2 and banco.plan_de(20)[2] == 3
    assert banco.plan_de(29)[0] == ("baja", "media", "lado")
    for cond, _ in banco.PLAN:
        assert cond[0] in banco.LUCES and cond[1] in banco.DISTANCIAS and cond[2] in banco.ANGULOS


def test_camara_en_la_toma_y_asignar(tmp_path):
    banco.guardar_toma(_cuadros(), "HOLA", 1, "ana", "buena", "media", "frente", tmp_path, camara="HP Windows")
    banco.guardar_toma(_cuadros(), "HOLA", 1, "ana", "buena", "media", "frente", tmp_path)
    cam = sorted(t.camara for t in banco.cargar_tomas(tmp_path))
    assert cam == ["desconocida", "hp-windows"]
    assert banco.asignar_camara("ana", "iphone13", tmp_path) == 1        # solo la que no tenía
    assert sorted(t.camara for t in banco.cargar_tomas(tmp_path)) == ["hp-windows", "iphone13"]
    assert banco.asignar_camara("ana", "otra", tmp_path) == 0


def _lista_corta(tmp_path, palabras):
    carpeta = tmp_path / "listas"
    carpeta.mkdir()
    (carpeta / "steven.txt").write_text("# c\n" + "\n".join(palabras) + "\n", encoding="utf-8")
    return carpeta


def test_registrar_revisa_completo_y_problemas(tmp_path):
    from scripts import registrar_banco as rb
    listas = _lista_corta(tmp_path, ["A", "B"])
    raiz = tmp_path / "banco"
    for _ in range(2):
        banco.guardar_toma(_cuadros(), "A", 1, "Steven Baltodano", "buena", "media", "frente", raiz, camara="hp-linux")
    r = rb.revisar("Steven Baltodano", raiz, listas)
    assert not rb.completo(r) and r["faltan"] == {"B": 2}
    banco.guardar_toma(_cuadros(), "ZZZ", 3, "Steven Baltodano", "buena", "media", "frente", raiz, camara="hp-linux")
    for _ in range(2):
        banco.guardar_toma(_cuadros(), "B", 2, "Steven Baltodano", "baja", "lejos", "lado", raiz)   # sin cámara
    r = rb.revisar("Steven Baltodano", raiz, listas)
    assert r["ajenas"] == ["ZZZ"] and not rb.completo(r)
    assert any("sin cámara" in p for p in rb.problemas(r)) and any("no son de tu lista" in p for p in rb.problemas(r))
    banco.asignar_camara("Steven Baltodano", "hp-linux", raiz)
    for ruta in (raiz / "steven-baltodano").glob("03_ZZZ_*.npz"):
        ruta.unlink()
    r = rb.revisar("Steven Baltodano", raiz, listas)
    assert rb.completo(r) and r["camaras"] == {"hp-linux": 4}
    md = rb.registro_md(r, {"top1": 0.5, "top3": 0.75, "aceptada_bien": 0.25, "aceptacion_erronea": 0.0,
                            "no_dice_nada": 0.75, "sin_sena": 0.0}, "2026-11-05")
    assert "COMPLETO" in md and "hp-linux: 4" in md and "50.0%" in md and "2026-11-05" in md


def test_estado_de_las_cuatro_personas(tmp_path):
    from scripts import registrar_banco as rb
    listas = tmp_path / "listas"
    listas.mkdir()
    for p in banco.PERSONAS:
        (listas / f"{p}.txt").write_text("A\nB\n", encoding="utf-8")
    raiz = tmp_path / "banco"
    for orden, e in ((1, "A"), (2, "B")):
        for _ in range(2):
            banco.guardar_toma(_cuadros(), e, orden, "Johan Morales", "buena", "media", "frente", raiz, camara="huawei")
    est = {p: (n, esperadas, ok) for p, n, esperadas, ok, _ in rb.estado(raiz, listas, tmp_path / "reg")}
    assert est["johan"] == (4, 4, True) and est["steven"] == (0, 4, False)


def test_primera_pendiente_retoma(tmp_path):
    palabras = ["A", "B", "C"]
    assert grabar_banco.primera_pendiente("ana", palabras, 2, 0, tmp_path) == 0
    for _ in range(2):
        banco.guardar_toma(_cuadros(), "A", 1, "ana", "buena", "media", "frente", tmp_path)
    assert grabar_banco.primera_pendiente("ana", palabras, 2, 0, tmp_path) == 1
    assert grabar_banco.primera_pendiente("ana", palabras, 2, 2, tmp_path) == 2
    for o, e in ((2, "B"), (3, "C")):
        for _ in range(2):
            banco.guardar_toma(_cuadros(), e, o, "ana", "buena", "media", "frente", tmp_path)
    assert grabar_banco.primera_pendiente("ana", palabras, 2, 0, tmp_path) is None


def _fila(pedida, top, aceptada, hubo=True):
    return {"etiqueta": pedida, "top": [(e, 0.9) for e in top], "aceptada": aceptada, "hubo_sena": hubo}


def test_metricas():
    filas = [
        _fila("HOLA", ["HOLA", "ADIÓS"], "HOLA"),          # bien
        _fila("CASA", ["ESCUELA", "CASA", "BAÑO"], None),   # top3 pero calla
        _fila("SÍ", ["NO", "SÍ"], "NO"),                    # aceptación errónea
        _fila("AYER", [], None, hubo=False),                # sin seña
    ]
    m = evaluar_banco.metricas(filas)
    assert m["n"] == 4
    assert m["top1"] == 0.25 and m["top3"] == 0.75
    assert m["aceptada_bien"] == 0.25 and m["aceptacion_erronea"] == 0.25
    assert m["no_dice_nada"] == 0.5 and m["sin_sena"] == 0.25
    assert evaluar_banco.metricas([]) == {"n": 0}


def test_confusiones():
    filas = [_fila("SÍ", ["NO"], "NO"), _fila("SÍ", ["NO"], "NO"), _fila("CASA", ["ESCUELA"], None),
             _fila("HOLA", ["HOLA"], "HOLA")]
    assert evaluar_banco.confusiones(filas)[0] == ("SÍ", "NO", 2)
    assert ("CASA", "ESCUELA (sin aceptar)", 1) in evaluar_banco.confusiones(filas)
