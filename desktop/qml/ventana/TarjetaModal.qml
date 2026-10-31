import QtQuick
import QtQuick.Effects
import Lesco

// Tarjeta blanca de las capas con fondo oscuro (Detalle de seña, Enseñar una seña):
// centrada en la pantalla, con su sombra.
Rectangle {
    id: tarjeta
    property real desplazamientoY: 0   // distancia respecto al centro vertical
    anchors.horizontalCenter: parent.horizontalCenter
    y: (parent.height - height) / 2 + desplazamientoY
    color: Tema.fondoTarjeta
    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.25)
        shadowVerticalOffset: 12
        shadowBlur: 0.9
    }
}
