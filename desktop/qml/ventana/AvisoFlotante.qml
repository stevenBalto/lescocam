import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// Aviso oscuro de las «Capa · Aviso …»: ✓ + texto, centrado y 128 px sobre el
// borde inferior de la pantalla (como en Figma: 640 de 768). El texto admite
// <b>negrita</b>.
Rectangle {
    id: aviso
    property string texto

    anchors.horizontalCenter: parent.horizontalCenter
    y: parent.height - 128
    width: fila.implicitWidth + 32
    height: 40
    radius: 12
    color: "#14213d"
    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.30)
        shadowVerticalOffset: 8
        shadowBlur: 0.6
    }

    Accessible.role: Accessible.AlertMessage
    Accessible.name: aviso.texto.replace(/<[^>]*>/g, "")

    Row {
        id: fila
        x: 16
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
        Texto { text: "✓"; color: "#7be0a6"; peso: Font.Bold; tam: 14; alto: 1.2 }
        Texto { text: aviso.texto; textFormat: Text.StyledText; color: "#ffffff"; tam: 14; alto: 1.2 }
    }
}
