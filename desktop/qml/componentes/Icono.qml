import QtQuick
import Lesco

// Ícono de Figma («Ícono/…») pintado del color pedido.
Image {
    property string nombre
    property color color: Tema.textoPrincipal
    property int lado: 18

    width: lado
    height: lado
    sourceSize: Qt.size(lado * 2, lado * 2)
    source: nombre ? Tema.icono(nombre, color) : ""
    smooth: true
}
