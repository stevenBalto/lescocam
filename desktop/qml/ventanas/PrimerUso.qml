import QtQuick
import QtQuick.Window
import Lesco
import "../componentes"

// E · Primer uso (pantallas 22–26): asistente centrado en la pantalla.
Window {
    id: ventana
    width: contenido.implicitWidth
    height: contenido.implicitHeight
    x: Screen.virtualX + (Screen.desktopAvailableWidth - width) / 2
    y: Screen.virtualY + (Screen.desktopAvailableHeight - height) / 2
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "transparent"
    title: "LESCOCam · Primer uso"
    visible: Nav.esPrimerUso(Nav.pantalla)

    Cargador {
        id: contenido
        anchors.fill: parent
        codigo: Nav.pantalla
        archivo: ventana.visible ? "../primeruso/PrimerUso.qml" : ""
    }
}
