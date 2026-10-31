import QtQuick
import Lesco

// Marcador para las pantallas del prototipo que todavía no se pasaron a código.
Rectangle {
    property string codigo: Nav.pantalla
    color: Tema.fondoPanel
    Column {
        anchors.centerIn: parent
        spacing: 8
        Texto { anchors.horizontalCenter: parent.horizontalCenter; text: "Pantalla " + codigo; peso: Font.ExtraBold; tam: Tema.tamSubtitulo }
        Texto { anchors.horizontalCenter: parent.horizontalCenter; text: "Pendiente de pasar desde Figma"; color: Tema.textoSecundario }
    }
}
