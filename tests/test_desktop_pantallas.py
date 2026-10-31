"""Recorre todas las pantallas y capas del prototipo y verifica que el QML carga sin errores.

Corre sin abrir ventanas (plataforma «offscreen» de Qt).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject
from PySide6.QtWidgets import QApplication

from desktop.app import Aplicacion

PANTALLAS = (
    "00a 00b 00c 00d 01 01r 01b 01d 01e 01h 01h2 01s 02 02a 02h 02b 03 03b 03c 03d 03g 03y 03h 03i "
    "04 04c 04e 06 07 07a 07h 07b 08 09 09s 09s2 09s3 09v 09g 09k 09m 09p 09e 09r1 09r2 "
    "12 12e 12h 12k 13 13s 13f 13l 13q 13m 14 14a 14c 14d 14e 14f 14g 15a 15b 15c 15d "
    "16 17 18 19 20 21 21b 22 23 23b 23n 24 24ok 25 25b 25c 25d 25e 26 26b"
).split()

CAPAS = [
    "Capa · Bandeja", "Capa · Bandeja · destello apagado", "Capa · Bandeja · burbuja oculta",
    "Capa · Bandeja · burbuja oculta · destello apagado", "Capa · Menú de la burbuja",
    "Capa · Historial rápido", "Capa · Detalle de seña", "Capa · Enseñar una seña · 1",
    "Capa · Enseñar una seña · 2", "Capa · Enseñar una seña · 3",
    "Capa · Aviso del historial · copiado", "Capa · Aviso del historial · audio",
    "Capa · Aviso del diccionario · copiado", "Capa · Aviso del diccionario · escuchar",
    "Capa · Aviso de ajustes · escuchar", "Capa · Windows pide la cámara",
]


@pytest.fixture(scope="module")
def app():
    qapp = QApplication.instance() or QApplication([])
    aplicacion = Aplicacion(dev=True, pantalla="01")
    avisos = []
    aplicacion.cargar()
    aplicacion.motor.warnings.connect(lambda lista: avisos.extend(a.toString() for a in lista))
    raiz = aplicacion.motor.rootObjects()[0]
    yield qapp, raiz, avisos
    for objeto in aplicacion.motor.rootObjects():
        objeto.deleteLater()


def _mostrar(qapp, raiz, metodo, valor):
    QMetaObject.invokeMethod(raiz, metodo, Q_ARG("QVariant", valor))
    for _ in range(5):
        qapp.processEvents()


@pytest.mark.parametrize("codigo", PANTALLAS)
def test_pantalla_carga_sin_errores(app, codigo):
    qapp, raiz, avisos = app
    avisos.clear()
    _mostrar(qapp, raiz, "irA", codigo)
    assert avisos == []


@pytest.mark.parametrize("nombre", CAPAS)
def test_capa_carga_sin_errores(app, nombre):
    qapp, raiz, avisos = app
    _mostrar(qapp, raiz, "irA", "02")
    avisos.clear()
    _mostrar(qapp, raiz, "abrirCapa", nombre)
    assert avisos == []
