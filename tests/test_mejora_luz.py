"""Mejoras de luz y medidor de nivel (core/mejora_luz.py, problema 4)."""

import numpy as np
import pytest

from core.mejora_luz import (
    CONDICIONES_LUZ,
    LUZ_BAJA_ENTRA,
    LUZ_REGULAR_ENTRA,
    LUZ_REGULAR_SALE,
    MedidorLuz,
    brillo,
    brillo_central,
    caja_puntos,
    clahe,
    denoise,
    gamma,
    mejorar,
    simular_luz,
)


def _frame(valor, ruido=0.0, forma=(120, 160)):
    """Frame BGR uint8 de brillo uniforme `valor`, con ruido gaussiano opcional."""
    img = np.full((*forma, 3), valor, dtype=np.float32)
    if ruido:
        img += np.random.default_rng(0).normal(0, ruido, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def test_brillo_mide_la_luma():
    assert brillo(_frame(0)) == pytest.approx(0, abs=1)
    assert brillo(_frame(200)) == pytest.approx(200, abs=1)


def test_brillo_en_caja_usa_solo_esa_zona():
    img = _frame(10)
    img[:20, :20] = 250                      # una esquina brillante
    assert brillo(img, (0, 0, 20, 20)) > 200
    assert brillo(img, (60, 60, 100, 100)) < 20


def test_gamma_aclara_lo_oscuro():
    oscuro = _frame(40)
    assert brillo(gamma(oscuro, 2.2)) > brillo(oscuro)


def test_gamma_uno_no_cambia_nada():
    img = _frame(80)
    assert np.array_equal(gamma(img, 1.0), img)


def test_denoise_baja_el_ruido():
    ruidoso = _frame(120, ruido=25)
    assert np.std(denoise(ruidoso).astype(np.float32)) < np.std(ruidoso.astype(np.float32))


def test_mejorar_conserva_forma_y_tipo():
    img = _frame(60, ruido=10)
    for estrategia in ("ninguna", "gamma", "clahe", "denoise_gamma", "denoise_clahe"):
        salida = mejorar(img, estrategia)
        assert salida.shape == img.shape
        assert salida.dtype == np.uint8


def test_mejorar_ninguna_no_toca():
    img = _frame(60)
    assert np.array_equal(mejorar(img, "ninguna"), img)


def test_mejorar_estrategia_desconocida_falla():
    with pytest.raises(ValueError):
        mejorar(_frame(60), "inventada")


def test_caja_puntos_cubre_los_landmarks():
    puntos = [(0.4, 0.4), (0.6, 0.6)]
    caja = caja_puntos(puntos, 100, 100, margen=0.0)
    assert caja == (40, 40, 60, 60)


def test_caja_puntos_vacio_es_none():
    assert caja_puntos([], 100, 100) is None


def test_brillo_central_ignora_los_bordes():
    img = _frame(10)
    img[:30, :] = 250                         # franja brillante arriba (techo/ventana)
    # el brillo del cuadro entero sube por la franja, pero el central-bajo sigue oscuro
    assert brillo(img) > brillo_central(img)
    assert brillo_central(img) < 30


def test_simular_normal_no_toca():
    img = _frame(120)
    assert np.array_equal(simular_luz(img, "normal"), img)
    assert np.array_equal(simular_luz(img, None), img)


def test_simular_poca_luz_oscurece():
    img = _frame(120)
    for cond in ("poca_luz_1", "poca_luz_2", "poca_luz_3"):
        salida = simular_luz(img, cond)
        assert salida.shape == img.shape and salida.dtype == np.uint8
        assert brillo(salida) < brillo(img)             # queda más oscuro
    # a mayor nivel, más oscuro
    assert brillo(simular_luz(img, "poca_luz_3")) < brillo(simular_luz(img, "poca_luz_1"))


def test_simular_contraluz_quema_arriba_y_oscurece_abajo():
    img = _frame(120)
    salida = simular_luz(img, "contraluz_3")
    alto = salida.shape[0]
    arriba = brillo(salida[:alto // 5])
    abajo = brillo(salida[4 * alto // 5:])
    assert arriba > abajo                                # la ventana (arriba) queda más brillante


def test_condiciones_luz_incluye_normal():
    assert CONDICIONES_LUZ[0] == "normal"
    assert "contraluz_3" in CONDICIONES_LUZ


def test_nivel_buena_con_luz_suficiente():
    med = MedidorLuz()
    _, nivel, pedir, estrategia = med.antes_de_detectar(_frame(200))
    assert nivel == "buena"
    assert not pedir
    assert estrategia == "ninguna"


def test_nivel_regular_con_poca_luz():
    med = MedidorLuz()
    oscuro = _frame(int(LUZ_REGULAR_ENTRA) - 8)
    salida, nivel, pedir, estrategia = med.antes_de_detectar(oscuro)
    assert nivel == "regular"
    assert not pedir
    assert estrategia != "ninguna"            # se aplica una mejora
    assert salida.shape == oscuro.shape


def test_pide_mas_luz_con_muy_poca_luz():
    med = MedidorLuz()
    _, nivel, pedir, _ = med.antes_de_detectar(_frame(int(LUZ_BAJA_ENTRA) - 5))
    assert nivel == "baja"
    assert pedir


def test_se_recupera_solo_cuando_vuelve_la_luz():
    # No depende de manos: si el brillo vuelve a subir, el nivel baja a buena solo.
    med = MedidorLuz()
    med.antes_de_detectar(_frame(int(LUZ_BAJA_ENTRA) - 5))     # cae a baja
    assert med.antes_de_detectar(_frame(200))[1] == "buena"    # vuelve la luz -> buena


def test_histeresis_no_parpadea_en_el_limite():
    # Entre el umbral de entrada y el de salida de "regular", el nivel se mantiene.
    med = MedidorLuz()
    entre = _frame(int((LUZ_REGULAR_ENTRA + LUZ_REGULAR_SALE) / 2))
    assert med.antes_de_detectar(_frame(200))[1] == "buena"
    assert med.antes_de_detectar(entre)[1] == "buena"          # estando en buena, no entra a regular
    med.antes_de_detectar(_frame(int(LUZ_REGULAR_ENTRA) - 8))  # fuerza regular
    assert med.antes_de_detectar(entre)[1] == "regular"        # estando en regular, no vuelve a buena
