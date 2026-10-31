import QtQuick
import Lesco

// Subrayado ondulado («ola») que marca una palabra dudosa.
Canvas {
    id: ola
    property color color: Tema.acentoNaranja
    property real grosor: 2
    property real paso: 6
    height: 5

    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.strokeStyle = ola.color
        ctx.lineWidth = ola.grosor
        ctx.lineCap = "round"
        ctx.beginPath()
        var medio = height / 2, amp = (height - grosor) / 2
        ctx.moveTo(0, medio)
        for (var x = 0; x <= width; x += 1)
            ctx.lineTo(x, medio - Math.sin(x / paso * Math.PI) * amp)
        ctx.stroke()
    }
}
