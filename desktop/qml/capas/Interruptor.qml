import QtQuick
import Lesco

// Componente «Interruptor» de Figma (42 × 24): encendido naranja, apagado gris.
Item {
    id: interruptor
    property bool encendido: true
    signal alternar()

    width: 42
    height: 24
    activeFocusOnTab: true
    Accessible.role: Accessible.CheckBox
    Accessible.checked: encendido

    Rectangle {
        anchors.fill: parent
        radius: 12
        color: interruptor.encendido ? Tema.acentoNaranja : Tema.interruptorApagado
        Behavior on color { ColorAnimation { duration: Tema.animRapida } }
    }
    Rectangle {
        y: 3
        x: interruptor.encendido ? 21 : 3
        width: 18; height: 18; radius: 9
        color: "#ffffff"
        Behavior on x { NumberAnimation { duration: Tema.animRapida } }
    }
    Rectangle {   // anillo de foco de teclado
        anchors.fill: parent; anchors.margins: -3
        radius: 15
        color: "transparent"
        border.width: 3
        border.color: Tema.foco
        visible: interruptor.activeFocus
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: interruptor.alternar()
    }
    Keys.onSpacePressed: alternar()
    Keys.onReturnPressed: alternar()
}
