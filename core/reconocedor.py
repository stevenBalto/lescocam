"""Un solo flujo de letras: quietas (clasificador + aceptador) y con movimiento (DTW).

Reglas para que no se pisen (medidas con scripts/evaluar_movimiento.py):

  - Una letra quieta aceptada mientras hay un gesto en curso (Segmentador.activo)
    que además se lee en alguna plantilla de movimiento (`posturas`: I, L, R, X,
    N, M... calculadas al cargar) no se dice enseguida: si el gesto resulta ser
    una letra con movimiento, era una postura intermedia y se descarta; si no
    (transición entre letras), se dice al terminar el gesto. Las demás letras se
    dicen como siempre.
  - Una letra quieta que es la POSTURA INICIAL de una letra con movimiento
    (L de LL, R de RR, N de Ñ, I de J, ...: `bases`, calculadas al cargar con el
    clasificador de quietas sobre el comienzo de cada plantilla) no se dice
    enseguida: queda pendiente ESPERA_BASE segundos más. Si en ese tiempo arranca
    un gesto y resulta ser la letra con movimiento, se dice solo esa (LL, no
    L + LL). Si el gesto no es ninguna letra, o la mano se queda quieta, o se va,
    se dice la letra quieta pendiente.
  - Después de una letra con movimiento, las quietas callan hasta que la mano
    vuelva a moverse, cambie de forma o se pierda: la postura final de LL (una L)
    no se dice como L, ni la de J como I.
  - Un temblor no arranca gestos (puntos suavizados + D_INICIO del Segmentador)
    y un gesto que no se parece a ninguna plantilla no dice nada.

Costo medido (video entero, signs.json de la app): las 18 letras que no son
bases ni posturas salen igual que antes; I, L, M, N, Q, R, X tardan 0.06-0.6 s
más (mediana de todas: 0.40 -> 0.50 s).

`actualizar(mano, ahora)` devuelve la lista de letras a decir en este frame
(casi siempre vacía; a lo sumo las pendientes y la de movimiento). Sin
movimientos.json (movimiento=None) se comporta igual que el Aceptador solo.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from core.aceptador import Aceptador
from core.movimiento import Cuadro, ReconocedorMovimiento, Segmentador, cuadro_de_mano
from core.rasgos import rasgos

ESPERA_BASE = 0.5          # segundos extra de una letra quieta que puede empezar un movimiento
V_BASE_QUIETA = 0.3        # y la mano tiene que estar de verdad quieta (manos/s): si ya empieza a moverse, espera
ESPERA_BASE_MAX = 1.0      # pero no más que esto (una mano que tiembla mucho no deja la letra colgada)
SEGUNDOS_BASE = 0.25       # comienzo de cada plantilla que define su postura inicial
CAMBIO_FORMA = 1.0         # distancia de rasgos que cuenta como "otra forma" (letras distintas: 1.3-3.3)


def bases_de_movimiento(clasificador, plantillas, aceptador: Optional[Aceptador] = None) -> dict:
    """letra con movimiento -> letras quietas que se leen claras al comienzo de su plantilla.

    Cuenta una letra si en los primeros SEGUNDOS_BASE de la plantilla pasa el
    umbral y el margen del aceptador; si ninguna pasa, la más parecida al primer cuadro.
    """
    a = aceptador or Aceptador()
    bases: dict[str, set] = {}
    if clasificador is None:
        return bases
    for etiqueta, cuadros in plantillas:
        if not cuadros:
            continue
        claras = set()
        for c in cuadros:
            if c.t - cuadros[0].t > SEGUNDOS_BASE:
                break
            letra = a._valida(clasificador.mejores(c.vector, 2))
            if letra is not None:
                claras.add(letra)
        if not claras:
            top = clasificador.mejores(cuadros[0].vector, 1)
            claras = {top[0][0]} if top else set()
        bases.setdefault(etiqueta, set()).update(claras)
    return bases


def posturas_de_movimiento(clasificador, plantillas, aceptador: Optional[Aceptador] = None) -> set:
    """Letras quietas que se leen claras en ALGÚN cuadro de alguna plantilla (posturas intermedias)."""
    a = aceptador or Aceptador()
    posturas = set()
    if clasificador is None:
        return posturas
    for _, cuadros in plantillas:
        for c in cuadros:
            letra = a._valida(clasificador.mejores(c.vector, 2))
            if letra is not None:
                posturas.add(letra)
    return posturas


class Reconocedor:
    def __init__(self, clasificador, aceptador: Optional[Aceptador] = None,
                 movimiento: Optional[ReconocedorMovimiento] = None, plantillas=(),
                 segmentador: Optional[Segmentador] = None, espera_base: float = ESPERA_BASE):
        """clasificador: core.clasificador.Clasificador de quietas (o None).
        movimiento: ReconocedorMovimiento (o None = solo letras quietas, como antes).
        plantillas: [(letra, [Cuadro])] de movimiento, para calcular las bases.
        """
        self.clasificador = clasificador
        self.aceptador = aceptador or Aceptador()
        self.movimiento = movimiento
        self.segmentador = segmentador or Segmentador()
        self.espera_base = espera_base
        self.bases = bases_de_movimiento(clasificador, plantillas, self.aceptador) if movimiento is not None else {}
        self._todas_bases = set().union(*self.bases.values()) if self.bases else set()
        self.posturas = (posturas_de_movimiento(clasificador, plantillas, self.aceptador) | self._todas_bases
                         if movimiento is not None else set())
        self.ultimo_gesto: Optional[tuple] = None    # (letra o None, top) del último gesto, para mostrar
        self._reiniciar()

    @classmethod
    def desde_archivos(cls, categoria: str = "letra") -> "Reconocedor":
        """Clasificador de signs.json + movimientos.json si existe (si no, solo quietas)."""
        from core.clasificador import Clasificador
        from core.movimiento import RUTA_MOVIMIENTOS, cuadros_de_toma, leer_movimientos
        clasificador = Clasificador(categoria=categoria)
        movimiento, plantillas = None, []
        try:
            movimiento = ReconocedorMovimiento(categoria=categoria)
            datos = leer_movimientos(RUTA_MOVIMIENTOS)
            plantillas = [(e, cuadros_de_toma(t)) for e, entrada in datos["signs"].items()
                          if entrada.get("categoria", "letra") == categoria for t in entrada.get("takes", [])]
        except (OSError, ValueError):
            movimiento = None
        return cls(clasificador, movimiento=movimiento, plantillas=plantillas)

    def _reiniciar(self) -> None:
        self._pendientes: list = []                  # [letra quieta, desde, aceptada durante un gesto]
        self._silencio: Optional[np.ndarray] = None # rasgos de la postura final del último movimiento

    # ------------------------------------------------------------------ frame a frame
    def mano_perdida(self, ahora: float) -> list[str]:
        return self.actualizar(None, ahora)

    def actualizar(self, mano, ahora: float) -> list[str]:
        """mano: core.camara.Mano (o None sin mano). Letras a decir en este frame."""
        cuadro = cuadro_de_mano(mano, ahora) if mano is not None else None
        vector = mano.vector if mano is not None else None
        return self.actualizar_cuadro(cuadro, vector, ahora)

    def actualizar_cuadro(self, cuadro: Optional[Cuadro], vector, ahora: float) -> list[str]:
        """Como actualizar() pero con el Cuadro ya armado (lo usan las pruebas y la evaluación).

        vector: el vector de 63 para las letras quietas (puede haber vector sin
        cuadro, p. ej. con la mano cortada por el borde de la imagen).
        """
        salida: list[str] = []
        seg = self.segmentador
        estaba_activo, estaba_moviendo = seg.activo, seg.moviendo
        gesto = seg.actualizar(cuadro, ahora) if self.movimiento is not None else None
        if seg.moviendo and not estaba_moviendo:
            self._silencio = None              # la mano se volvió a mover: las quietas vuelven
        if gesto is not None:
            salida += self._cerrar_gesto(gesto)
        elif estaba_activo and not seg.activo:
            salida += self._sin_gesto()        # era temblor, o el gesto fue muy corto o muy largo

        if vector is None:
            self.aceptador.mano_perdida()
            if not seg.activo:
                salida += self._soltar()
                self._silencio = None
            return salida

        top = self.clasificador.mejores(vector, 2) if self.clasificador is not None else []
        if self._silencio is not None:
            r = rasgos(vector)
            if r is not None and r.shape == self._silencio.shape and np.linalg.norm(r - self._silencio) > CAMBIO_FORMA:
                self._silencio = None
        letra = self.aceptador.actualizar(top, ahora)
        if letra is not None and self._silencio is None:
            if seg.activo and letra in self.posturas:   # postura de una letra con movimiento: se decide al terminar
                if not self._pendientes or self._pendientes[-1][0] != letra:
                    self._pendientes.append([letra, ahora, True])
            elif letra in self._todas_bases:   # puede ser el comienzo de una letra con movimiento
                salida += self._soltar()
                self._pendientes = [[letra, ahora, False]]
            else:
                salida += self._soltar()
                salida.append(letra)
        if len(self._pendientes) == 1 and not self._pendientes[0][2] and not seg.moviendo:
            espera = ahora - self._pendientes[0][1]
            if espera >= self.espera_base and ((not seg.activo and seg.velocidad < V_BASE_QUIETA)
                                               or espera >= ESPERA_BASE_MAX):
                salida += self._soltar()
        return salida

    # ------------------------------------------------------------------ internos
    def _soltar(self) -> list[str]:
        letras = [p[0] for p in self._pendientes]
        self._pendientes = []
        return letras

    def _sin_gesto(self) -> list[str]:
        """El candidato o el gesto se descartó: lo aceptado mientras tanto se dice; una base sola sigue esperando."""
        if any(p[2] for p in self._pendientes):
            return self._soltar()
        return []

    def _cerrar_gesto(self, gesto: list) -> list[str]:
        top = self.movimiento.mejores(gesto, 2)
        letra, _ = self.movimiento.clasificar(gesto)
        self.ultimo_gesto = (letra, top)
        if letra is None:
            return self._soltar()
        # Las posturas de dentro del gesto y su postura inicial son parte de la letra con movimiento.
        salida = [p[0] for p in self._pendientes if not p[2] and p[0] not in self.bases.get(letra, ())]
        self._pendientes = []
        salida.append(letra)
        final = rasgos(gesto[-1].vector)
        self._silencio = final if final is not None else np.zeros(0)   # sin rasgos: calla hasta moverse
        self.aceptador.mano_perdida()
        return salida
