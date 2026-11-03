"""Letras con movimiento: formato de movimientos.json, DTW, segmentación y convivencia con las quietas."""

import json
from dataclasses import replace

import numpy as np
import pytest

from core.aceptador import Aceptador
from core.clasificador import Clasificador
from core.landmarks import VERSION_VECTOR, corregir_proporcion
from core.movimiento import (MUESTRAS, RUTA_MOVIMIENTOS, TIPO, VERSION_MOVIMIENTOS, Cuadro, ReconocedorMovimiento,
                             Segmentador, VersionIncompatible, cuadro_de_puntos, cuadros_de_toma, descriptor, dtw,
                             escribir_movimientos, leer_movimientos, movimientos_vacio, segmentar)
from core.reconocedor import Reconocedor

LETRAS = {"J", "LL", "Ñ", "RR", "Z"}


@pytest.fixture(scope="module")
def plantillas():
    datos = leer_movimientos()
    return {e: cuadros_de_toma(t) for e, entrada in datos["signs"].items() for t in entrada["takes"][:1]}


@pytest.fixture(scope="module")
def movimiento():
    return ReconocedorMovimiento()


@pytest.fixture(scope="module")
def clasificador():
    return Clasificador()


def con_tiempos(cuadros, t0, factor=1.0):
    """Copia de los cuadros con el tiempo corrido a t0 y estirado por factor."""
    base = cuadros[0].t
    return [replace(c, t=t0 + (c.t - base) * factor, _forma=None) for c in cuadros]


def quieta(cuadro, t0, segundos, fps, temblor=0.0, semilla=0):
    """La misma postura repetida (con un poco de temblor en píxeles = fracción de la escala)."""
    rng = np.random.default_rng(semilla)
    n = int(round(segundos * fps))
    return [replace(cuadro, t=t0 + i / fps, muneca=cuadro.muneca + rng.normal(0, temblor * cuadro.escala, 2),
                    _forma=None) for i in range(n)]


def flujo(gesto, fps=30.0, antes=0.7, despues=0.7, factor=1.0):
    """Postura inicial quieta, el gesto, postura final quieta (a fps dado)."""
    pre = quieta(gesto[0], 0.0, antes, fps, 0.005, 1)
    medio = con_tiempos(gesto, antes, factor)
    if fps < 25:   # submuestrea el gesto
        medio = [c for i, c in enumerate(medio) if i % 2 == 0]
    fin = medio[-1].t + 1 / fps
    post = quieta(gesto[-1], fin, despues, fps, 0.005, 2)
    return pre + medio + post


def pasar(rec, cuadros):
    dichas = []
    for c in cuadros:
        dichas += rec.actualizar_cuadro(c, c.vector, c.t)
    return dichas


# ---------------------------------------------------------------- formato (contrato con la app móvil)

def test_formato_de_movimientos_json():
    assert RUTA_MOVIMIENTOS.stat().st_size < 1_000_000
    datos = json.loads(RUTA_MOVIMIENTOS.read_text(encoding="utf-8"))
    assert datos["version"] == VERSION_MOVIMIENTOS
    assert datos["version_vector"] == VERSION_VECTOR
    assert set(datos["signs"]) == LETRAS
    for letra, entrada in datos["signs"].items():
        assert entrada["categoria"] == "letra"
        assert entrada["tipo"] == TIPO
        assert entrada["takes"]
        for toma in entrada["takes"]:
            assert toma["source"].startswith(("video:", "webcam:"))
            assert toma["fps"] > 0 and len(toma["frame"]) == 2
            tiempos = [c["t"] for c in toma["cuadros"]]
            assert tiempos[0] == 0.0 and tiempos == sorted(tiempos)
            for c in toma["cuadros"]:
                assert len(c["vector"]) == 63 and len(c["muneca"]) == 2
                assert c["escala"] > 0 and c["lado"] in ("Left", "Right")


def test_version_incompatible_se_rechaza(tmp_path):
    ruta = tmp_path / "movimientos.json"
    ruta.write_text(json.dumps({"version": 99, "version_vector": VERSION_VECTOR, "signs": {}}), encoding="utf-8")
    with pytest.raises(VersionIncompatible):
        leer_movimientos(ruta)
    ruta.write_text(json.dumps({"version": VERSION_MOVIMIENTOS, "version_vector": 2, "signs": {}}), encoding="utf-8")
    with pytest.raises(VersionIncompatible):
        leer_movimientos(ruta)


def test_escribir_y_leer_conserva_los_cuadros(tmp_path, plantillas):
    from core.movimiento import toma_desde_cuadros
    datos = movimientos_vacio()
    datos["signs"]["LL"] = {"categoria": "letra", "tipo": TIPO,
                            "takes": [toma_desde_cuadros(plantillas["LL"], "webcam:prueba", 30, (640, 480), "hoy")]}
    ruta = tmp_path / "m.json"
    escribir_movimientos(ruta, datos)
    vuelta = cuadros_de_toma(leer_movimientos(ruta)["signs"]["LL"]["takes"][0])
    assert len(vuelta) == len(plantillas["LL"])
    assert vuelta[0].t == 0.0
    assert vuelta[3].vector == pytest.approx(plantillas["LL"][3].vector, abs=1e-5)


@pytest.mark.parametrize("lado", ["Left", "Right"])
def test_puntos_px_reconstruye_la_imagen(lado):
    rng = np.random.default_rng(3)
    puntos = rng.uniform(0.2, 0.8, size=(21, 3))
    c = cuadro_de_puntos(puntos, lado, (640, 480), 0.0)
    assert c.puntos_px() == pytest.approx(corregir_proporcion(puntos, (640, 480))[:, :2], abs=1e-3)


def test_mano_cortada_por_el_borde_no_cuenta():
    puntos = np.random.default_rng(4).uniform(0.2, 0.8, size=(21, 3))
    puntos[20, 1] = 1.05
    assert cuadro_de_puntos(puntos, "Right", (640, 480), 0.0) is None


def test_guardar_movimientos_reemplaza_solo_las_del_mismo_video(tmp_path, plantillas):
    from pathlib import Path

    from scripts.importar_video import guardar_movimientos
    ruta = tmp_path / "m.json"
    guardar_movimientos({"J": plantillas["J"]}, Path("video.mp4"), 30.0, ruta)
    guardar_movimientos({"J": plantillas["J"]}, Path("video.mp4"), 30.0, ruta)
    guardar_movimientos({"J": plantillas["J"]}, Path("otro.mp4"), 30.0, ruta)
    fuentes = [t["source"] for t in leer_movimientos(ruta)["signs"]["J"]["takes"]]
    assert sorted(fuentes) == ["video:otro.mp4", "video:video.mp4"]


# ---------------------------------------------------------------- DTW y descriptor

def test_dtw_de_una_serie_consigo_misma_es_cero():
    a = np.random.default_rng(0).normal(size=(20, 5))
    assert dtw(a, a) == 0.0


def test_dtw_es_simetrico_y_absorbe_un_corrimiento():
    t = np.linspace(0, 1, 20)
    a = np.sin(2 * np.pi * t)[:, None]
    b = np.sin(2 * np.pi * (t - 0.1))[:, None]
    assert dtw(a, b) == pytest.approx(dtw(b, a))
    assert dtw(a, b) < np.abs(a - b).mean()   # alinear le gana a comparar punto a punto


def test_dtw_valor_conocido():
    """Para verificar la versión de Dart: pasos simétricos (diagonal x2) / (n + m)."""
    a = np.array([[0.0], [1.0], [2.0]])
    b = np.array([[0.0], [2.0]])
    # costos |a_i - b_j| = [[0, 2], [1, 1], [2, 0]]; el mejor camino es (0,0) diagonal 2*0,
    # (1,0) vertical +1, (2,1) diagonal 2*0 = 1; se divide por n + m = 5.
    assert dtw(a, b, banda=1.0) == pytest.approx(1.0 / 5)


def test_descriptor_no_depende_de_la_velocidad_ni_de_los_fps(plantillas):
    g = plantillas["Z"]
    d = descriptor(g)
    assert d.shape == (MUESTRAS, 31 + 6 + 2)
    assert descriptor(con_tiempos(g, 5.0, 1.3)) == pytest.approx(d)
    a_15 = descriptor(g[::2])
    assert dtw(d, a_15) < 0.25          # Z es la más rápida: a 15 fps pierde algo de detalle


def test_cada_plantilla_se_reconoce_a_si_misma(plantillas, movimiento):
    for letra, g in plantillas.items():
        assert movimiento.clasificar(g) == (letra, pytest.approx(1.0))


@pytest.mark.parametrize("factor", [0.7, 1.0, 1.3])
@pytest.mark.parametrize("paso", [1, 2])
def test_plantillas_mas_lentas_rapidas_y_a_15_fps(plantillas, movimiento, factor, paso):
    for letra, g in plantillas.items():
        assert movimiento.clasificar(con_tiempos(g, 0.0, factor)[::paso])[0] == letra


# ---------------------------------------------------------------- segmentación

@pytest.mark.parametrize("fps", [15.0, 30.0])
def test_segmenta_un_gesto_entre_dos_quietas(plantillas, fps):
    g = plantillas["LL"]
    gestos = segmentar(flujo(g, fps), [c.t for c in flujo(g, fps)])
    assert len(gestos) == 1
    duracion = g[-1].t - g[0].t
    assert gestos[0][-1].t - gestos[0][0].t == pytest.approx(duracion, abs=0.35)


@pytest.mark.parametrize("fps", [15.0, 30.0])
def test_quieta_con_temblor_no_es_un_gesto(plantillas, fps):
    """Temblor de 4 Hz y 0.05 manos de amplitud: no arranca ningún gesto."""
    c = plantillas["LL"][0]
    seg = Segmentador()
    for i in range(int(3 * fps)):
        t = i / fps
        movida = replace(c, t=t, muneca=c.muneca + [0.05 * c.escala * np.sin(2 * np.pi * 4 * t), 0], _forma=None)
        assert seg.actualizar(movida, t) is None
        assert not seg.moviendo


def test_perder_la_mano_cierra_el_gesto(plantillas):
    g = plantillas["Z"]
    seg = Segmentador()
    cuadros = quieta(g[0], 0.0, 0.5, 30.0) + con_tiempos(g, 0.5)
    for c in cuadros:
        assert seg.actualizar(c, c.t) is None
    fin = cuadros[-1].t
    assert seg.actualizar(None, fin + 0.1) is None
    gesto = seg.actualizar(None, fin + 0.5)
    assert gesto is not None and len(gesto) > 10


# ---------------------------------------------------------------- convivencia con las quietas

@pytest.mark.parametrize("fps", [15.0, 30.0])
def test_cada_letra_con_movimiento_se_dice_sola(plantillas, movimiento, clasificador, fps):
    """LL dice solo LL (no L + LL), J solo J (no I + J), etc."""
    pl = list(plantillas.items())
    for letra, g in plantillas.items():
        rec = Reconocedor(clasificador, Aceptador(), movimiento, pl)
        assert pasar(rec, flujo(g, fps)) == [letra]


def test_la_postura_final_no_se_dice_como_quieta(plantillas, movimiento, clasificador):
    """Después de LL la mano queda en L un buen rato: no se dice L."""
    rec = Reconocedor(clasificador, Aceptador(), movimiento, list(plantillas.items()))
    assert pasar(rec, flujo(plantillas["LL"], despues=3.0)) == ["LL"]


@pytest.mark.parametrize("letra_mov,base", [("LL", "L"), ("RR", "R"), ("J", "I")])
def test_la_base_quieta_con_temblor_no_dispara_movimiento(plantillas, movimiento, clasificador, letra_mov, base):
    """Una L quieta (con temblor) dice L, nunca LL."""
    rec = Reconocedor(clasificador, Aceptador(), movimiento, list(plantillas.items()))
    assert base in rec.bases[letra_mov]
    c = plantillas[letra_mov][0]
    cuadros = [replace(c, t=i / 30, muneca=c.muneca + [0.05 * c.escala * np.sin(2 * np.pi * 4 * i / 30), 0],
                       _forma=None) for i in range(60)]
    assert pasar(rec, cuadros) == [base]


def test_un_corrimiento_corto_no_es_ll(plantillas, movimiento, clasificador):
    """La L que se corre 0.25 manos (la persona acomoda la mano) no es LL."""
    rec = Reconocedor(clasificador, Aceptador(), movimiento, list(plantillas.items()))
    c = plantillas["LL"][0]
    cuadros = []
    for i in range(60):
        t = i / 30
        dx = 0.25 * c.escala * float(np.clip((t - 0.8) / 0.3, 0, 1))
        cuadros.append(replace(c, t=t, muneca=c.muneca + [dx, 0], _forma=None))
    assert "LL" not in pasar(rec, cuadros)


def test_sin_movimientos_se_comporta_como_el_aceptador(plantillas, clasificador):
    """Sin movimientos.json el Reconocedor dice lo mismo y cuando mismo que el Aceptador de siempre."""
    rec, aceptador = Reconocedor(clasificador, Aceptador()), Aceptador()
    cuadros = quieta(plantillas["LL"][0], 0.0, 2.0, 30.0) + quieta(plantillas["RR"][0], 2.0, 2.0, 30.0)
    for c in cuadros:
        assert rec.actualizar_cuadro(c, c.vector, c.t) == [
            x for x in [aceptador.actualizar(clasificador.mejores(c.vector, 2), c.t)] if x]


def test_desde_archivos_carga_quietas_y_movimiento():
    rec = Reconocedor.desde_archivos()
    assert rec.movimiento is not None and set(rec.movimiento.etiquetas) == LETRAS
