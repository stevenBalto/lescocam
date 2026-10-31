import QtQuick
import Lesco

// Botón redondo de 30 px de la cabecera azul del panel (Historial, Diccionario…).
Rectangle {
    id: b
    property string icono
    property int ladoIcono: 17
    property string nombreAccesible
    signal clic()

    width: 30; height: 30; radius: 15
    color: zona.pressed ? Qt.rgba(1, 1, 1, 0.22) : zona.containsMouse ? Qt.rgba(1, 1, 1, 0.18) : Qt.rgba(1, 1, 1, 0.10)
    Accessible.role: Accessible.Button
    Accessible.name: nombreAccesible

    Icono { anchors.centerIn: parent; nombre: b.icono; lado: b.ladoIcono; color: "#ffffff" }
    MouseArea { id: zona; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: b.clic() }
}
