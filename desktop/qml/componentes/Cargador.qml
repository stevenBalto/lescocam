import QtQuick

// Carga el archivo QML de una pantalla. Si todavía no existe, muestra el
// marcador «Pendiente de pasar desde Figma» en su lugar.
Item {
    id: cargador
    property url archivo
    property string codigo
    readonly property Item item: carga.item

    implicitWidth: carga.item ? carga.item.implicitWidth : 400
    implicitHeight: carga.item ? carga.item.implicitHeight : 300

    Loader {
        id: carga
        anchors.fill: parent
        source: cargador.archivo
    }
    Pendiente {
        anchors.fill: parent
        codigo: cargador.codigo
        visible: carga.status === Loader.Error || (carga.status === Loader.Null && cargador.codigo !== "")
    }
}
