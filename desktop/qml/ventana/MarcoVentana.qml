import QtQuick
import QtQuick.Effects
import Lesco

// Marco de las ventanas 12–15 (1060×650, esquinas del panel y sombra de Figma).
// La ventana real es más grande que la tarjeta para que quepa la sombra.
Item {
    id: marco
    property int ancho: 1060
    property int alto: 650
    readonly property int margen: 48
    default property alias contenido: interior.data

    implicitWidth: ancho + margen * 2
    implicitHeight: alto + margen * 2

    Rectangle {   // fondo con sombra
        x: marco.margen; y: marco.margen
        width: marco.ancho; height: marco.alto
        radius: Tema.radioPanel
        color: Tema.fondoPanel
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.30)
            shadowVerticalOffset: 14
            shadowBlur: 0.9
        }
    }

    Item {   // contenido recortado con las esquinas
        id: interior
        x: marco.margen; y: marco.margen
        width: marco.ancho; height: marco.alto
        layer.enabled: true
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: mascara
        }
    }
    Item {
        id: mascara
        x: marco.margen; y: marco.margen
        width: marco.ancho; height: marco.alto
        layer.enabled: true
        visible: false
        Rectangle { anchors.fill: parent; radius: Tema.radioPanel }
    }
}
