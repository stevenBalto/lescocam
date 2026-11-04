"""Modo palabra: cuerpo + dos manos, reposo y segmentación, descriptor canónico, DTW y senas.db."""

import sqlite3

import numpy as np
import pytest

from core import palabras as P
from core import senas_db
from core.clasificador import leer_signs
from core.cuerpo import CuadroCuerpo, a_arrays, desde_arrays
from core.landmarks import VERSION_VECTOR
from core.movimiento import dtw
from core.reconocedor_palabras import ReconocedorPalabras

FRAME = (640, 360)
HOMBROS_Y = 150.0
ANCHO = 120.0                      # ancho de hombros en píxeles
CENTRO_X = 320.0
REPOSO = (CENTRO_X, HOMBROS_Y + 1.2 * ANCHO)


@pytest.fixture(scope="module")
def formas():
    """Vectores (63) de manos reales de signs.json: letra -> (21, 3) normalizado (como una derecha)."""
    datos = leer_signs()
    return {l: np.asarray(datos["signs"][l]["takes"][0]["vector"], dtype=np.float64).reshape(21, 3)
            for l in ("A", "B", "L", "Y")}


def mano_img(forma, muneca_px, brazo, escala=45.0, frame=FRAME, cx=CENTRO_X, rot=0.0):
    """21 landmarks normalizados de la imagen: una mano con la forma dada, la muñeca en muneca_px.

    El brazo 0 (izquierda de la imagen) lleva la imagen espejo, como una mano izquierda real.
    """
    v = forma.copy()
    if rot:
        c, s = np.cos(rot), np.sin(rot)
        v[:, :2] = v[:, :2] @ np.array([[c, -s], [s, c]]).T
    if brazo == 0:
        v[:, 0] = -v[:, 0]
    pts = np.empty((21, 3))
    pts[:, 0] = (muneca_px[0] + v[:, 0] * escala) / frame[0]
    pts[:, 1] = (muneca_px[1] + v[:, 1] * escala) / frame[1]
    pts[:, 2] = v[:, 2] * escala / frame[0]
    return pts


def pose_img(munecas, frame=FRAME, cx=CENTRO_X, hy=HOMBROS_Y, ancho=ANCHO):
    """Pose (33, 4): hombro 12 a la izquierda de la imagen (brazo 0), 11 a la derecha (brazo 1)."""
    p = np.zeros((33, 4))
    p[:, 3] = 1.0
    p[:, 0], p[:, 1] = cx / frame[0], (hy - 0.6 * ancho) / frame[1]
    p[12, :2] = (cx - ancho / 2) / frame[0], hy / frame[1]
    p[11, :2] = (cx + ancho / 2) / frame[0], hy / frame[1]
    p[16, :2] = munecas[0][0] / frame[0], munecas[0][1] / frame[1]
    p[15, :2] = munecas[1][0] / frame[0], munecas[1][1] / frame[1]
    return p


def cuerpo(t, munecas, formas_brazo, frame=FRAME, escala_px=1.0, dx=0.0, orden=(0, 1)):
    """CuadroCuerpo sintético. munecas: [(x, y)] px por brazo (en la escala de referencia);
    formas_brazo: [forma o None] por brazo. escala_px/dx simulan acercarse/correrse."""
    def px(p):
        return (CENTRO_X + (p[0] - CENTRO_X) * escala_px + dx, HOMBROS_Y + (p[1] - HOMBROS_Y) * escala_px)
    m = [px(x) for x in munecas]
    pose = pose_img(m, frame, CENTRO_X + dx, HOMBROS_Y, ANCHO * escala_px)
    manos = [(mano_img(formas_brazo[b], m[b], b, 45.0 * escala_px, frame), "Left" if b == 0 else "Right", 0.9)
             for b in orden if formas_brazo[b] is not None]
    return CuadroCuerpo(t, frame, manos, pose)


def sena(formas, t0=0.0, fps=30.0, duracion=1.0, brazos=(1,), forma="L", mano_quieta=None, **kw):
    """Una seña sintética: los brazos de `brazos` suben del reposo, dibujan un arco y bajan."""
    salida = []
    n = int(duracion * fps)
    for i in range(n):
        u = i / (n - 1)
        alto = np.sin(np.pi * u)                        # sube y baja
        munecas, fb = [REPOSO, REPOSO], [None, None]
        for b in brazos:
            lado = -1 if b == 0 else 1
            munecas[b] = (CENTRO_X + lado * (40 + 60 * u), REPOSO[1] - alto * 1.5 * ANCHO)
            fb[b] = formas[forma]
        if mano_quieta is not None:
            fb[mano_quieta] = formas["A"]
        salida.append(cuerpo(t0 + i / fps, munecas, fb, **kw))
    return salida


def reposo(t0, segundos, fps=30.0, **kw):
    return [cuerpo(t0 + i / fps, [REPOSO, REPOSO], [None, None], **kw) for i in range(int(segundos * fps))]


def palabra_cuadros(cuerpos):
    return [P.cuadro_palabra(c) for c in cuerpos]


# ---------------------------------------------------------------- cuadro del cuerpo

def test_cuadro_sin_cuerpo_o_sin_hombros():
    assert P.cuadro_palabra(CuadroCuerpo(0.0, FRAME, [], None)) is None
    p = pose_img([REPOSO, REPOSO])
    p[11, 3] = 0.1
    assert P.cuadro_palabra(CuadroCuerpo(0.0, FRAME, [], p)) is None


def test_manos_van_al_brazo_mas_cercano_sin_importar_el_orden(formas):
    m = [(250.0, 100.0), (390.0, 120.0)]
    for orden in ((0, 1), (1, 0)):
        c = P.cuadro_palabra(cuerpo(0.0, m, [formas["B"], formas["L"]], orden=orden))
        assert c.ancho == pytest.approx(ANCHO)
        assert np.allclose(c.centro, (CENTRO_X, HOMBROS_Y))
        assert np.allclose(c.muneca[0], m[0], atol=1e-3) and np.allclose(c.muneca[1], m[1], atol=1e-3)
        # Cada brazo tiene la forma de su mano (B abierta, L).
        assert np.linalg.norm(c.forma[0] - P.forma_mano(mano_img(formas["B"], m[0], 0), 0, FRAME)) < 1e-6
        assert np.linalg.norm(c.forma[1] - P.forma_mano(mano_img(formas["L"], m[1], 1), 1, FRAME)) < 1e-6


def test_forma_espejada_es_igual_en_los_dos_brazos(formas):
    """La izquierda (brazo 0, imagen espejo) se describe igual que la derecha: zurdos y diestros comparables."""
    d = P.forma_mano(mano_img(formas["L"], (400, 100), 1), 1, FRAME)
    i = P.forma_mano(mano_img(formas["L"], (240, 100), 0), 0, FRAME)
    assert d.shape == (P.FORMA,)
    assert np.allclose(d, i, atol=1e-6)


def test_sin_mano_detectada_usa_la_muneca_de_la_pose(formas):
    c = P.cuadro_palabra(cuerpo(0.0, [REPOSO, (400.0, 90.0)], [None, None]))
    assert np.allclose(c.muneca[1], (400.0, 90.0), atol=1e-3)
    assert c.forma == [None, None]


def test_reposo():
    c = P.cuadro_palabra(cuerpo(0.0, [REPOSO, REPOSO], [None, None]))
    assert P.en_reposo(c)
    alto = (CENTRO_X, HOMBROS_Y + (P.Y_REPOSO - 0.1) * ANCHO)
    c = P.cuadro_palabra(cuerpo(0.0, [REPOSO, alto], [None, None]))
    assert not P.en_reposo(c) and P.brazo_en_reposo(c, 0)
    # Muñeca fuera de cuadro (manos en el regazo) = reposo.
    c = P.cuadro_palabra(cuerpo(0.0, [REPOSO, (CENTRO_X, 400.0)], [None, None]))
    assert c.muneca[1] is None and P.en_reposo(c)
    assert P.en_reposo(None)


# ---------------------------------------------------------------- segmentación

def test_corta_las_dos_repeticiones(formas):
    flujo = reposo(0, 1.0) + sena(formas, 1.0) + reposo(2.0, 1.0) + sena(formas, 3.0) + reposo(4.0, 1.0)
    senas = P.segmentar(palabra_cuadros(flujo), [c.t for c in flujo])
    assert len(senas) == 2
    for s, t0 in zip(senas, (1.0, 3.0)):
        assert s[0].t == pytest.approx(t0, abs=P.PREVIOS + 0.1)
        assert s[-1].t == pytest.approx(t0 + 1.0, abs=0.2)


def test_descarta_muy_cortas_y_muy_largas(formas):
    corta = reposo(0, 1.0) + sena(formas, 1.0, duracion=0.2) + reposo(1.2, 1.0)
    assert P.segmentar(palabra_cuadros(corta), [c.t for c in corta]) == []
    larga = reposo(0, 1.0) + sena(formas, 1.0, duracion=P.DURACION_MAX + 1.5) + reposo(6.5, 1.0)
    assert P.segmentar(palabra_cuadros(larga), [c.t for c in larga]) == []


def test_sin_cuerpo_mucho_rato_corta_la_sena(formas):
    s = sena(formas, 1.0, duracion=1.2)
    flujo = reposo(0, 1.0) + s[:20]
    cuadros = palabra_cuadros(flujo) + [None] * 30
    tiempos = [c.t for c in flujo] + [flujo[-1].t + (i + 1) / 30 for i in range(30)]
    senas = P.segmentar(cuadros, tiempos)
    assert len(senas) == 1 and senas[0][-1].t <= flujo[-1].t + 1e-9


# ---------------------------------------------------------------- descriptor

def test_descriptor_forma_y_una_o_dos_manos(formas):
    una = [c for c in palabra_cuadros(sena(formas, brazos=(1,)))]
    dos = [c for c in palabra_cuadros(sena(formas, brazos=(0, 1)))]
    d1 = P.descriptor(una, False)
    d2 = P.descriptor(dos, False)
    assert d1.shape == d2.shape == (P.MUESTRAS, P.COLUMNAS)
    assert d1[0, -1] == 0 and not np.any(d1[:, P.BLOQUE:2 * P.BLOQUE])      # no dominante fuera
    assert d2[0, -1] == P.PESO_ACTIVA and np.any(d2[:, P.BLOQUE:2 * P.BLOQUE])


def test_espejos_posibles(formas):
    assert P.espejos_posibles(palabra_cuadros(sena(formas, brazos=(1,)))) == [False]
    assert P.espejos_posibles(palabra_cuadros(sena(formas, brazos=(0,)))) == [True]
    dos = palabra_cuadros(sena(formas, brazos=(0, 1)))
    assert P.espejos_posibles(dos) == [False, True]
    assert P.espejos_posibles(dos, "derecha") == [False]
    assert P.espejos_posibles(dos, "izquierda") == [True]


def test_zurdo_da_el_mismo_descriptor(formas):
    """La misma seña con la otra mano (imagen espejo) queda igual en forma canónica."""
    diestra = palabra_cuadros(sena(formas, brazos=(1,)))
    zurda = palabra_cuadros(sena(formas, brazos=(0,)))
    a = P.descriptores(diestra)
    b = P.descriptores(zurda)
    assert len(a) == len(b) == 1
    assert np.allclose(a[0], b[0], atol=1e-6)


def test_distancia_y_encuadre_no_cambian_el_descriptor(formas):
    base = P.descriptor(palabra_cuadros(sena(formas)), False)
    otra = P.descriptor(palabra_cuadros(sena(formas, escala_px=0.6, dx=-70.0)), False)
    assert np.allclose(base, otra, atol=1e-4)
    # Cámara 4:3 (otra proporción del frame): la corrección de proporción lo deja igual.
    cuatro_tercios = P.descriptor(palabra_cuadros(sena(formas, frame=(480, 360))), False)
    assert np.allclose(base, cuatro_tercios, atol=1e-4)


def test_velocidad_y_fps_casi_no_cambian_el_descriptor(formas):
    base = P.descriptor(palabra_cuadros(sena(formas)), False)
    lenta = P.descriptor(palabra_cuadros(sena(formas, duracion=1.4, fps=15.0)), False)
    assert np.abs(base - lenta).mean() < 0.05


# ---------------------------------------------------------------- comparación

def test_dtw_lote_igual_al_dtw_de_movimiento():
    rng = np.random.default_rng(3)
    a = rng.normal(size=(P.MUESTRAS, 5))
    plantillas = rng.normal(size=(4, P.MUESTRAS, 5))
    lote = P.dtw_lote(a, plantillas)
    for k in range(4):
        assert lote[k] == pytest.approx(dtw(a, plantillas[k], P.BANDA))
    assert P.dtw_lote(a, plantillas[:1] * 0 + a)[0] == pytest.approx(0.0, abs=1e-6)


def comparador_sintetico(formas):
    etiquetas, desc = [], []
    for nombre, kw in (("ARCO-L", {"forma": "L"}), ("ARCO-B", {"forma": "B"}), ("DOS-Y", {"forma": "Y", "brazos": (0, 1)})):
        etiquetas.append(nombre)
        cuadros = palabra_cuadros(sena(formas, **kw))
        desc.append(P.descriptor(cuadros, P.espejos_posibles(cuadros, "derecha")[0]))
    return P.ComparadorPalabras(etiquetas, desc)


def test_clasifica_y_nunca_inventa(formas):
    comp = comparador_sintetico(formas)
    palabra, conf, top = comp.clasificar(P.descriptores(palabra_cuadros(sena(formas, forma="B", duracion=1.2))))
    assert palabra == "ARCO-B" and conf > 0.9 and len(top) == 3
    # Zurdo haciendo la seña de dos manos: se prueba espejada y se reconoce igual.
    palabra, _, _ = comp.clasificar(P.descriptores(palabra_cuadros(sena(formas, forma="Y", brazos=(0, 1)))))
    assert palabra == "DOS-Y"
    # Dos plantillas iguales de palabras distintas: no hay margen, no dice nada.
    d = comp._plantillas[0]
    empate = P.ComparadorPalabras(["X", "Y"], [d, d])
    assert empate.clasificar([d])[0] is None
    # Nada parecido: no pasa el umbral.
    assert comp.clasificar([d + 5.0])[0] is None
    assert comp.clasificar([])[0] is None


# ---------------------------------------------------------------- senas.db (contrato con la app móvil)

def test_db_ida_y_vuelta(tmp_path, formas):
    cuadros = palabra_cuadros(sena(formas))
    crudo = P.descriptor(cuadros, False, pesos=(1, 1, 1, 1, 1))
    ruta = tmp_path / "senas.db"
    senas_db.escribir(ruta, [{"etiqueta": "ARCO", "idw": 1, "manos": 1, "fuente": "prueba",
                              "plantillas": [{"repeticion": 1, "fuente": "prueba", "inicio": 0.0, "fin": 1.0,
                                              "crudo": crudo}]}], "prueba")
    datos = senas_db.leer(ruta)
    assert datos["meta"]["columnas"] == str(P.COLUMNAS) and datos["meta"]["muestras"] == str(P.MUESTRAS)
    assert datos["palabras"]["ARCO"]["categoria"] == "palabra"
    (etiqueta, leido), = datos["plantillas"]
    assert etiqueta == "ARCO" and np.abs(leido - crudo).max() <= 0.5 / senas_db.ESCALA + 1e-12
    comp = senas_db.comparador(ruta)
    assert comp.clasificar(P.descriptores(cuadros))[0] == "ARCO"
    # Pesos guardados = pesos del motor.
    import json
    assert np.allclose(json.loads(datos["meta"]["pesos"]), senas_db.pesos_columnas())

    con = sqlite3.connect(ruta)
    con.execute("UPDATE meta SET valor = '99' WHERE clave = 'version_descriptor'")
    con.commit()
    con.close()
    with pytest.raises(senas_db.VersionIncompatible):
        senas_db.leer(ruta)


def test_senas_db_versionada():
    """data/reference/senas.db: las palabras iniciales, chica y con el formato del motor."""
    assert senas_db.RUTA_DB.stat().st_size < 2_000_000
    datos = senas_db.leer()
    assert datos["meta"]["version_vector"] == str(VERSION_VECTOR)
    lista = [l.strip() for l in (senas_db.RAIZ / "data" / "reference" / "palabras_iniciales.txt")
             .read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    palabras = {e for e, d in datos["palabras"].items() if d["categoria"] == "palabra"}
    assert palabras == set(lista)
    assert {d["categoria"] for d in datos["palabras"].values()} <= {"palabra", "letra"}
    assert len(datos["plantillas"]) >= len(datos["palabras"])
    for _, crudo in datos["plantillas"]:
        assert crudo.shape == (P.MUESTRAS, P.COLUMNAS) and np.all(np.isfinite(crudo))


# ---------------------------------------------------------------- en vivo

def test_reconocedor_en_vivo(formas):
    rec = ReconocedorPalabras(comparador_sintetico(formas))
    flujo = reposo(0, 1.0) + sena(formas, 1.0, forma="L", duracion=0.9) + reposo(1.9, 1.0)
    dichas = []
    for c in flujo:
        p = rec.actualizar(c, c.t)
        if p:
            dichas.append(p)
    assert dichas == ["ARCO-L"]
    assert rec.ultima[0] == "ARCO-L" and not rec.activo


def test_cache_de_arrays_ida_y_vuelta(formas):
    cuadros = sena(formas, duracion=0.3, brazos=(0, 1)) + [CuadroCuerpo(1.0, FRAME, [], None)]
    vuelta = desde_arrays(a_arrays(cuadros))
    assert len(vuelta) == len(cuadros) and vuelta[-1].pose is None
    for a, b in zip(cuadros[:-1], vuelta[:-1]):
        assert [l for _, l, _ in a.manos] == [l for _, l, _ in b.manos]
        assert np.allclose(a.manos[0][0], b.manos[0][0], atol=1e-6)
        assert np.allclose(a.pose, b.pose, atol=1e-6)


def test_plantilla_negativa_no_se_dice(formas):
    """Si la seña se parece más a una letra deletreada (categoría "letra") que a una palabra: nada."""
    cuadros = palabra_cuadros(sena(formas, forma="B"))
    d = P.descriptor(cuadros, False)
    otra = P.descriptor(palabra_cuadros(sena(formas, forma="L")), False)
    comp = P.ComparadorPalabras(["LETRA-B", "ARCO-L"], [d, otra], categorias={"LETRA-B": "letra"})
    assert comp.palabras == ["ARCO-L"]
    palabra, conf, top = comp.clasificar(P.descriptores(cuadros))
    assert palabra is None and top[0][0] == "LETRA-B" and conf > 0.9
    assert comp.clasificar(P.descriptores(palabra_cuadros(sena(formas, forma="L"))))[0] == "ARCO-L"
