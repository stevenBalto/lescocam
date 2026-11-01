"""Voz del sistema en un hilo propio (Qt Text-to-Speech).

Vive fuera del hilo de la interfaz: crear la voz y cambiarla tarda hasta un
par de segundos en Windows y congelaba la ventana. Además ordena el trabajo:

- nunca se llama a `say` mientras algo suena (primero se corta y se espera a
  que el motor avise que quedó libre), así no se mezclan ni se cortan frases;
- la voz y la velocidad solo se cambian con el motor libre;
- `ocupado` no parpadea al interrumpir una frase con otra;
- si el motor de voz no responde, un vigilante lo destraba.
"""

import os

from PySide6.QtCore import QLocale, QObject, QTimer, Signal, Slot

SEGUNDOS_PARA_EMPEZAR = 4000   # ms: si `say` no llega a «Speaking» en este tiempo, se da por perdida
SEGUNDOS_PARA_CORTAR = 1500    # ms: si `stop` no llega a «Ready» en este tiempo, se destraba


class Locutor(QObject):
    vocesListas = Signal(list)      # nombres de las voces en español
    ocupadoCambio = Signal(bool)    # hay algo sonando o por sonar
    fallo = Signal(str)

    def __init__(self):
        super().__init__()
        self._tts = None
        self._voces = {}
        self._cola = []
        self._voz = ""
        self._velocidad = 0.0
        self._aplicado = None
        self._diciendo = False      # se llamó a say y el motor todavía no avisó que terminó
        self._ocupado = False
        self._vigilante = None

    @Slot(str, float)
    def iniciar(self, voz: str, velocidad: float):
        """Crea la voz (ya dentro del hilo) y avisa qué voces en español hay."""
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech
        except ImportError as e:
            self.fallo.emit(f"Audio no disponible ({type(e).__name__})")
            return
        self._estados = QTextToSpeech.State
        motor = os.environ.get("LESCOCAM_TTS", "")   # «sapi» o «winrt»; vacío = el de Qt
        self._tts = QTextToSpeech(motor, self) if motor in QTextToSpeech.availableEngines() else QTextToSpeech(self)
        self._tts.stateChanged.connect(self._al_cambiar_estado)
        self._tts.errorOccurred.connect(lambda codigo, texto: self._al_fallar(texto))
        self._vigilante = QTimer(self)
        self._vigilante.setSingleShot(True)
        self._vigilante.timeout.connect(self._destrabar)
        actual = self._tts.locale()
        for loc in self._tts.availableLocales():
            if loc.language() == QLocale.Language.Spanish:
                self._tts.setLocale(loc)
                for v in self._tts.availableVoices():
                    self._voces[v.name().replace("Microsoft ", "")] = v
        self._tts.setLocale(actual)
        self._voz, self._velocidad = voz, velocidad
        if self._voz not in self._voces and self._voces:
            self._voz = next(iter(self._voces))
        self.vocesListas.emit(list(self._voces))
        self._siguiente()

    @Slot(str, float)
    def configurar(self, voz: str, velocidad: float):
        self._voz, self._velocidad = voz, velocidad   # se aplica antes de la próxima frase

    @Slot(str, bool)
    def decir(self, texto: str, interrumpir: bool):
        if interrumpir:
            self._cola = [texto]
        else:
            self._cola.append(texto)
        if self._tts is None:   # la voz todavía arranca: queda en la cola y suena al terminar de iniciar
            return
        if interrumpir:
            if self._diciendo:
                self._tts.stop()
                self._vigilar(SEGUNDOS_PARA_CORTAR)
                self._marcar()
                return
        if not self._diciendo:
            self._siguiente()
        self._marcar()

    @Slot()
    def parar(self):
        self._cola = []
        if self._tts is not None and self._diciendo:
            self._tts.stop()
            self._vigilar(SEGUNDOS_PARA_CORTAR)
        self._marcar()

    # --- Interno --------------------------------------------------------------
    def _siguiente(self):
        if self._diciendo or self._tts is None:
            return
        if not self._cola:
            self._marcar()
            return
        if (self._voz, self._velocidad) != self._aplicado:
            voz = self._voces.get(self._voz)
            if voz is not None:
                self._tts.setLocale(voz.locale())
                self._tts.setVoice(voz)
            self._tts.setRate(self._velocidad)
            self._aplicado = (self._voz, self._velocidad)
        texto = self._cola.pop(0)
        self._diciendo = True
        self._tts.say(texto)
        self._vigilar(SEGUNDOS_PARA_EMPEZAR)
        self._marcar()

    def _al_cambiar_estado(self, estado):
        if estado == self._estados.Speaking:
            if self._vigilante is not None:
                self._vigilante.stop()
        elif estado == self._estados.Ready and self._diciendo:
            self._diciendo = False
            if self._vigilante is not None:
                self._vigilante.stop()
            self._siguiente()
            self._marcar()

    def _al_fallar(self, texto: str):
        self.fallo.emit(texto or "Error de audio")
        self._destrabar()

    def _vigilar(self, ms: int):
        if self._vigilante is not None:
            self._vigilante.start(ms)

    def _destrabar(self):
        """El motor no avisó a tiempo: se da la frase por terminada y se sigue con la cola."""
        if self._tts is not None and self._tts.state() == self._estados.Speaking:
            self._vigilar(SEGUNDOS_PARA_EMPEZAR)   # sigue sonando: no era un bloqueo
            return
        self._diciendo = False
        self._siguiente()
        self._marcar()

    def _marcar(self):
        ocupado = self._diciendo or bool(self._cola)
        if ocupado != self._ocupado:
            self._ocupado = ocupado
            self.ocupadoCambio.emit(ocupado)
