"""Ronda 3 del banco: listas, videos de referencia (CENAREC + Hands-On) y base del motor."""
from pathlib import Path

from core import banco, senas_db
from scripts import armar_ronda3 as R
from scripts.grabar_banco import catalogo_referencias


def test_palabras_ronda3_sin_las_del_banco():
    assert R.palabras_ronda3(["HOLA", "CASA", "PERRO", "CASA"], {"HOLA"}) == ["CASA", "PERRO"]


def test_orden_fijo_por_persona_y_distinto_entre_personas():
    palabras = [f"P{i}" for i in range(200)]
    a = R.orden_de("christian", palabras)
    assert a == R.orden_de("christian", palabras)
    assert sorted(a) == sorted(palabras)
    assert a != R.orden_de("steven", palabras)


def test_escribir_y_leer_lista(tmp_path):
    ruta = R.escribir("johan", ["CASA", "ÁRBOL"], tmp_path)
    assert ruta == tmp_path / "johan.txt"
    assert banco.leer_lista(ruta) == ["CASA", "ÁRBOL"]


def test_listas_versionadas_iguales_salvo_el_orden():
    listas = {p: banco.leer_lista(R.LISTAS / f"{p}.txt") for p in banco.PERSONAS}
    base = sorted(listas["christian"])
    assert len(base) == len(set(base)) > 2000
    assert all(sorted(l) == base for l in listas.values())
    assert not set(base) & set(banco.leer_lista(R.INICIALES))


def test_catalogo_referencias_cenarec_primero_y_handson_por_clave(tmp_path):
    cenarec = {"CAFÉ (BEBIDA)": {"archivo": "cafe.mp4"}, "HOLA": {"archivo": "hola.mp4"}}
    handson = {
        "2": {"etiqueta": "café", "archivo": "cafe_2.mp4"},          # ya está en CENAREC: no se toca
        "5": {"etiqueta": "abuso físico 2", "archivo": "abuso_5.mp4"},
        "4": {"etiqueta": "abuso físico 1", "archivo": "abuso_4.mp4"},  # el primero por etiqueta gana
    }
    cat = catalogo_referencias(cenarec, handson, tmp_path)
    assert cat["CAFÉ (BEBIDA)"] == {"archivo": "cafe.mp4"}
    assert cat["HOLA"] == {"archivo": "hola.mp4"}
    assert Path(cat["ABUSO-FÍSICO"]["archivo"]) == (tmp_path / "abuso_4.mp4").resolve()
    assert Path(cat["ABUSO-FÍSICO"]["archivo"]).is_absolute()


def test_ruta_motor_usa_la_completa_si_existe(tmp_path, monkeypatch):
    completa = tmp_path / "senas_completa.db"
    monkeypatch.setattr(senas_db, "RUTA_DB_COMPLETA", completa)
    assert senas_db.ruta_motor() == senas_db.RUTA_DB
    completa.write_bytes(b"")
    assert senas_db.ruta_motor() == completa


def test_clave_palabra_normaliza_la_enie_descompuesta():
    from scripts.construir_palabras import clave_palabra
    import unicodedata
    assert clave_palabra(unicodedata.normalize("NFD", "seña")) == clave_palabra("SEÑA") == "SEÑA"


def test_clave_unica_aplica_repetidas():
    from scripts.construir_palabras import clave_unica
    assert clave_unica("colores", {"COLORES": "COLOR"}) == "COLOR"
    assert clave_unica("casa 2", {}) == "CASA"


def test_texto_base_y_candidatas():
    from scripts.repetidas_handson import candidatas, texto_base
    assert texto_base("CÓMO-2") == "como"
    assert texto_base("PROFESORES") == "profesor"
    assert texto_base("ABUELOS") == "abuelo"
    pares = candidatas(["FELIZ", "FELIZ/CONTENTO/ALEGRE", "COLOR", "COLORES", "PERRO"])
    assert ("FELIZ", "FELIZ/CONTENTO/ALEGRE") in pares
    assert ("COLOR", "COLORES") in pares
    assert not any("PERRO" in p for p in pares)


def test_elegir_nunca_junta_dos_de_cenarec_y_resuelve_cadenas():
    from scripts.repetidas_handson import elegir
    cen = {"NIÑO", "NIÑO-2", "FELIZ/CONTENTO/ALEGRE"}
    sims = [(0.9, "NIÑO", "NIÑO-2"),                       # dos de CENAREC: no
            (0.8, "CONTENTO", "FELIZ/CONTENTO/ALEGRE"),    # Hands-On -> CENAREC
            (0.75, "ALEGRE", "CONTENTO"),                  # Hands-On -> Hands-On -> CENAREC
            (0.5, "BAJO", "BAJOS")]                         # poco parecidas: no
    assert elegir(sims, cen, 0.7) == {"CONTENTO": "FELIZ/CONTENTO/ALEGRE", "ALEGRE": "FELIZ/CONTENTO/ALEGRE"}
