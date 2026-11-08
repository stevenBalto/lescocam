"""scripts/medir_dos_manos.brazos_arriba: qué cuadros cuentan para medir el detector."""
import numpy as np

from scripts.medir_dos_manos import brazos_arriba


def _pose(muneca_izq_y, muneca_der_y, vis=1.0):
    p = np.full((1, 33, 4), np.nan, dtype=np.float32)
    p[0, 11] = (0.40, 0.40, 0, 1)   # hombros: ancho = 0.2 * 16/9 ≈ 0.356 en unidades de alto
    p[0, 12] = (0.60, 0.40, 0, 1)
    p[0, 15] = (0.35, muneca_izq_y, 0, vis)
    p[0, 16] = (0.65, muneca_der_y, 0, vis)
    return p


def test_dos_brazos_levantados_cuenta():
    assert brazos_arriba(_pose(0.45, 0.50)).tolist() == [True]


def test_un_brazo_en_reposo_no_cuenta():
    # 0.40 + 0.85 * 0.356 ≈ 0.70: más abajo es reposo
    assert brazos_arriba(_pose(0.45, 0.75)).tolist() == [False]


def test_muneca_fuera_de_la_imagen_o_poco_visible_no_cuenta():
    assert brazos_arriba(_pose(0.45, 1.05)).tolist() == [False]
    assert brazos_arriba(_pose(0.45, 0.50, vis=0.2)).tolist() == [False]


def test_sin_pose_no_cuenta():
    assert brazos_arriba(np.full((2, 33, 4), np.nan, dtype=np.float32)).tolist() == [False, False]
