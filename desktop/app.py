"""Arranque de la interfaz de escritorio de LESCOCam (PySide6 + QML).

Por ahora la interfaz reproduce el prototipo de Figma: pantallas, capas y
navegación, con datos de ejemplo. El motor de `core/` se conecta más adelante.
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import parse_qs

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon, QImage, QPainter
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from desktop import iconos

RAIZ = Path(__file__).resolve().parent
QML = RAIZ / "qml"
ASSETS = RAIZ / "assets"


class ProveedorIconos(QQuickImageProvider):
    """Sirve `image://icono/<nombre>?color=%23RRGGBB` desde `iconos.py`."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, ident, size, requested):
        nombre, _, consulta = ident.partition("?")
        color = parse_qs(consulta).get("color", ["#0d2d6d"])[0]
        lado = max(requested.width(), requested.height(), 24)
        imagen = QImage(lado, lado, QImage.Format.Format_ARGB32_Premultiplied)
        imagen.fill(0)
        if nombre in iconos.DIBUJOS:
            pintor = QPainter(imagen)
            QSvgRenderer(iconos.svg(nombre, color)).render(pintor)
            pintor.end()
        if size is not None:
            size.setWidth(lado)
            size.setHeight(lado)
        return imagen


class Recargador(QObject):
    """En modo --dev vuelve a cargar el QML cada vez que se guarda un archivo."""

    cambio = Signal()

    def __init__(self):
        super().__init__()
        self._vigia = QFileSystemWatcher()
        self._pausa = QTimer(singleShot=True, interval=150)
        self._pausa.timeout.connect(self.cambio)
        self._vigia.fileChanged.connect(self._avisar)
        self._vigia.directoryChanged.connect(self._avisar)
        self._vigilar()

    def _vigilar(self):
        rutas = [str(p) for p in QML.rglob("*") if p.suffix in {".qml", ".js", ""}]
        if rutas:
            self._vigia.addPaths(rutas)

    @Slot()
    def _avisar(self, *_):
        self._vigilar()  # algunos editores reemplazan el archivo al guardar
        self._pausa.start()


class Aplicacion:
    def __init__(self, dev: bool, pantalla: str, oscuro: bool = False, escala: int = 0):
        self.dev = dev
        self.pantalla = pantalla
        self.oscuro = oscuro
        self.escala = escala
        self.motor = None

    def cargar(self):
        anterior = self.motor
        if anterior is not None:
            raiz = anterior.rootObjects()
            if raiz:
                self.pantalla = raiz[0].property("pantallaActual") or self.pantalla
            for objeto in raiz:
                objeto.deleteLater()
            anterior.deleteLater()

        motor = QQmlApplicationEngine()
        motor.warnings.connect(lambda avisos: [print(a.toString(), file=sys.stderr) for a in avisos])
        motor.addImageProvider("icono", ProveedorIconos())
        motor.addImportPath(str(QML))
        motor.setInitialProperties({
            "modoDev": self.dev,
            "pantallaInicial": self.pantalla,
            "oscuro": self.oscuro,
            "escala": self.escala,
            "assets": QUrl.fromLocalFile(str(ASSETS) + "/").toString(),
        })
        motor.load(QUrl.fromLocalFile(str(QML / "Main.qml")))
        if not motor.rootObjects():
            print("No se pudo cargar la interfaz (revisá los errores de QML arriba).", file=sys.stderr)
        self.motor = motor


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m desktop", description="Interfaz de escritorio de LESCOCam")
    parser.add_argument("--dev", action="store_true", help="modo desarrollo: recarga al guardar, chat de prueba y atajos para saltar de pantalla")
    parser.add_argument("--pantalla", default="", help="código de la pantalla inicial del prototipo, por ejemplo 02 o 13s")
    parser.add_argument("--captura", metavar="CARPETA", help="guarda un PNG de cada ventana visible y cierra (para comparar con Figma)")
    parser.add_argument("--oscuro", action="store_true", help="arrancar en modo oscuro")
    parser.add_argument("--escala", type=int, choices=(100, 125, 150), default=100, help="tamaño del texto en %%")
    args = parser.parse_args(argv)

    QGuiApplication.setApplicationName("LESCOCam")
    QGuiApplication.setOrganizationName("LESCOCam")
    app = QApplication(sys.argv[:1])  # QApplication: la bandeja de Windows la necesita
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(ASSETS / "imagenes" / "icono-app.png")))
    for fuente in (ASSETS / "fuentes").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(fuente))

    aplicacion = Aplicacion(args.dev, args.pantalla, args.oscuro, (100, 125, 150).index(args.escala))
    aplicacion.cargar()
    if args.dev:
        recargador = Recargador()
        recargador.cambio.connect(aplicacion.cargar)
    if args.captura:
        QTimer.singleShot(1500, lambda: _capturar(Path(args.captura), args.pantalla or "01"))
    return app.exec()


def _capturar(carpeta: Path, pantalla: str):
    carpeta.mkdir(parents=True, exist_ok=True)
    for ventana in QGuiApplication.topLevelWindows():
        if ventana.isVisible() and hasattr(ventana, "grabWindow"):
            nombre = ventana.title().replace(" ", "-").replace("·", "").replace("--", "-") or "ventana"
            ventana.grabWindow().save(str(carpeta / f"{pantalla}-{nombre}.png"))
    QGuiApplication.quit()
