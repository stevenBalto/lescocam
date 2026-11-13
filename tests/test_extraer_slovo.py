"""Pruebas de scripts/extraer_slovo.py con datos sintéticos (sin MediaPipe ni el zip real)."""
from __future__ import annotations

import io
import zipfile

from scripts import extraer_slovo as S

CABECERA = "attachment_id\ttext\tuser_id\theight\twidth\tlength\ttrain\tbegin\tend\n"


def _tsv(*filas: str) -> str:
    return CABECERA + "".join(f + "\n" for f in filas)


def _zip(archivos: dict[str, bytes]) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for nombre, datos in archivos.items():
            zf.writestr(nombre, datos)
    buf.seek(0)
    return zipfile.ZipFile(buf)


def _zip_en_disco(ruta, archivos: dict[str, bytes]):
    with zipfile.ZipFile(ruta, "w") as zf:
        for nombre, datos in archivos.items():
            zf.writestr(nombre, datos)
    return ruta


# --- leer_anotaciones ---

def test_leer_anotaciones_campos_y_cirilico():
    texto = _tsv("abc\tпривет\tu1\t360\t640\t40\tTrue\t36.0\t52.0")
    filas = S.leer_anotaciones(texto, {"abc.mp4": "train/abc.mp4"})
    assert filas == [{"id": "abc", "archivo": "abc.mp4", "glosa": "привет", "firmante": "u1",
                      "particion": "train", "inicio": 36, "fin": 52}]


def test_leer_anotaciones_omite_videos_que_no_estan_en_el_zip():
    texto = _tsv("a\tx\tu\t1\t1\t1\tTrue\t0\t1", "b\ty\tu\t1\t1\t1\tTrue\t0\t1")
    filas = S.leer_anotaciones(texto, {"b.mp4": "test/b.mp4"})
    assert [f["id"] for f in filas] == ["b"]


def test_leer_anotaciones_particion_solo_true_es_train():
    texto = _tsv("a\tx\tu\t1\t1\t1\tTrue\t0\t1",
                 "b\tx\tu\t1\t1\t1\tFalse\t0\t1",
                 "c\tx\tu\t1\t1\t1\t\t0\t1",
                 "d\tx\tu\t1\t1\t1\ttrue\t0\t1")
    videos = {f"{i}.mp4": f"{i}.mp4" for i in "abcd"}
    part = {f["id"]: f["particion"] for f in S.leer_anotaciones(texto, videos)}
    assert part == {"a": "train", "b": "test", "c": "test", "d": "test"}


def test_leer_anotaciones_begin_end_flotantes_y_vacios():
    texto = _tsv("a\tx\tu\t1\t1\t1\tTrue\t36.0\t52.9", "b\tx\tu\t1\t1\t1\tTrue\t\t")
    videos = {"a.mp4": "a.mp4", "b.mp4": "b.mp4"}
    por_id = {f["id"]: f for f in S.leer_anotaciones(texto, videos)}
    assert (por_id["a"]["inicio"], por_id["a"]["fin"]) == (36, 52)
    assert (por_id["b"]["inicio"], por_id["b"]["fin"]) == (0, 0)


def test_leer_anotaciones_omite_id_vacio():
    texto = _tsv("\tx\tu\t1\t1\t1\tTrue\t0\t1", "  \tx\tu\t1\t1\t1\tTrue\t0\t1")
    assert S.leer_anotaciones(texto, {".mp4": ".mp4"}) == []


def test_leer_anotaciones_ordenadas_por_id():
    texto = _tsv("c\tx\tu\t1\t1\t1\tTrue\t0\t1", "a\tx\tu\t1\t1\t1\tTrue\t0\t1",
                 "b\tx\tu\t1\t1\t1\tTrue\t0\t1")
    videos = {f"{i}.mp4": f"{i}.mp4" for i in "abc"}
    assert [f["id"] for f in S.leer_anotaciones(texto, videos)] == ["a", "b", "c"]


def test_leer_anotaciones_firmante_vacio_es_interrogacion_y_recorta_espacios():
    texto = _tsv("a\t  спасибо \t\t1\t1\t1\tTrue\t0\t1")
    f = S.leer_anotaciones(texto, {"a.mp4": "a.mp4"})[0]
    assert f["firmante"] == "?"
    assert f["glosa"] == "спасибо"


def test_leer_anotaciones_con_bom_decodificado_como_main():
    crudo = ("﻿" + _tsv("a\tпривет\tu\t1\t1\t1\tTrue\t0\t1")).encode("utf-8")
    filas = S.leer_anotaciones(crudo.decode("utf-8-sig"), {"a.mp4": "a.mp4"})
    assert len(filas) == 1 and filas[0]["glosa"] == "привет"


# --- indexar ---

def test_indexar_encuentra_tsv_y_videos_en_subcarpetas():
    zf = _zip({"slovo/annotations.tsv": b"x", "slovo/train/x.mp4": b"1", "slovo/test/y.mp4": b"2"})
    tsv, videos = S.indexar(zf)
    assert tsv == "slovo/annotations.tsv"
    assert videos == {"x.mp4": "slovo/train/x.mp4", "y.mp4": "slovo/test/y.mp4"}


def test_indexar_ignora_archivos_de_macos():
    zf = _zip({"annotations.tsv": b"x", "train/x.mp4": b"1", "train/._x.mp4": b"2",
               "__MACOSX/train/._y.mp4": b"3"})
    _, videos = S.indexar(zf)
    assert videos == {"x.mp4": "train/x.mp4"}


def test_indexar_sin_tsv_devuelve_none():
    tsv, videos = S.indexar(_zip({"train/x.mp4": b"1"}))
    assert tsv is None
    assert "x.mp4" in videos


def test_indexar_extension_mayuscula_y_otros_archivos():
    _, videos = S.indexar(_zip({"train/X.MP4": b"1", "train/leeme.txt": b"2"}))
    assert videos == {"X.MP4": "train/X.MP4"}


# --- main (solo los caminos de error, sin extraer nada) ---

def test_main_devuelve_2_si_no_es_zip(tmp_path):
    falso = tmp_path / "falso.zip"
    falso.write_bytes(b"esto no es un zip")
    assert S.main(["--zip", str(falso), "--carpeta", str(tmp_path / "salida")]) == 2


def test_main_devuelve_2_si_el_zip_no_existe(tmp_path):
    assert S.main(["--zip", str(tmp_path / "nada.zip"), "--carpeta", str(tmp_path / "salida")]) == 2


def test_main_devuelve_2_si_el_zip_no_tiene_annotations(tmp_path):
    z = _zip_en_disco(tmp_path / "sin_tsv.zip", {"train/x.mp4": b"1"})
    assert S.main(["--zip", str(z), "--carpeta", str(tmp_path / "salida")]) == 2


def test_main_devuelve_2_si_el_zip_no_tiene_videos(tmp_path):
    z = _zip_en_disco(tmp_path / "sin_videos.zip", {"annotations.tsv": CABECERA.encode()})
    assert S.main(["--zip", str(z), "--carpeta", str(tmp_path / "salida")]) == 2
