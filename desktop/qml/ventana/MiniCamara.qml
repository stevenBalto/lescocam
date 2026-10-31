import QtQuick
import Lesco
import "../componentes"

// Imagen de la cámara con la escena de ejemplo, recortada. Se usa en las
// miniaturas y en los videos de referencia (el «zoom» la agranda desde el centro).
Item {
    id: mini
    property real zoom: 1
    clip: true
    Camara {
        estado: ""
        anchors.centerIn: parent
        width: parent.width * mini.zoom
        height: parent.height * mini.zoom
    }
}
