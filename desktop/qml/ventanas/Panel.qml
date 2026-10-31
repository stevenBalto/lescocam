import QtQuick
import QtQuick.Window
import Lesco
import "../componentes"
import "../panel"

// La «tira» de LESCOCam: ventana de 400 px pegada al borde derecho, siempre
// encima de las demás apps. Muestra las pantallas 00–03, 07–09 y 16–21.
Window {
    id: ventana
    width: 400
    height: Screen.desktopAvailableHeight
    x: Screen.virtualX + Screen.desktopAvailableWidth - width
    y: Screen.virtualY
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: Tema.fondoPanel
    title: "LESCOCam"
    visible: Nav.esPanel(Nav.pantalla)

    readonly property string modo: /^(07|08|09)/.test(Nav.pantalla) ? "hablar" : "escribir"

    // Sombra hacia la izquierda (-10, 0, 28) dibujada como degradado
    Rectangle {
        width: 12; height: parent.height
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.10) }
            GradientStop { position: 1; color: "transparent" }
        }
        z: 10
    }

    Rectangle { id: banda; width: parent.width; height: 125; color: Tema.fondoBanda }

    Column {
        anchors.fill: parent

        CabeceraPanel {
            width: parent.width
            modo: ventana.modo
        }

        // Un archivo por grupo de pantallas; cada uno resuelve sus variantes
        // leyendo Nav.pantalla.
        Cargador {
            width: parent.width
            height: parent.height - y
            codigo: Nav.pantalla
            archivo: {
                var c = Nav.pantalla
                if (/^00/.test(c)) return "../panel/Inicio.qml"          // animación de inicio
                if (/^0[23]/.test(c)) return "../panel/Escribir.qml"     // A · Escribir
                if (/^0[789]/.test(c)) return "../panel/Hablar.qml"      // B · Hablar
                if (/^(1[6-9]|2[01])/.test(c)) return "../panel/Estados.qml" // D · Estados y errores
                return ""
            }
        }
    }

    Shortcut { sequence: "Esc"; onActivated: Nav.pulsarEscape() }
}
