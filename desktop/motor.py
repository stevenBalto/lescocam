"""Puente entre el motor de `core/` y la interfaz QML.

`Motor` se expone a QML como `motor`. Los componentes `Camara` piden la cámara
al hacerse visibles y la sueltan al ocultarse; la cámara solo está abierta
mientras alguien la pide. Cada frame (ya con la mano dibujada) se sirve en
`image://camara/frame?<n>`.
"""

import threading

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class ProveedorCamara(QQuickImageProvider):
    """Sirve `image://camara/frame?<n>` con el último frame de la cámara."""

    def __init__(self, motor: "Motor"):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._motor = motor

    def requestImage(self, ident, size, requested):
        imagen = self._motor.ultimo_frame()
        if imagen.isNull():
            imagen = QImage(2, 2, QImage.Format.Format_RGB32)
            imagen.fill(0)
        if size is not None:
            size.setWidth(imagen.width())
            size.setHeight(imagen.height())
        return imagen


class Motor(QObject):
    frameNuevo = Signal(int)
    hayVideoCambio = Signal()
    manoCambio = Signal()
    errorCambio = Signal()
    hablandoCambio = Signal()
    letraReconocida = Signal(str)

    def __init__(self, camara_permitida: bool = True):
        super().__init__()
        self._permitida = camara_permitida
        self._pedidos = 0
        self._hilo = None
        self._parar = threading.Event()
        self._candado = threading.Lock()
        self._frame = QImage()
        self._n = 0
        self._hay_video = False
        self._mano = False
        self._error = ""
        self._voz = None
        self._hablando = False

    # --- Propiedades para QML -------------------------------------------------
    @Property(bool, notify=hayVideoCambio)
    def hayVideo(self):
        return self._hay_video

    @Property(bool, notify=manoCambio)
    def hayMano(self):
        return self._mano

    @Property(str, notify=errorCambio)
    def errorCamara(self):
        return self._error

    @Property(bool, notify=hablandoCambio)
    def hablando(self):
        return self._hablando

    def ultimo_frame(self) -> QImage:
        with self._candado:
            return self._frame

    # --- Voz (TTS del sistema) ------------------------------------------------
    @Slot(str)
    def hablar(self, texto):
        """Lee el texto en voz alta, en español si el sistema tiene una voz."""
        if self._voz is None:
            from core.voz import Voz
            self._voz = Voz(al_hablar=self._cambiar_hablando)
        self._voz.parar()
        self._voz.hablar(texto)

    @Slot()
    def detenerVoz(self):
        if self._voz is not None:
            self._voz.parar()
            self._cambiar_hablando(False)

    def _cambiar_hablando(self, valor: bool):
        if valor != self._hablando:
            self._hablando = valor
            self.hablandoCambio.emit()

    # --- Cámara bajo demanda --------------------------------------------------
    @Slot()
    def pedirCamara(self):
        self._pedidos += 1
        if self._permitida and self._hilo is None:
            self._parar.clear()
            self._hilo = threading.Thread(target=self._bucle, daemon=True)
            self._hilo.start()

    @Slot()
    def soltarCamara(self):
        self._pedidos = max(0, self._pedidos - 1)
        if self._pedidos == 0:
            self.detener()

    def detener(self):
        if self._voz is not None:
            self._voz.cerrar()
            self._voz = None
        hilo, self._hilo = self._hilo, None
        if hilo is not None:
            self._parar.set()
            hilo.join(timeout=3)

    def _bucle(self):
        # Se importa acá para que la interfaz arranque aunque falte MediaPipe/OpenCV.
        try:
            import time

            import cv2
            from core import camara
            from core.aceptador import Aceptador
            from core.clasificador import Clasificador
            cap = camara.abrir_camara()
            detector = camara.Detector()
        except Exception as e:  # sin cámara, permiso denegado o falta de librerías
            self._publicar_error(f"No se pudo abrir la cámara: {e}")
            return
        self._publicar_error("")
        try:   # sin signs.json válido la cámara funciona igual, solo que sin reconocer
            clasificador, aceptador = Clasificador(), Aceptador()
        except (OSError, ValueError):
            clasificador = aceptador = None
        try:
            while not self._parar.is_set():
                frame = camara.leer_espejado(cap)
                if frame is None:
                    self._publicar_error("La cámara dejó de responder")
                    break
                mano = detector.procesar(frame)
                if mano is not None:
                    camara.dibujar_mano(frame, mano)
                if clasificador is not None:
                    if mano is None or mano.vector is None:
                        aceptador.mano_perdida()
                    else:
                        top = clasificador.mejores(mano.vector, 2)
                        letra = aceptador.actualizar(top, time.monotonic())
                        if letra is not None:
                            self.letraReconocida.emit(letra)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                alto, ancho = rgb.shape[:2]
                imagen = QImage(rgb.data, ancho, alto, ancho * 3, QImage.Format.Format_RGB888).copy()
                with self._candado:
                    self._frame = imagen
                    self._n += 1
                    n = self._n
                self._cambiar_estado(mano is not None)
                self.frameNuevo.emit(n)
        finally:
            cap.release()
            detector.cerrar()
            with self._candado:
                self._frame = QImage()
            self._cambiar_estado(False, video=False)

    def _cambiar_estado(self, mano: bool, video: bool = True):
        if video != self._hay_video:
            self._hay_video = video
            self.hayVideoCambio.emit()
        if mano != self._mano:
            self._mano = mano
            self.manoCambio.emit()

    def _publicar_error(self, texto: str):
        if texto != self._error:
            self._error = texto
            self.errorCambio.emit()
