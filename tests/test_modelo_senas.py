"""Fase 4: descriptores_asl, modelo_senas y entrenar_embedding (todo sintético y en CPU)."""
import json

import numpy as np
import pytest
import torch

from core import palabras as P
from core import senas_db
from scripts import descriptores_asl as da
from scripts import entrenar_embedding as ee
from scripts import modelo_senas as ms
from tests.test_palabras import formas, palabra_cuadros, reposo, sena  # noqa: F401


@pytest.fixture(autouse=True)
def solo_cpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)


# ---------------------------------------------------------------- descriptores_asl

def _video(cuerpos):
    return palabra_cuadros(cuerpos), [c.t for c in cuerpos]


def _dos_senas(formas):  # noqa: F811
    """reposo, seña corta (0.6 s), reposo, seña larga (1.5 s), reposo."""
    a = reposo(0.0, 1.0)
    b = sena(formas, t0=1.0, duracion=0.6)
    c = reposo(1.6, 1.0)
    d = sena(formas, t0=2.6, duracion=1.5)
    e = reposo(4.1, 1.0)
    return a + b + c + d + e


def test_sena_de_toma_la_mas_larga(formas):  # noqa: F811
    cuadros, tiempos = _video(_dos_senas(formas))
    todas = P.segmentar(cuadros, tiempos)
    assert len(todas) == 2
    elegida, como = da.sena_de(cuadros, tiempos)
    assert como == "segmentador"
    assert elegida[-1].t - elegida[0].t == pytest.approx(max(s[-1].t - s[0].t for s in todas))
    assert elegida[0].t > 2.0


def test_sena_de_cae_a_fuera_de_reposo_si_dura_mas_que_el_maximo(formas):  # noqa: F811
    larga = sena(formas, duracion=P.DURACION_MAX + 2.0)
    cuadros, tiempos = _video(larga)
    assert P.segmentar(cuadros, tiempos) == []
    elegida, como = da.sena_de(cuadros, tiempos)
    assert como == "fuera_reposo" and len(elegida) >= 2


def test_sena_de_nada_si_solo_hay_reposo_o_no_hay_cuadros():
    cuadros, tiempos = _video(reposo(0.0, 2.0))
    assert da.sena_de(cuadros, tiempos) == (None, "nada")
    assert da.sena_de([None, None], [0.0, 0.1]) == (None, "nada")
    assert da.describir([None, None], [0.0, 0.1]) == ([], "nada", 0.0)


def test_describir_forma_dtype_y_variantes(formas):  # noqa: F811
    cuadros, tiempos = _video(reposo(0.0, 0.8) + sena(formas, t0=0.8, duracion=1.0) + reposo(1.8, 0.8))
    variantes, como, dur = da.describir(cuadros, tiempos)
    assert como == "segmentador" and dur > 0.5
    assert variantes and len(variantes) <= 2
    for espejo, d in variantes:
        assert isinstance(espejo, (bool, np.bool_))
        assert d.shape == (P.MUESTRAS, P.COLUMNAS) and d.dtype == np.float32
    assert len({bool(e) for e, _ in variantes}) == len(variantes)


def test_describir_dos_manos_da_las_variantes_de_espejos_posibles(formas):  # noqa: F811
    cuerpos = reposo(0.0, 0.8) + sena(formas, t0=0.8, duracion=1.0, brazos=(0, 1)) + reposo(1.8, 0.8)
    cuadros, tiempos = _video(cuerpos)
    sena_, _ = da.sena_de(cuadros, tiempos)
    posibles = P.espejos_posibles(sena_, "auto")
    variantes, _, _ = da.describir(cuadros, tiempos)
    assert [e for e, _ in variantes] == posibles


# ---------------------------------------------------------------- modelo_senas

def _modelo(**kw):
    torch.manual_seed(0)
    cfg = dict(columnas=P.COLUMNAS, ancho=16, bloques=2, embedding=8)
    cfg.update(kw)
    return ms.ModeloSenas(**cfg).eval()


def test_salida_forma_y_norma_uno():
    x = torch.randn(5, P.MUESTRAS, P.COLUMNAS)
    e = _modelo()(x)
    assert e.shape == (5, 8)
    assert torch.allclose(e.norm(dim=1), torch.ones(5), atol=1e-5)


def test_media_y_desvio_se_aplican():
    m = _modelo()
    x = torch.randn(3, P.MUESTRAS, P.COLUMNAS)
    base = m(x)
    m.media.fill_(2.0)
    m.desvio.fill_(3.0)
    assert not torch.allclose(m(x), base)
    z = torch.randn(3, P.MUESTRAS, P.COLUMNAS)
    assert torch.allclose(m(2.0 + 3.0 * z), _modelo()(z), atol=1e-5)


def test_guardar_y_cargar_ida_y_vuelta_con_extra_numpy(tmp_path):
    m = _modelo()
    m.media.copy_(torch.randn(P.COLUMNAS))
    m.desvio.copy_(torch.rand(P.COLUMNAS) + 0.5)
    extra = {"a": np.float64(0.5), "b": np.bool_(True), "c": np.int64(3), "r": {"x": [np.float32(1.5)]}}
    ruta = tmp_path / "m.pt"
    ms.guardar(m, ruta, extra)
    crudo = torch.load(ruta, weights_only=True)
    e = json.loads(crudo["extra"])
    assert e["a"] == 0.5 and e["b"] is True and e["c"] == 3
    m2 = ms.cargar(ruta)
    assert m2.config == m.config and not m2.training
    x = torch.randn(4, P.MUESTRAS, P.COLUMNAS)
    with torch.no_grad():
        assert torch.allclose(m(x), m2(x), atol=1e-6)


def test_guardar_sin_extra(tmp_path):
    ms.guardar(_modelo(), tmp_path / "m.pt")
    assert json.loads(torch.load(tmp_path / "m.pt", weights_only=True)["extra"]) == {}


def test_arcface_perdida_finita_y_baja():
    torch.manual_seed(0)
    clases, emb = 4, 8
    centros = torch.randn(clases, P.COLUMNAS) * 3
    y = torch.arange(clases).repeat_interleave(16)
    x = (centros[y] + 0.1 * torch.randn(len(y), P.COLUMNAS)).unsqueeze(1).repeat(1, P.MUESTRAS, 1)
    m = ms.ModeloSenas(columnas=P.COLUMNAS, ancho=16, bloques=1, embedding=emb, abandono=0.0)
    cabeza = ms.CabezaArcFace(emb, clases, margen=0.4)
    opt = torch.optim.Adam(list(m.parameters()) + list(cabeza.parameters()), lr=1e-2)
    perdidas = []
    for _ in range(30):
        p = cabeza(m(x), y)
        assert torch.isfinite(p)
        opt.zero_grad()
        p.backward()
        opt.step()
        perdidas.append(p.item())
    assert perdidas[-1] < perdidas[0] * 0.5


def test_arcface_con_cos_extremo_sigue_finita():
    e = torch.tensor([[1.0, 0.0], [0.0, 1.0]], requires_grad=True)
    cabeza = ms.CabezaArcFace(2, 2)
    with torch.no_grad():
        cabeza.pesos.copy_(torch.eye(2))
    p = cabeza(e, torch.tensor([0, 1]))
    p.backward()
    assert torch.isfinite(p) and torch.isfinite(e.grad).all()


# ---------------------------------------------------------------- entrenar_embedding: datos

def _glosas_firmantes():
    glosas, firm, part, video = [], [], [], []
    v = 0
    for g in range(20):
        for k in range(4):
            glosas.append(f"G{g:02d}")
            firm.append(f"P{k}")
            part.append("val" if k == 3 else "train")
            video.append(v)
            v += 1
    return np.array(glosas), np.array(firm), np.array(part), np.array(video)


def test_separar_nuevas_fuera_del_entrenamiento_y_reproducible():
    glosas, _, part, _ = _glosas_firmantes()
    nuevas, ent = ee.separar(glosas, part, 0.15, 7)
    assert len(nuevas) == 3
    assert not ent[np.isin(glosas, list(nuevas))].any()
    assert (part[ent] == "train").all()
    assert ent.sum() == 17 * 3
    nuevas2, ent2 = ee.separar(glosas, part, 0.15, 7)
    assert nuevas == nuevas2 and (ent == ent2).all()


def test_galeria_y_consultas():
    glosas, firm, _, video = _glosas_firmantes()
    glosas, firm, video = np.repeat(glosas, 2), np.repeat(firm, 2), np.repeat(video, 2)   # 2 variantes por video
    mascara = np.ones(len(glosas), bool)
    gal, con = ee.galeria_y_consultas(video, glosas, firm, mascara, 3)
    assert len(set(glosas[gal])) == 20
    for g in set(glosas):
        filas = gal[glosas[gal] == g]
        assert len(filas) == 2 and len(set(video[filas])) == 1
        c = con[glosas[con] == g]
        assert len(c) == 6 and (firm[c] != firm[filas[0]]).all()
    gal2, con2 = ee.galeria_y_consultas(video, glosas, firm, mascara, 3)
    assert (gal == gal2).all() and (con == con2).all()


def test_galeria_salta_glosas_con_un_solo_video():
    glosas = np.array(["A", "A", "B", "B", "B"])
    video = np.array([0, 1, 2, 3, 4])
    firm = np.array(["p", "q", "p", "q", "r"])
    gal, con = ee.galeria_y_consultas(video, glosas, firm, np.array([1, 1, 1, 1, 1], bool), 0)
    assert set(glosas[gal]) == {"A", "B"}
    gal, con = ee.galeria_y_consultas(video, glosas, firm, np.array([1, 0, 1, 1, 1], bool), 0)
    assert set(glosas[gal]) == {"B"}
    assert len(gal) == 1 and (glosas[con] == "B").all()


# ---------------------------------------------------------------- entrenar_embedding: aumentación y métricas

def _lote(b=6, t=P.MUESTRAS):
    g = torch.Generator().manual_seed(1)
    x = torch.randn(b, t, P.COLUMNAS, generator=g)
    x[:, :, ee.ACTIVA] = 0.0
    x[:, :, ee.B:2 * ee.B] = 0.0              # no dominante inactiva
    x[: b // 2, :, ee.ACTIVA] = 1.0           # la mitad con no dominante activa
    x[: b // 2, :, ee.B:2 * ee.B] = torch.randn(b // 2, t, ee.B, generator=g)
    return x


def test_aumentar_forma_inactiva_en_cero_y_activa_igual():
    x = _lote()
    y = ee.aumentar(x, torch.Generator().manual_seed(0))
    assert y.shape == x.shape
    assert not torch.allclose(y, x)
    ina = x[:, 0, ee.ACTIVA] == 0
    assert (y[ina][:, :, ee.B:2 * ee.B] == 0).all()
    assert torch.equal(y[:, :, ee.ACTIVA], x[:, :, ee.ACTIVA])


def test_aumentar_reproducible_con_el_mismo_generador():
    x = _lote()
    a = ee.aumentar(x, torch.Generator().manual_seed(5))
    b = ee.aumentar(x, torch.Generator().manual_seed(5))
    c = ee.aumentar(x, torch.Generator().manual_seed(6))
    assert torch.equal(a, b) and not torch.equal(a, c)


def test_top1_por_video_junta_variantes_con_el_maximo():
    clases = np.array(["a", "b", "c"])
    sim = np.array([[0.1, 0.9, 0.0],
                    [0.8, 0.2, 0.0],
                    [0.0, 0.1, 0.7]])
    r = ee.top1_por_video(sim, np.array([0, 0, 1]), np.array(["a", "a", "c"]), clases)
    assert r["videos"] == 2 and r["clases"] == 3
    assert r["top1"] == 0.5 and r["top5"] == 1.0      # max del video 0 = [0.8, 0.9, 0] -> gana b
    sim[1, 0] = 0.95
    r = ee.top1_por_video(sim, np.array([0, 0, 1]), np.array(["a", "a", "c"]), clases)
    assert r["top1"] == 1.0


def test_top1_vacio():
    r = ee.top1_por_video(np.zeros((0, 2)), np.array([]), np.array([]), np.array(["a", "b"]))
    assert r["videos"] == 0 and r["top1"] == 0


def test_sim_por_glosa_maximo_por_glosa():
    sim = np.array([[0.1, 0.5, 0.2, 0.9], [1.0, 0.0, 0.3, 0.4]])
    s, clases = ee.sim_por_glosa(sim, np.array(["b", "a", "b", "a"]))
    assert list(clases) == ["a", "b"]
    assert np.allclose(s, [[0.9, 0.2], [0.4, 1.0]])
    assert s.dtype == np.float32


def test_zfilas():
    s = np.array([[1.0, 2.0, 3.0], [5.0, 5.0, 5.0]])
    z = ee.zfilas(s)
    assert np.allclose(z[0].mean(), 0) and np.allclose(z[0].std(), 1)
    assert np.isfinite(z).all() and np.allclose(z[1], 0)


def test_evaluar_cenarec_excluye_la_diagonal():
    etiquetas = np.array(["a", "a", "b", "b"])
    e = np.array([[1, 0], [1, 0.01], [0, 1], [0.01, 1]], dtype=np.float32)
    assert ee.evaluar_cenarec(e, etiquetas)["top1"] == 1.0
    # con vectores idénticos, sin excluir la diagonal ganaría siempre uno mismo; aquí el vecino es otra palabra
    e2 = np.array([[1, 0], [0, 1], [1, 0], [0, 1]], dtype=np.float32)
    assert ee.evaluar_cenarec(e2, np.array(["a", "b", "a", "b"]))["top1"] == 1.0
    e3 = np.array([[1, 0], [1, 0], [0, 1], [0, 1]], dtype=np.float32)
    assert ee.evaluar_cenarec(e3, np.array(["a", "b", "a", "b"]))["top1"] == 0.0
    r = ee.evaluar_cenarec(e, np.array(["a", "a", "b", "c"]))
    assert r["plantillas"] == 2                       # palabras con una sola plantilla no cuentan


def test_evaluar_cenarec_con_distancias():
    dist = np.array([[0, 1, 5], [1, 0, 5], [5, 5, 0]], dtype=float)
    r = ee.evaluar_cenarec(None, np.array(["a", "a", "b"]), dist)
    assert r == {"plantillas": 2, "top1": 1.0}
    assert dist[0, 0] == 0                            # no se modifica la entrada del llamador


# ---------------------------------------------------------------- entrenar_embedding: main de punta a punta

def _datos_npz(ruta):
    rng = np.random.default_rng(0)
    glosas, firm, part, video = _glosas_firmantes()
    centros = rng.normal(size=(20, 1, P.COLUMNAS)) * 2
    g = np.array([int(s[1:]) for s in glosas])
    x = (centros[g] + 0.3 * rng.normal(size=(len(g), P.MUESTRAS, P.COLUMNAS))).astype(np.float32)
    x[:, :, ee.ACTIVA] = 0
    np.savez_compressed(ruta, x=x, video=video.astype(np.int32), espejo=np.zeros(len(g), bool), glosas=glosas,
                        firmantes=firm, particiones=part)
    return ruta


def _db(ruta):
    rng = np.random.default_rng(1)
    entradas = []
    for e in ("HOLA", "GRACIAS", "CASA"):
        base = rng.normal(size=(P.MUESTRAS, P.COLUMNAS))
        entradas.append({"etiqueta": e, "idw": 1, "manos": 1, "fuente": "prueba",
                         "plantillas": [{"repeticion": r, "fuente": "x", "inicio": 0.0, "fin": 1.0,
                                         "crudo": base + 0.05 * rng.normal(size=base.shape)} for r in range(3)]})
    senas_db.escribir(ruta, entradas, "prueba")
    return ruta


def test_cenarec_lee_las_palabras(tmp_path):
    x, et = ee.cenarec(_db(tmp_path / "senas.db"))
    assert x.shape == (9, P.MUESTRAS, P.COLUMNAS) and x.dtype == np.float32
    assert set(et) == {"HOLA", "GRACIAS", "CASA"}


def test_main_punta_a_punta(tmp_path, capsys):
    datos = _datos_npz(tmp_path / "descriptores_v3.npz")
    db = _db(tmp_path / "senas.db")
    salida = tmp_path / "modelo" / "embedding_v1.pt"
    rc = ee.main(["--datos", str(datos), "--db", str(db), "--salida", str(salida), "--epocas", "2",
                  "--dtw-max", "5", "--ancho", "16", "--bloques", "1", "--lote", "32"])
    assert rc == 0 and salida.exists()
    r = json.loads((tmp_path / "modelo" / "reporte_v1.json").read_text(encoding="utf-8"))
    assert r["epoca_elegida"] in (1, 2)
    assert {"A", "B", "C_cenarec", "dtw", "B_dtw_y_fusion"} <= set(r["final"])
    assert len(r["glosas_nuevas"]) == 3
    assert set(r["final"]["B_dtw_y_fusion"]) == {"0.0", "0.3", "0.5", "0.7", "1.0"}
    assert ms.cargar(salida).config["ancho"] == 16      # weights_only=True con el reporte dentro de extra
    assert "época" in capsys.readouterr().out
