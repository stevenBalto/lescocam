"""Ajustes del puente motor ↔ interfaz (sin cámara ni sonido)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication

from desktop.motor import VELOCIDADES, Motor


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
