import QtQuick
import Lesco

// Texto con la fuente del diseño. `peso`: Font.Normal, Font.Bold o Font.ExtraBold.
Text {
    property int peso: Font.Normal
    property real alto: 1.4            // interlineado de Figma (1.4 = 140 %)

    font.family: Tema.fuente
    property real tam: Tema.tamNota  // tamaño en px de Figma (admite decimales, ej. 12.5)
    font.pointSize: tam * 0.75
    font.weight: peso
    color: Tema.textoPrincipal
    // Como en Figma: alto de línea = tamaño × interlineado (no la altura de la fuente × interlineado)
    lineHeight: Math.round(tam * alto)
    lineHeightMode: Text.FixedHeight
    textFormat: Text.PlainText
    renderType: Text.NativeRendering
}
