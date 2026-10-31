import QtQuick
import QtQuick.Effects
import Lesco

// Tarjeta blanca con sombra suave (cartas de detalle del historial y del diccionario).
Rectangle {
    id: tarjeta
    property bool sombra: true
    radius: 24
    color: Tema.fondoTarjeta
    layer.enabled: sombra
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.12)
        shadowVerticalOffset: 12
        shadowBlur: 0.7
    }
}
