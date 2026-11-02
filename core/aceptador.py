"""Acepta una letra solo si es estable: umbral + margen + un tiempo seguido.

La estabilidad se mide en segundos y no en frames, para que se comporte igual a
15 o a 30 fps. Además se piden unos pocos frames como mínimo, para que un salto
de la cámara (dos frames separados por medio segundo) no alcance.
"""
from __future__ import annotations

from typing import Optional

from core.clasificador import UMBRAL

# Diferencia mínima de confianza entre la mejor letra y la segunda (= 0.20 de
# distancia en rasgos) y tiempo seguido con la misma letra válida. Elegidos con
# scripts/evaluar_motor.py pasando el video entero por el aceptador. Con los
# vectores v2 (sin corregir la proporción) hacía falta margen 0.12; con la
# version 3 el margen 0.10 no inventa letras en el flujo (ni en transiciones ni
# en letras con movimiento) y acepta más: 16/25 letras contra 14/25 con 0.12.
# Bajar el umbral a 0.40 sumaba solo 1 letra más: se deja en 0.45.
MARGEN = 0.10
SEGUNDOS_ESTABLE = 0.4
FRAMES_MINIMOS = 4
SEGUNDOS_REPETIR = 1.5


class Aceptador:
    def __init__(self, umbral: float = UMBRAL, margen: float = MARGEN, segundos: float = SEGUNDOS_ESTABLE,
                 frames_minimos: int = FRAMES_MINIMOS, segundos_repetir: float = SEGUNDOS_REPETIR):
        self.umbral, self.margen = umbral, margen
        self.segundos, self.frames_minimos = segundos, frames_minimos
        self.segundos_repetir = segundos_repetir
        self.candidata: Optional[str] = None
        self.desde = 0.0       # cuándo empezó la racha de la candidata
        self.racha = 0         # frames seguidos de la candidata
        self.ultima: Optional[str] = None
        self.ultima_hora = 0.0

    def mano_perdida(self) -> None:
        self.candidata, self.racha, self.ultima = None, 0, None

    def actualizar(self, top: list, ahora: float) -> Optional[str]:
        """top = [(etiqueta, confianza), ...] ordenado; ahora = segundos (reloj monótono).

        Devuelve la letra si se acepta en este frame.
        """
        etiqueta = self._valida(top)
        if etiqueta is not None and etiqueta == self.candidata:
            self.racha += 1
        else:
            self.candidata, self.racha, self.desde = etiqueta, (1 if etiqueta is not None else 0), ahora

        # Se vio una seña válida distinta de la última aceptada: se vuelve a armar
        if etiqueta is not None and etiqueta != self.ultima:
            self.ultima = None

        if etiqueta is None or self.racha < self.frames_minimos or ahora - self.desde < self.segundos:
            return None
        if etiqueta == self.ultima and ahora - self.ultima_hora < self.segundos_repetir:
            return None
        self.ultima, self.ultima_hora = etiqueta, ahora
        return etiqueta

    def _valida(self, top: list) -> Optional[str]:
        if not top:
            return None
        mejor_etiqueta, mejor = top[0]
        if mejor < self.umbral:
            return None
        if len(top) > 1 and mejor - top[1][1] < self.margen:
            return None
        return mejor_etiqueta
