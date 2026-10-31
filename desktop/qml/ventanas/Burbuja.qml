import QtQuick
import QtQuick.Window
import QtQuick.Effects
import Lesco
import "../escritorio"

// La burbuja flotante (= el ícono de la app). Clic: abre LESCOCam.
// Se puede arrastrar. Clic derecho o Shift+F10: menú de la burbuja.
Window {
    id: ventana
    width: 84
    height: 100   // el disco y la etiqueta de estado, que cuelga debajo
    x: Screen.virtualX + Screen.desktopAvailableWidth - width - 22
    y: Screen.virtualY + 268
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint
    color: "transparent"
    title: "Burbuja de LESCOCam"
    visible: Nav.burbujaVisible && (Nav.esReposo(Nav.pantalla) || Nav.esChat(Nav.pantalla))
             && Nav.pantalla !== "01s" && !/^01h/.test(Nav.pantalla)

    Item {
        id: disco
        width: 64; height: 64
        x: 10; y: 6
        scale: zona.pressed ? 0.95 : zona.containsMouse ? 1.04 : 1
        Behavior on scale { NumberAnimation { duration: Tema.animRapida } }

        // Aro y etiqueta del estado. En el prototipo la burbuja siempre está
        // en reposo; el estado real vendrá del motor.
        EstadoBurbuja { anchors.fill: parent; estado: "reposo"; z: 1 }

        Image {
            id: icono
            anchors.fill: parent
            source: Qt.resolvedUrl("../../assets/imagenes/icono-app-redondo.png")
            sourceSize: Qt.size(128, 128)
            smooth: true
            visible: false
        }
        MultiEffect {
            anchors.fill: parent
            source: icono
            shadowEnabled: true
            shadowColor: Qt.rgba(10 / 255, 23 / 255, 51 / 255, 0.4)
            shadowVerticalOffset: 8
            shadowBlur: 0.6
        }
    }

    MouseArea {
        id: zona
        anchors.fill: disco
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: Qt.PointingHandCursor
        property point inicio
        property bool arrastrando: false
        onPressed: (m) => { inicio = Qt.point(m.x, m.y); arrastrando = false }
        onPositionChanged: (m) => {
            if (!pressed) return
            var dy = m.y - inicio.y
            if (Math.abs(dy) > 4) arrastrando = true
            if (arrastrando) ventana.y += dy     // la burbuja se mueve por el borde
        }
        onClicked: (m) => {
            if (arrastrando) return
            if (m.button === Qt.RightButton) Nav.abrir("Capa · Menú de la burbuja")
            else Nav.tocarBurbuja()
        }
    }
}
