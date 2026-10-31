import QtQuick
import QtQuick.Window
import Lesco
import "../componentes"

// «Capas» de Figma (se abren encima de la pantalla): Bandeja, Menú de la
// burbuja, Historial rápido, Detalle de seña, Enseñar una seña, avisos…
//
// En Figma cada capa es un frame de pantalla completa con el contenido en
// una posición; acá igual: la ventana cubre la pantalla, es transparente, y
// el archivo de la capa ubica su contenido (por ejemplo, abajo a la derecha
// para la bandeja). Si la capa define `cerrarAlTocarFuera: true`, un clic
// fuera del contenido la cierra (CLICK → CLOSE en Figma).
Window {
    id: ventana
    readonly property string nombre: Nav.esCapa(Nav.capa) ? Nav.capa : ""
    x: Screen.virtualX
    y: Screen.virtualY
    width: Screen.width
    height: Screen.height
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    color: "transparent"
    title: "LESCOCam · " + nombre
    visible: nombre !== ""

    // "Capa · Aviso del historial · copiado" → "capas/AvisoDelHistorialCopiado.qml"
    function archivoDe(n) {
        var sinTildes = n.replace("Capa · ", "").replace(/[áÁ]/g, "a").replace(/[éÉ]/g, "e")
                         .replace(/[íÍ]/g, "i").replace(/[óÓ]/g, "o").replace(/[úÚ]/g, "u").replace(/ñ/g, "n")
        var partes = sinTildes.split(/[ ·]+/)
        return "../capas/" + partes.map(function (p) { return p.charAt(0).toUpperCase() + p.slice(1) }).join("") + ".qml"
    }

    MouseArea {
        anchors.fill: parent
        enabled: contenido.item && contenido.item.cerrarAlTocarFuera === true
        onClicked: Nav.cerrar()
    }

    Cargador {
        id: contenido
        anchors.fill: parent
        codigo: ventana.nombre
        archivo: ventana.nombre ? ventana.archivoDe(ventana.nombre) : ""
    }

    Timer {   // las «Capa · Aviso …» se cierran solas (AFTER_TIMEOUT 1800 → CLOSE)
        running: ventana.nombre.indexOf("Capa · Aviso") === 0
        interval: Nav.duracionAviso
        onTriggered: Nav.cerrar()
    }

    Shortcut { sequence: "Esc"; onActivated: Nav.cerrar() }
}
