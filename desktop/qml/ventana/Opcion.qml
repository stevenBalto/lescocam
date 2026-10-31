import QtQuick
import Lesco
import "../componentes"

// «Chip» de opción de Ajustes (alto 39, pastilla): activo = fondo azul.
Rectangle {
    id: chip
    property string texto
    property bool activo: false
    signal elegir()

    implicitWidth: etiqueta.implicitWidth + 31
    width: implicitWidth
    height: 39
    radius: 999
    color: activo ? Tema.fondoSeleccion : "transparent"
    border.width: 1.5
    border.color: activo ? Tema.fondoSeleccion : Tema.bordeControl
    activeFocusOnTab: true
    Accessible.role: Accessible.RadioButton
    Accessible.name: texto
    Accessible.checked: activo

    Texto {
        id: etiqueta
        anchors.centerIn: parent
        text: chip.texto
        tam: 14
        alto: 1.3
        peso: chip.activo ? Font.Bold : Font.Normal
        color: chip.activo ? Tema.textoSobreSeleccion : Tema.textoPrincipal
    }
    Rectangle {
        anchors.fill: parent; anchors.margins: -3; radius: 22
        color: "transparent"; border.width: 3; border.color: Tema.foco
        visible: chip.activeFocus
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: chip.elegir()
    }
    Keys.onSpacePressed: elegir()
    Keys.onReturnPressed: elegir()
}
