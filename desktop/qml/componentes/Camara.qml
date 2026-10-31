import QtQuick
import QtQuick.Effects
import Lesco

// Componente «Cámara» (368×236): escena con la persona y los 21 puntos de cada
// mano, y la pastilla de estado arriba a la izquierda. Siempre dice su estado
// con texto, no solo con color.
Item {
    id: camara
    property string estado: "Cámara · solo en este equipo"
    property color colorPunto: Tema.estadoEnVivo
    property bool mostrarEscena: true
    default property alias encima: capaEncima.data

    implicitWidth: 368
    implicitHeight: 236

    Rectangle {
        id: marco
        anchors.fill: parent
        radius: 16
        color: Tema.fondoCamara
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.3)
            shadowVerticalOffset: 12
            shadowBlur: 0.8
        }
    }

    Item {
        anchors.fill: parent
        layer.enabled: true
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: mascara
        }
        Image {
            anchors.fill: parent
            visible: camara.mostrarEscena
            source: Qt.resolvedUrl("../../assets/imagenes/camara-escena.svg")
            sourceSize: Qt.size(width * 2, height * 2)
        }
        Item { id: capaEncima; anchors.fill: parent }
    }
    Item {
        id: mascara
        anchors.fill: parent
        layer.enabled: true
        visible: false
        Rectangle { anchors.fill: parent; radius: 16 }
    }

    Rectangle {
        x: 10; y: 10
        height: filaEstado.implicitHeight + 10
        width: filaEstado.implicitWidth + 19
        radius: height / 2
        color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.75)
        visible: camara.estado !== ""
        Row {
            id: filaEstado
            x: 9
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Rectangle { width: 8; height: 8; radius: 4; color: camara.colorPunto; anchors.verticalCenter: parent.verticalCenter }
            Texto { text: camara.estado; color: "#ffffff"; tam: Tema.tamNota }
        }
    }
}
