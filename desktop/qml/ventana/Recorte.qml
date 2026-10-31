import QtQuick
import QtQuick.Effects
import Lesco

// Recorta a sus hijos con esquinas redondeadas (cámaras y videos).
Item {
    id: recorte
    property int radio: 16
    default property alias contenido: interior.data

    Item {
        id: interior
        anchors.fill: parent
        layer.enabled: true
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: mascara
        }
    }
    Item {
        id: mascara
        anchors.fill: parent
        layer.enabled: true
        visible: false
        Rectangle { anchors.fill: parent; radius: recorte.radio }
    }
}
