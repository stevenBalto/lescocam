import QtQuick
import Lesco

// «Interruptor» de Figma (44×24): naranja con perilla azul si está activo,
// gris con perilla blanca si no.
Rectangle {
    id: interruptor
    property bool activo: false
    property string nombreAccesible
    signal cambio(bool valor)

    width: 44; height: 24; radius: 12
    color: activo ? Tema.acentoNaranja : Tema.bordeControl
    activeFocusOnTab: true
    Accessible.role: Accessible.CheckBox
    Accessible.name: nombreAccesible
    Accessible.checked: activo
    Behavior on color { ColorAnimation { duration: Tema.animRapida } }

    Rectangle {
        y: 3; width: 18; height: 18; radius: 9
        x: interruptor.activo ? 23 : 3
        color: interruptor.activo ? Tema.textoSobreNaranja : "#ffffff"
        Behavior on x { NumberAnimation { duration: Tema.animRapida } }
    }
    Rectangle {
        anchors.fill: parent; anchors.margins: -3; radius: 15
        color: "transparent"; border.width: 3; border.color: Tema.foco
        visible: interruptor.activeFocus
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: interruptor.cambio(!interruptor.activo)
    }
    Keys.onSpacePressed: cambio(!activo)
    Keys.onReturnPressed: cambio(!activo)
}
