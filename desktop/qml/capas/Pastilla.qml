import QtQuick
import Lesco
import "../componentes"

// Botón en pastilla de «Lo último» (Pegar, Reproducir): fondo de chip,
// texto ExtraBold de 13 px y, si hace falta, un ícono delante.
Item {
    id: pastilla
    property string texto
    property string icono
    property color colorIcono: Tema.acentoNaranja
    signal clic()

    implicitWidth: fila.implicitWidth + 24
    implicitHeight: 32
    width: implicitWidth
    height: implicitHeight
    activeFocusOnTab: true

    Rectangle {
        anchors.fill: parent
        radius: 16
        color: zona.pressed ? Qt.darker(Tema.fondoChip, 1.12) : zona.containsMouse ? Qt.darker(Tema.fondoChip, 1.06) : Tema.fondoChip
        border.width: pastilla.activeFocus ? 3 : 0
        border.color: Tema.foco
    }
    Row {
        id: fila
        anchors.centerIn: parent
        spacing: 5
        Icono {
            anchors.verticalCenter: parent.verticalCenter
            visible: pastilla.icono !== ""
            nombre: pastilla.icono
            color: pastilla.colorIcono
            lado: 10
        }
        Texto {
            anchors.verticalCenter: parent.verticalCenter
            text: pastilla.texto
            tam: 13
            peso: Font.ExtraBold
            alto: 1.3
        }
    }
    MouseArea {
        id: zona
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: pastilla.clic()
    }
    Keys.onReturnPressed: clic()
    Keys.onSpacePressed: clic()
}
