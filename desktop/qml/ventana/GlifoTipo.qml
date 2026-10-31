import QtQuick
import Lesco
import "../componentes"

// Glifo del tipo de frase: «Aa» + cursor naranja (escrito) o «» (hablado).
Row {
    id: glifo
    property string tipo: "escrito"
    property real tam: 15
    property color color: Tema.textoPrincipal
    spacing: 1

    Texto { visible: glifo.tipo === "escrito"; text: "Aa"; peso: Font.ExtraBold; tam: glifo.tam; alto: 1; color: glifo.color }
    Rectangle {
        visible: glifo.tipo === "escrito"
        width: 2.5; height: glifo.tam * 0.95; radius: 1
        color: Tema.acentoNaranja
        anchors.verticalCenter: parent.verticalCenter
    }
    Texto { visible: glifo.tipo !== "escrito"; text: "«»"; peso: Font.ExtraBold; tam: glifo.tam; alto: 1; color: glifo.color }
}
