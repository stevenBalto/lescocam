import QtQuick
import QtQuick.Window
import Lesco
import "../componentes"

// Ventanas grandes que se abren encima (overlay en Figma): 12 Historial,
// 13 Diccionario, 14 Práctica y 15 Ajustes. Centradas en la pantalla.
// El tamaño lo da el contenido (implicitWidth / implicitHeight).
Window {
    id: ventana
    readonly property string codigo: Nav.esVentana(Nav.capa) ? Nav.capa
                                   : Nav.esVentana(Nav.pantalla) ? Nav.pantalla : ""
    width: contenido.implicitWidth
    height: contenido.implicitHeight
    x: Screen.virtualX + (Screen.desktopAvailableWidth - width) / 2
    y: Screen.virtualY + (Screen.desktopAvailableHeight - height) / 2
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "transparent"
    title: "LESCOCam · " + codigo
    visible: codigo !== ""

    Cargador {
        id: contenido
        anchors.fill: parent
        codigo: ventana.codigo
        archivo: {
            var c = ventana.codigo
            if (/^12/.test(c)) return "../ventana/Historial.qml"
            if (/^13/.test(c)) return "../ventana/Diccionario.qml"
            if (/^14/.test(c)) return "../ventana/Practica.qml"
            if (/^15/.test(c)) return "../ventana/Ajustes.qml"
            return ""
        }
    }

    Shortcut { sequence: "Esc"; onActivated: Nav.pulsarEscape() }
}
