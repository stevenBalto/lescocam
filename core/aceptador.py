"""Acepta una letra solo si es estable: umbral + margen + N frames seguidos."""
from __future__ import annotations

from typing import Optional

SEGUNDOS_REPETIR = 1.5


class Aceptador:
    def __init__(self, umbral: float = 0.92, margen: float = 0.02, frames: int = 10,
                 segundos_repetir: float = SEGUNDOS_REPETIR):
        self.umbral, self.margen, self.frames = umbral, margen, frames
        self.segundos_repetir = segundos_repetir
        self.candidata: Optional[str] = None
        self.racha = 0
        self.ultima: Optional[str] = None
        self.ultima_hora = 0.0

    def mano_perdida(self) -> None:
        self.candidata, self.racha, self.ultima = None, 0, None

    def actualizar(self, top: list, ahora: float) -> Optional[str]:
        """top = [(etiqueta, sim), ...] ordenado. Devuelve la letra si se acepta en este frame."""
        etiqueta = self._valida(top)
        if etiqueta is not None and etiqueta == self.candidata:
            self.racha += 1
        else:
            self.candidata, self.racha = etiqueta, (1 if etiqueta is not None else 0)

        # Se vio una seña válida distinta de la última aceptada: se vuelve a armar
        if etiqueta is not None and etiqueta != self.ultima:
            self.ultima = None

        if etiqueta is None or self.racha < self.frames:
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
