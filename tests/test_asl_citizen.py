"""ASL Citizen: muestra estratificada, lectura del zip, reanudación, errores y landmarks_v1.npz
(sin MediaPipe ni videos reales: el detector se sustituye por uno falso)."""
import json
import zipfile
from collections import Counter

import numpy as np
import pytest

from core.cuerpo import CuadroCuerpo, a_arrays, desde_arrays
from scripts import construir_landmarks_asl as cla
from scripts import extraer_asl_citizen as eac


# ---------------------------------------------------------------- utilidades

def _fila(i, glosa, firmante, particion="train"):
    return {"id": f"v{i:04d}", "archivo": f"v{i:04d}.mp4", "glosa": glosa,
            "firmante": firmante, "particion": particion}


def _filas_sinteticas():
    filas, i = [], 0
    for g in range(10):
        for k in range(8):
            filas.append(_fila(i, f"G{g}", f"P{k % 4}", "train" if k < 6 else "val"))
            i += 1
    return filas


def _csv(filas):
    lineas = ["Participant ID,Video file,Gloss,ASL-LEX Code"]
    lineas += [f"{f['firmante']},{f['archivo']},{f['glosa']},code" for f in filas]
    return "\n".join(lineas) + "\n"


def _zip_sintetico(ruta, filas, extra_test=()):
    por = {"train": [], "val": [], "test": []}
    for f in list(filas) + list(extra_test):
        por[f["particion"]].append(f)
    with zipfile.ZipFile(ruta, "w") as zf:
        for part, fs in por.items():
            zf.writestr(f"ASL_Citizen/splits/{part}.csv", "﻿" + _csv(fs))
        for f in list(filas) + list(extra_test):
            zf.writestr(f"ASL_Citizen/videos/{f['archivo']}", b"no-es-un-video")
        zf.writestr("__MACOSX/._basura.mp4", b"x")
        zf.writestr("ASL_Citizen/videos/._oculto.mp4", b"x")
    return ruta


def _cuadros_falsos(n=4, semilla=0):
    rng = np.random.default_rng(semilla)
    mano = (rng.random((21, 3)).astype(np.float32), "Right", 0.9)
    pose = np.full((33, 4), 0.5, dtype=np.float32)
    return [CuadroCuerpo(i / 30, (640, 480), [mano], pose) for i in range(n)]


@pytest.fixture
def falso_extractor(monkeypatch):
    """extraer_cuadros falso; falla si el video temporal contiene el texto 'roto'. Pool en proceso."""
    llamadas = []

    def falso(ruta_video, saltar, alto_max, recorte=True):
        llamadas.append(ruta_video)
        with open(ruta_video, "rb") as fh:
            if b"roto" in fh.read():
                raise ValueError("video corrupto")
        return a_arrays(_cuadros_falsos()), 30.0

    class PoolFalso:
        def __init__(self, n, initializer=None, initargs=()):
            if initializer:
                initializer(*initargs)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def imap_unordered(self, fn, it, chunksize=1):
            return map(fn, it)

    monkeypatch.setattr(eac, "extraer_cuadros", falso)
    monkeypatch.setattr(eac, "Pool", PoolFalso)
    return llamadas


# ---------------------------------------------------------------- muestra

def test_muestra_solo_train_val_y_glosas_con_2_videos():
    filas = _filas_sinteticas()
    filas += [_fila(900 + i, "GTEST", "P0", "test") for i in range(5)]
    filas += [_fila(950, "SOLA", "P1", "train")]                       # 1 video: se descarta
    filas += [_fila(960, "MIXTA", "P1", "train"), _fila(961, "MIXTA", "P2", "test")]  # 1 usable
    m = eac.armar_muestra(filas, 1000, 7)
    assert {f["particion"] for f in m} <= {"train", "val"}
    glosas = {f["glosa"] for f in m}
    assert not glosas & {"GTEST", "SOLA", "MIXTA"}
    assert len(m) == 80 and len({f["id"] for f in m}) == 80          # n mayor al total: todo lo usable


def test_muestra_reproducible_y_semilla_cambia():
    filas = _filas_sinteticas()
    a = eac.armar_muestra(filas, 30, 7)
    assert a == eac.armar_muestra(list(filas), 30, 7)
    assert [f["id"] for f in a] != [f["id"] for f in eac.armar_muestra(filas, 30, 8)]
    assert len(a) == 30


def test_muestra_reparto_parejo_entre_glosas_y_firmantes():
    m = eac.armar_muestra(_filas_sinteticas(), 40, 3)
    por_glosa = Counter(f["glosa"] for f in m)
    assert set(por_glosa.values()) == {4}                              # 40 / 10 glosas
    por_firmante = Counter(f["firmante"] for f in m)
    assert max(por_firmante.values()) - min(por_firmante.values()) <= 1


def test_cuotas_por_glosa_con_tope_y_sobrante():
    c = eac.cuotas_por_glosa({"a": 2, "b": 10, "c": 10}, 14)
    assert sum(c.values()) == 14 and c["a"] == 2 and c["b"] == 6 and c["c"] == 6
    assert eac.cuotas_por_glosa({"a": 2, "b": 3}, 100) == {"a": 2, "b": 3}
    assert eac.cuotas_por_glosa({}, 5) == {}


# ---------------------------------------------------------------- zip / CSV

def test_indexar_y_leer_zip(tmp_path):
    filas = _filas_sinteticas()[:6]
    ruta = _zip_sintetico(tmp_path / "a.zip", filas)
    with zipfile.ZipFile(ruta) as zf:
        csvs, videos = eac.indexar_zip(zf)
        assert set(csvs) == {"train", "val", "test"}
        assert set(videos) == {f["archivo"] for f in filas}            # sin __MACOSX ni ._
        leidas = eac.leer_particiones(zf, csvs)
    assert len(leidas) == 6
    r = next(f for f in leidas if f["id"] == "v0000")
    assert (r["glosa"], r["firmante"], r["particion"], r["archivo"]) == ("G0", "P0", "train", "v0000.mp4")


def test_leer_particiones_ignora_filas_incompletas(tmp_path):
    ruta = tmp_path / "b.zip"
    with zipfile.ZipFile(ruta, "w") as zf:
        zf.writestr("train.csv", "Participant ID,Video file,Gloss\nP1,x.mp4,HOLA\nP2,,ADIOS\nP3,y.mp4,\n,z.mp4,SI\n")
    with zipfile.ZipFile(ruta) as zf:
        csvs, _ = eac.indexar_zip(zf)
        filas = eac.leer_particiones(zf, csvs)
    assert [(f["id"], f["firmante"]) for f in filas] == [("x", "P1"), ("z", "?")]


# ---------------------------------------------------------------- main: muestra, reanudación, errores

def test_solo_muestra_escribe_json(tmp_path):
    ruta = _zip_sintetico(tmp_path / "a.zip", _filas_sinteticas(), [_fila(900, "GT", "P0", "test"), _fila(901, "GT", "P1", "test")])
    carpeta = tmp_path / "salida"
    assert eac.main(["--zip", str(ruta), "--carpeta", str(carpeta), "--n", "20", "--solo-muestra"]) == 0
    d = json.loads((carpeta / "muestra.json").read_text(encoding="utf-8"))
    assert d["n"] == 20 and len(d["videos"]) == 20 and d["particiones"] == ["train", "val"]
    assert all(v["glosa"] != "GT" for v in d["videos"])


def test_zip_invalido_y_estructura_inesperada(tmp_path, capsys):
    malo = tmp_path / "no.zip"
    malo.write_bytes(b"incompleto")
    assert eac.main(["--zip", str(malo), "--carpeta", str(tmp_path / "s")]) == 2
    vacio = tmp_path / "vacio.zip"
    with zipfile.ZipFile(vacio, "w") as zf:
        zf.writestr("leeme.txt", "hola")
    assert eac.main(["--zip", str(vacio), "--carpeta", str(tmp_path / "s")]) == 2


def test_extraccion_reanuda_y_anota_errores(tmp_path, falso_extractor):
    filas = _filas_sinteticas()[:16]
    ruta = _zip_sintetico(tmp_path / "a.zip", filas)
    # un video roto: se reemplaza su contenido en un zip nuevo
    with zipfile.ZipFile(ruta) as zin, zipfile.ZipFile(tmp_path / "r.zip", "w") as zout:
        for n in zin.namelist():
            zout.writestr(n, b"roto" if n.endswith("v0003.mp4") else zin.read(n))
    carpeta = tmp_path / "salida"
    args = ["--zip", str(tmp_path / "r.zip"), "--carpeta", str(carpeta), "--n", "16", "--procesos", "1"]
    assert eac.main(args) == 0
    npzs = {p.stem for p in (carpeta / "extraccion").glob("*.npz")}
    assert len(npzs) == 15 and "v0003" not in npzs                    # el lote siguió pese al error
    errores = json.loads((carpeta / "errores.json").read_text(encoding="utf-8"))
    assert list(errores) == ["v0003"] and "ValueError" in errores["v0003"]
    assert not list((carpeta / "extraccion").glob("*.tmp.npz"))
    with np.load(carpeta / "extraccion" / "v0000.npz") as d:           # contenido del .npz por video
        assert str(d["glosa"]) == "G0" and str(d["particion"]) == "train" and float(d["fps"]) == 30.0
        assert d["manos"].shape == (4, 2, 21, 3)
    # segunda corrida: solo reintenta el que falló
    falso_extractor.clear()
    assert eac.main(args) == 0
    assert len(falso_extractor) == 1


def test_reanudacion_salta_npz_existente(tmp_path, falso_extractor):
    ruta = _zip_sintetico(tmp_path / "a.zip", _filas_sinteticas()[:8])
    carpeta = tmp_path / "salida"
    args = ["--zip", str(ruta), "--carpeta", str(carpeta), "--n", "8", "--procesos", "1"]
    assert eac.main(args) == 0
    assert len(falso_extractor) == 8
    (carpeta / "extraccion" / "v0001.npz").unlink()
    falso_extractor.clear()
    assert eac.main(args) == 0
    assert len(falso_extractor) == 1                                   # solo el borrado


def test_trabajo_cache_no_toca_el_video(tmp_path):
    destino = tmp_path / "x.npz"
    destino.write_bytes(b"ya")
    r = eac._trabajo((_fila(1, "G", "P"), "no-existe.mp4", str(destino), 1, 480, True))
    assert r[0] == "v0001" and r[4] == "cache" and destino.read_bytes() == b"ya"


def test_trabajo_borra_video_temporal(tmp_path, falso_extractor):
    with zipfile.ZipFile(tmp_path / "z.zip", "w") as zf:
        zf.writestr("v/v0001.mp4", b"datos")
    eac._iniciar(str(tmp_path / "z.zip"))
    try:
        r = eac._trabajo((_fila(1, "G", "P"), "v/v0001.mp4", str(tmp_path / "o.npz"), 2, 480, True))
    finally:
        eac._ZF.close()
        eac._ZF = None
    assert r[4] == "ok" and r[2] == 4
    import os
    assert not os.path.exists(falso_extractor[0])
    with np.load(tmp_path / "o.npz") as d:
        assert int(d["saltar"]) == 2


# ---------------------------------------------------------------- construir_landmarks_asl

def _guardar_extraccion(carpeta, i, n, glosa, firmante, particion="train", saltar=1, con_pose=True):
    ext = carpeta / "extraccion"
    ext.mkdir(parents=True, exist_ok=True)
    cuadros = _cuadros_falsos(n, semilla=i)
    if not con_pose:
        for c in cuadros:
            c.pose = None
    np.savez_compressed(ext / f"v{i:04d}.npz", fps=np.float64(30.0), saltar=np.int32(saltar),
                        id=np.array(f"v{i:04d}"), glosa=np.array(glosa), firmante=np.array(firmante),
                        particion=np.array(particion), **a_arrays(cuadros))


def test_construir_tipos_offsets_e_ida_y_vuelta(tmp_path):
    _guardar_extraccion(tmp_path, 1, 3, "HOLA", "P1", "train")
    _guardar_extraccion(tmp_path, 2, 5, "ADIOS", "P2", "val", saltar=2, con_pose=False)
    res = cla.construir(tmp_path)
    assert res["videos"] == 2 and res["fotogramas"] == 8 and res["glosas"] == 2
    assert res["particiones"] == {"train": 1, "val": 1} and res["omitidos"] == []
    assert res["pct_con_cuerpo"] == 37.5 and res["pct_con_dos_manos"] == 0.0
    with np.load(tmp_path / "landmarks_v1.npz") as d:
        assert d["manos"].dtype == np.float16 and d["pose"].dtype == np.float16
        assert d["score"].dtype == np.float16 and d["t"].dtype == np.float32 and d["lado"].dtype == np.int8
        assert d["offsets"].dtype == np.int64 and list(d["offsets"]) == [0, 3, 8]
    lm = cla.cargar(tmp_path / "landmarks_v1.npz")
    assert len(lm) == 2 and list(lm.ids) == ["v0001", "v0002"] and list(lm.saltar) == [1, 2]
    assert list(lm.indices("val")) == [1] and list(lm.indices(glosa="HOLA")) == [0]
    v = lm.video(0)
    assert v["manos"].dtype == np.float32 and v["t"].dtype == np.float64 and v["manos"].shape == (3, 2, 21, 3)
    original = _cuadros_falsos(3, semilla=1)
    vuelta = desde_arrays(v)
    assert len(vuelta) == 3 and vuelta[0].frame == (640, 480)
    assert np.allclose(vuelta[1].manos[0][0], original[1].manos[0][0], atol=1e-3)   # tolerancia float16
    assert vuelta[1].manos[0][1] == "Right" and vuelta[2].t == pytest.approx(2 / 30, abs=1e-6)
    assert desde_arrays(lm.video(1))[0].pose is None                                 # NaN -> sin persona


def test_construir_sin_comprimir_se_carga(tmp_path):
    _guardar_extraccion(tmp_path, 1, 3, "HOLA", "P1")
    cla.construir(tmp_path, comprimir=False)
    lm = cla.cargar(tmp_path / "landmarks_v1.npz")
    assert lm.video(0)["pose"].shape == (3, 33, 4)


def test_construir_omite_danados_y_tmp(tmp_path):
    _guardar_extraccion(tmp_path, 1, 3, "HOLA", "P1")
    (tmp_path / "extraccion" / "v0002.npz").write_bytes(b"basura")
    (tmp_path / "extraccion" / "v0003.tmp.npz").write_bytes(b"parcial")
    res = cla.construir(tmp_path)
    assert res["videos"] == 1 and len(res["omitidos"]) == 1 and "v0002.npz" in res["omitidos"][0]


def test_construir_sin_archivos_falla(tmp_path):
    (tmp_path / "extraccion").mkdir()
    with pytest.raises(SystemExit):
        cla.construir(tmp_path)
    (tmp_path / "extraccion" / "x.npz").write_bytes(b"basura")
    with pytest.raises(SystemExit):
        cla.construir(tmp_path)


def test_construir_main_con_salida_propia(tmp_path, capsys):
    _guardar_extraccion(tmp_path, 1, 2, "HOLA", "P1")
    salida = tmp_path / "otra" / "lm.npz"
    assert cla.main(["--carpeta", str(tmp_path), "--salida", str(salida)]) == 0
    assert salida.exists() and not (tmp_path / "landmarks_v1.npz").exists()
