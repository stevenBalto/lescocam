"""Puente entre el motor de `core/` y la interfaz QML.

`Motor` se expone a QML como `motor`. Los componentes `Camara` piden la cámara
al hacerse visibles y la sueltan al ocultarse; la cámara solo está abierta
mientras alguien la pide. Cada frame (ya con la mano dibujada) se sirve en
`image://camara/frame?<n>`. También maneja la voz del sistema y los ajustes
que se guardan en el equipo (voz, velocidad, cámara, espejo, puntos, pausa).
"""

import os
import sys
import threading

from PySide6.QtCore import Property, QObject, QSettings, QThread, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

from desktop.locutor import Locutor

# Escala de Qt: en Windows lo positivo acelera mucho más que lo negativo frena
# (+0,5 ya es unas 3,5 veces más rápido y se oye entrecortado). Medido con la voz Sabina:
# Lenta ≈ 0,8× · Normal 1× · Rápida ≈ 1,3×.
VELOCIDADES = {"Lenta": -0.4, "Normal": 0.0, "Rápida": 0.07}
SEGUNDOS_SIN_MANOS = 3
# Modo (ajuste `modo`, se elige en Ajustes › Cámara):
#   "letras"   deletreo con una mano (core/reconocedor) → `letraReconocida`
#   "palabras" dos manos + pose (core/cuerpo.DetectorCuerpo) y palabras completas
#              de data/reference/senas.db (core/reconocedor_palabras) → `palabraReconocida`
# LESCOCAM_MODO=palabras|letras fuerza el modo al arrancar (para probar sin tocar el ajuste).
MODO_LETRAS = "letras"
MODO_PALABRAS = "palabras"
MODOS = (MODO_LETRAS, MODO_PALABRAS)


def texto_palabra(etiqueta: str) -> str:
    """Etiqueta del diccionario → texto para escribir: «POR-FAVOR» → «por favor»,
    «TIERRA(PLANETA)» → «tierra», «INFORMAR-2» → «informar»."""
    import re
    texto = re.sub(r"\(.*?\)", "", etiqueta)
    texto = re.sub(r"-\d+$", "", texto.strip())
    return texto.replace("-", " ").strip().lower()


class _Punto:
    """Punto x, y (normalizado) para dibujar las manos del modo palabra con camara.dibujar_mano."""
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)


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
    palabraReconocida = Signal(str)
    sinManos = Signal()
    nivelLuzCambio = Signal()
    simulacionLuzCambio = Signal()
    primerUsoVistoCambio = Signal()
    ajusteCambio = Signal()
    # Órdenes al hilo de la voz (se entregan en cola, sin bloquear la interfaz)
    _iniciar_voz = Signal(str, float)
    _configurar_voz = Signal(str, float)
    _decir = Signal(str, bool)
    _parar_voz = Signal()

    def __init__(self, camara_permitida: bool = True):
        super().__init__()
        self._permitida = camara_permitida
        # Con la cámara apagada (pruebas) los ajustes no se leen ni se guardan en el equipo
        self._ajustes = QSettings("LESCOCam", "LESCOCam") if camara_permitida else None
        self._pedidos = 0
        self._hilo = None
        self._parar = threading.Event()
        self._candado = threading.Lock()
        self._frame = QImage()
        self._n = 0
        self._hay_video = False
        self._mano = False
        self._nivel_luz = "buena"   # "buena" | "regular" | "baja" (ver core/mejora_luz.MedidorLuz)
        self._sim_luz = "normal"    # simulación de luz para pruebas (solo --dev); no se guarda
        self._error = ""
        self._hilo_voz = None
        self._locutor = None
        self._nombres_voces = []
        self._hablando = False
        self._voz = self._leer("voz", "")
        self._velocidad = self._leer("velocidad", "Normal")
        self._espejo = self._leer("espejo", True)
        self._puntos = self._leer("puntosMano", True)
        self._pausar = self._leer("pausarSinManos", True)
        self._camara = self._leer("camara", "")
        # El asistente de primer uso se muestra una sola vez; se puede volver a ver
        # desde Ajustes › Acerca de. Se guarda en el equipo para no repetirlo en cada arranque.
        self._primer_uso_visto = self._leer("primerUsoVisto", False)
        modo = os.environ.get("LESCOCAM_MODO") or self._leer("modo", MODO_LETRAS)
        self._modo = modo if modo in MODOS else MODO_LETRAS

    # --- Ajustes guardados ----------------------------------------------------
    def _leer(self, clave, defecto):
        if self._ajustes is None:
            return defecto
        valor = self._ajustes.value(clave, defecto)
        if isinstance(defecto, bool):
            return valor in (True, "true", "1", 1)
        return str(valor)

    def _guardar(self, clave, valor):
        if self._ajustes is not None:
            self._ajustes.setValue(clave, valor)
        self.ajusteCambio.emit()

    @Property(bool, notify=ajusteCambio)
    def espejo(self):
        return self._espejo

    @espejo.setter
    def espejo(self, v):
        self._espejo = bool(v)
        self._guardar("espejo", self._espejo)

    @Property(bool, notify=ajusteCambio)
    def puntosMano(self):
        return self._puntos

    @puntosMano.setter
    def puntosMano(self, v):
        self._puntos = bool(v)
        self._guardar("puntosMano", self._puntos)

    @Property(bool, notify=ajusteCambio)
    def pausarSinManos(self):
        return self._pausar

    @pausarSinManos.setter
    def pausarSinManos(self, v):
        self._pausar = bool(v)
        self._guardar("pausarSinManos", self._pausar)

    @Property(str, notify=ajusteCambio)
    def modo(self):
        return self._modo

    @Slot(str)
    def elegirModo(self, nombre):
        if nombre in MODOS and nombre != self._modo:
            self._modo = nombre
            self._guardar("modo", nombre)
            if self._hilo is not None:   # la cámara estaba abierta: se reabre con el otro detector
                self.detener_camara()
                self._arrancar()

    # --- Estado para QML ------------------------------------------------------
    @Property(bool, notify=hayVideoCambio)
    def hayVideo(self):
        return self._hay_video

    @Property(bool, notify=manoCambio)
    def hayMano(self):
        return self._mano

    @Property(str, notify=nivelLuzCambio)
    def nivelLuz(self):
        """Luz en la zona de la mano: "buena" (no se toca), "regular" (se mejora la
        imagen automáticamente) o "baja" (ni con la mejora se detecta: pedir más luz)."""
        return self._nivel_luz

    @Property(str, notify=simulacionLuzCambio)
    def simulacionLuz(self):
        """Condición de luz simulada sobre la cámara (pruebas): "normal", "poca_luz_1..3"
        o "contraluz_1..3". Ver core/mejora_luz.CONDICIONES_LUZ."""
        return self._sim_luz

    @Slot(str)
    def simularLuz(self, condicion):
        from core.mejora_luz import CONDICIONES_LUZ
        condicion = condicion if condicion in CONDICIONES_LUZ else "normal"
        if condicion != self._sim_luz:
            self._sim_luz = condicion
            self.simulacionLuzCambio.emit()

    @Property(str, notify=errorCambio)
    def errorCamara(self):
        return self._error

    @Property(bool, notify=hablandoCambio)
    def hablando(self):
        return self._hablando

    @Property(bool, notify=primerUsoVistoCambio)
    def primerUsoVisto(self):
        return self._primer_uso_visto

    @Slot()
    def marcarPrimerUsoVisto(self):
        """Lo llama la interfaz al terminar el primer uso: no se vuelve a mostrar solo."""
        if not self._primer_uso_visto:
            self._primer_uso_visto = True
            self._guardar("primerUsoVisto", True)
            self.primerUsoVistoCambio.emit()

    def ultimo_frame(self) -> QImage:
        with self._candado:
            return self._frame

    # --- Voz (síntesis del sistema, en un hilo propio: ver locutor.py) ---------
    def _arrancar_voz(self):
        if self._hilo_voz is not None or not self._permitida:
            return
        self._locutor = Locutor()
        self._hilo_voz = QThread()
        self._locutor.moveToThread(self._hilo_voz)
        self._locutor.vocesListas.connect(self._al_tener_voces)
        self._locutor.ocupadoCambio.connect(self._cambiar_hablando)
        self._locutor.fallo.connect(self._publicar_error_voz)
        self._decir.connect(self._locutor.decir)
        self._parar_voz.connect(self._locutor.parar)
        self._configurar_voz.connect(self._locutor.configurar)
        self._hilo_voz.started.connect(lambda: self._iniciar_voz.emit(self._voz, VELOCIDADES[self._velocidad]))
        self._iniciar_voz.connect(self._locutor.iniciar)
        self._hilo_voz.start()

    def _al_tener_voces(self, nombres):
        self._nombres_voces = list(nombres)
        if self._voz not in self._nombres_voces and self._nombres_voces:
            self._voz = self._nombres_voces[0]
        self.ajusteCambio.emit()

    def _publicar_error_voz(self, texto):
        print(f"Voz: {texto}", file=sys.stderr)

    @Property("QStringList", notify=ajusteCambio)
    def voces(self):
        self._arrancar_voz()
        return self._nombres_voces

    @Property(str, notify=ajusteCambio)
    def voz(self):
        self._arrancar_voz()
        return self._voz

    @Slot(str)
    def elegirVoz(self, nombre):
        if nombre in self._nombres_voces:
            self._voz = nombre
            self._configurar_voz.emit(self._voz, VELOCIDADES[self._velocidad])
            self._guardar("voz", nombre)

    @Property(str, notify=ajusteCambio)
    def velocidad(self):
        return self._velocidad

    @Slot(str)
    def elegirVelocidad(self, nombre):
        if nombre in VELOCIDADES:
            self._velocidad = nombre
            self._configurar_voz.emit(self._voz, VELOCIDADES[nombre])
            self._guardar("velocidad", nombre)

    @Slot(str)
    def hablar(self, texto):
        """Lee el texto en voz alta; si ya hablaba, corta y empieza con este."""
        texto = (texto or "").strip()
        if texto:
            self._arrancar_voz()
            self._decir.emit(texto, True)

    @Slot(str)
    def hablarEnCola(self, texto):
        """Lee el texto al terminar lo que ya suena (para decir palabra por palabra)."""
        texto = (texto or "").strip()
        if texto:
            self._arrancar_voz()
            self._decir.emit(texto, False)

    @Slot()
    def detenerVoz(self):
        self._parar_voz.emit()

    def _cambiar_hablando(self, valor: bool):
        if valor != self._hablando:
            self._hablando = valor
            self.hablandoCambio.emit()

    # --- Cámaras --------------------------------------------------------------
    @Property("QStringList", notify=ajusteCambio)
    def camaras(self):
        from PySide6.QtMultimedia import QMediaDevices
        return [c.description() for c in QMediaDevices.videoInputs()]

    @Property(str, notify=ajusteCambio)
    def camara(self):
        nombres = self.camaras
        return self._camara if self._camara in nombres else (nombres[0] if nombres else "")

    @Slot(str)
    def elegirCamara(self, nombre):
        if nombre in self.camaras and nombre != self.camara:
            self._camara = nombre
            self._guardar("camara", nombre)
            if self._hilo is not None:   # la cámara estaba abierta: se reabre con la nueva
                self.detener_camara()
                self._arrancar()

    def _indice_camara(self) -> int:
        nombres = self.camaras
        return nombres.index(self.camara) if self.camara in nombres else 0

    # --- Cámara bajo demanda --------------------------------------------------
    @Slot()
    def pedirCamara(self):
        self._pedidos += 1
        self._arrancar()

    def _arrancar(self):
        if self._permitida and self._hilo is None and self._pedidos > 0:
            self._parar.clear()
            self._hilo = threading.Thread(target=self._bucle, args=(self._indice_camara(),), daemon=True)
            self._hilo.start()

    @Slot()
    def soltarCamara(self):
        self._pedidos = max(0, self._pedidos - 1)
        if self._pedidos == 0:
            self.detener_camara()

    def detener_camara(self):
        hilo, self._hilo = self._hilo, None
        if hilo is not None:
            self._parar.set()
            hilo.join(timeout=3)

    def detener(self):
        if self._hilo_voz is not None:
            self._parar_voz.emit()
            self._hilo_voz.quit()
            self._hilo_voz.wait(2000)
            self._hilo_voz = None
        self.detener_camara()

    def _bucle(self, indice: int):
        # Se importa acá para que la interfaz arranque aunque falte MediaPipe/OpenCV.
        try:
            import time

            import cv2
            from core import camara
            from core.mejora_luz import MedidorLuz, simular_luz
            from core.reconocedor import Reconocedor
            cap = camara.abrir_camara(indice)
            palabras = None
            if self._modo == MODO_PALABRAS:
                from core.cuerpo import DetectorCuerpo
                from core.reconocedor_palabras import ReconocedorPalabras
                detector = DetectorCuerpo(recorte=True)   # busca de cerca la mano que falte (problema 3)
                palabras = ReconocedorPalabras.desde_db()
            else:
                detector = camara.Detector()
        except Exception as e:  # sin cámara, permiso denegado o falta de librerías
            self._publicar_error(f"No se pudo abrir la cámara: {e}")
            return
        self._publicar_error("")
        try:   # sin signs.json válido la cámara funciona igual, solo que sin reconocer
            reconocedor = Reconocedor.desde_archivos() if palabras is None else None   # quietas + movimiento
        except (OSError, ValueError):
            reconocedor = None
        ultima_mano = time.monotonic()
        avisado = False
        medidor = MedidorLuz()
        try:
            while not self._parar.is_set():
                # Siempre se detecta con la imagen espejada: así «izquierda/derecha» es la mano real.
                frame = camara.leer_espejado(cap)
                if frame is None:
                    self._publicar_error("La cámara dejó de responder")
                    break
                ahora = time.monotonic()
                # Simulación de luz para pruebas (solo --dev; "normal" no toca nada):
                # degrada la cámara como el banco de luz, para probar el medidor desde la PC.
                if self._sim_luz != "normal":
                    frame = simular_luz(frame, self._sim_luz)
                # Mejora de luz automática según el brillo: en poca luz aclara la imagen
                # ANTES de detectar (y es la que se muestra). En luz buena no toca nada.
                # El nivel es continuo y se recupera solo. Ver core/mejora_luz.MedidorLuz.
                frame, nivel_luz, _pedir_luz, _ = medidor.antes_de_detectar(frame)
                if palabras is not None:
                    cuerpo = detector.procesar(frame, ahora)
                    palabra = palabras.actualizar(cuerpo, ahora)
                    if palabra:
                        self.palabraReconocida.emit(texto_palabra(palabra))
                    manos = [camara.Mano([_Punto(*p[:2]) for p in pts], lado, None, cuerpo.frame)
                             for pts, lado, _ in cuerpo.manos]
                    # Entre señas los brazos descansan abajo (a veces fuera de cuadro):
                    # con el cuerpo a la vista no se pausa.
                    presente = bool(manos) or cuerpo.pose is not None
                else:
                    mano = detector.procesar(frame)
                    manos = [mano] if mano is not None else []
                    presente = bool(manos)
                if presente:
                    ultima_mano, avisado = ahora, False
                if manos and self._puntos:
                    for m in manos:
                        camara.dibujar_mano(frame, m)
                if not presente and self._pausar and not avisado and ahora - ultima_mano > SEGUNDOS_SIN_MANOS:
                    avisado = True
                    self.sinManos.emit()
                if reconocedor is not None:
                    for letra in reconocedor.actualizar(mano, ahora):
                        self.letraReconocida.emit(letra)
                if not self._espejo:
                    frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                alto, ancho = rgb.shape[:2]
                imagen = QImage(rgb.data, ancho, alto, ancho * 3, QImage.Format.Format_RGB888).copy()
                with self._candado:
                    self._frame = imagen
                    self._n += 1
                    n = self._n
                self._cambiar_estado(bool(manos))
                self._cambiar_nivel_luz(nivel_luz)
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

    def _cambiar_nivel_luz(self, nivel: str):
        if nivel != self._nivel_luz:
            self._nivel_luz = nivel
            self.nivelLuzCambio.emit()

    def _publicar_error(self, texto: str):
        if texto != self._error:
            self._error = texto
            self.errorCambio.emit()
