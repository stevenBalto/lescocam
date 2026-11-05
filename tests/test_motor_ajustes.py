"""Ajustes del puente motor ↔ interfaz (sin cámara ni sonido)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication

from desktop.motor import MODO_LETRAS, MODO_PALABRAS, VELOCIDADES, Motor, texto_palabra


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


def test_valores_por_defecto(qapp):
    motor = Motor(camara_permitida=False)
    assert motor.espejo and motor.puntosMano and motor.pausarSinManos
    assert motor.velocidad == "Normal"


def test_cambiar_ajustes_avisa_a_la_interfaz(qapp):
    motor = Motor(camara_permitida=False)
    avisos = []
    motor.ajusteCambio.connect(lambda: avisos.append(1))
    motor.espejo = False
    motor.elegirVelocidad("Rápida")
    assert motor.espejo is False
    assert motor.velocidad == "Rápida"
    assert len(avisos) == 2


def test_velocidad_desconocida_se_ignora(qapp):
    motor = Motor(camara_permitida=False)
    motor.elegirVelocidad("Turbo")
    assert motor.velocidad == "Normal"
    assert set(VELOCIDADES) == {"Lenta", "Normal", "Rápida"}


def test_sin_camara_permitida_no_se_guarda_nada(qapp):
    assert Motor(camara_permitida=False)._ajustes is None


def test_modo_por_defecto_es_letras_y_se_cambia(qapp, monkeypatch):
    monkeypatch.delenv("LESCOCAM_MODO", raising=False)
    motor = Motor(camara_permitida=False)
    assert motor.modo == MODO_LETRAS
    motor.elegirModo(MODO_PALABRAS)
    assert motor.modo == MODO_PALABRAS
    motor.elegirModo("otro")
    assert motor.modo == MODO_PALABRAS


def test_variable_de_entorno_fuerza_el_modo(qapp, monkeypatch):
    monkeypatch.setenv("LESCOCAM_MODO", "palabras")
    assert Motor(camara_permitida=False).modo == MODO_PALABRAS
    monkeypatch.setenv("LESCOCAM_MODO", "cualquiera")
    assert Motor(camara_permitida=False).modo == MODO_LETRAS


@pytest.mark.parametrize("etiqueta, texto", [
    ("HOLA", "hola"), ("POR-FAVOR", "por favor"), ("COSTA-RICA", "costa rica"),
    ("TIERRA(PLANETA)", "tierra"), ("INFORMAR-2", "informar"), ("SÍ", "sí"),
])
def test_texto_palabra(etiqueta, texto):
    assert texto_palabra(etiqueta) == texto
