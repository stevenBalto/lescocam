"""Reconocimiento de PALABRAS en vivo (modo "palabra"), aparte del deletreo.

El deletreo (core/reconocedor.Reconocedor: letras quietas y con movimiento) no
cambia. Este modo usa otro detector (core/cuerpo.DetectorCuerpo: dos manos +
pose) y otras plantillas (data/reference/senas.db). Una app elige el modo; los
dos no corren a la vez (el de palabras es más caro: ~30 ms por frame contra ~20).

Inicio y fin de una seña (core/palabras.Segmentador):
  - En REPOSO: los dos brazos descansan (muñeca por debajo del umbral de reposo de
    ese brazo, que desde la v3 es RELATIVO a cada persona y como mucho Y_REPOSO
    anchos de hombro bajo los hombros; o fuera de cuadro / no detectada).
  - Arranca cuando algún brazo sale del reposo T_ARRANQUE s seguidos (la seña
    guarda PREVIOS s de antes) y termina cuando los dos vuelven T_FIN s
    seguidos. Muy corta (< DURACION_MIN) o muy larga (> DURACION_MAX, p. ej.
    deletrear con la mano arriba) se descarta sin decir nada.
  - Sin cuerpo más de HUECO_MAX s corta la seña.
  - Entre señas SIN volver al reposo (frases encadenadas) todavía no se corta:
    ver "Siguiente paso" en el hilo de backend (pausa de la mano + ventana deslizante).

`actualizar(cuadro_cuerpo, ahora)` devuelve la palabra reconocida en este frame
(o None). Si la mejor no pasa umbral, margen relativo y control de duración no dice nada.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.cuerpo import CuadroCuerpo
from core.palabras import ComparadorPalabras, CuadroPalabra, Segmentador, cuadro_palabra, descriptores, duracion


class ReconocedorPalabras:
    def __init__(self, comparador: ComparadorPalabras, segmentador: Optional[Segmentador] = None, mano: str = "auto"):
        """mano: "auto" (prueba diestra y zurda en señas de dos manos), "derecha" o "izquierda"."""
        self.comparador = comparador
        self.segmentador = segmentador or Segmentador()
        self.mano = mano
        self.ultima: Optional[tuple] = None   # (palabra o None, confianza, top-5) de la última seña, para mostrar

    @classmethod
    def desde_db(cls, ruta: Path | str | None = None, mano: str = "auto") -> "ReconocedorPalabras":
        from core import senas_db
        return cls(senas_db.comparador(ruta or senas_db.RUTA_DB), mano=mano)

    @property
    def activo(self) -> bool:
        """Hay una seña en curso (para mostrarlo en la interfaz)."""
        return self.segmentador.activo

    def actualizar(self, cuerpo: Optional[CuadroCuerpo], ahora: float) -> Optional[str]:
        """cuerpo: lo que dio DetectorCuerpo en este frame (None si no se procesó)."""
        cuadro = cuadro_palabra(cuerpo) if cuerpo is not None else None
        if cuadro is not None:
            cuadro.t = ahora
        return self.actualizar_cuadro(cuadro, ahora)

    def actualizar_cuadro(self, cuadro: Optional[CuadroPalabra], ahora: float) -> Optional[str]:
        """Como actualizar() con el CuadroPalabra ya armado (pruebas y evaluación)."""
        sena = self.segmentador.actualizar(cuadro, ahora)
        return self._clasificar(sena) if sena else None

    def terminar(self) -> Optional[str]:
        sena = self.segmentador.terminar()
        return self._clasificar(sena) if sena else None

    def _clasificar(self, sena: list) -> Optional[str]:
        palabra, conf, top = self.comparador.clasificar(descriptores(sena, self.mano), duracion=duracion(sena))
        self.ultima = (palabra, conf, top)
        return palabra
