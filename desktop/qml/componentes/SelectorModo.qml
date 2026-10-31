import QtQuick
import Lesco

// «Selector de modo» de la cabecera: Escribir (Aa|) / Hablar («»).
Rectangle {
    id: selector
    property string modo: "escribir"      // "escribir" | "hablar"
    signal elegir(string modo)

    height: 38
    width: fila.implicitWidth + 6
    radius: 16
    color: Qt.rgba(1, 1, 1, 0.12)

    Row {
        id: fila
        x: 3; y: 3
        height: parent.height - 6

        Opcion {
            clave: "escribir"
            Row {
                spacing: 1
                anchors.verticalCenter: parent.verticalCenter
                Texto { text: "Aa"; peso: Font.ExtraBold; tam: 14; alto: 1; color: parent.parent.colorTexto }
                Rectangle { width: 2; height: 12; radius: 1; color: Tema.acentoNaranja; anchors.verticalCenter: parent.verticalCenter }
            }
            etiqueta: "Escribir"
        }
        Opcion {
            clave: "hablar"
            Texto {
                anchors.verticalCenter: parent.verticalCenter
                textFormat: Text.StyledText
                text: "<font color='#f68b1f'>«</font>»"
                peso: Font.ExtraBold; tam: 14; alto: 1
                font.letterSpacing: -1.12
                color: parent.colorTexto
            }
            etiqueta: "Hablar"
        }
    }

    component Opcion: Rectangle {
        id: op
        property string clave
        property string etiqueta
        default property alias glifo: glifos.data
        readonly property bool activa: selector.modo === clave
        readonly property color colorTexto: activa ? Tema.textoPrincipal : "#ffffff"

        height: parent.height
        width: contenido.implicitWidth + 18
        radius: 13
        color: activa ? Tema.fondoTarjeta : zona.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent"

        Row {
            id: contenido
            anchors.centerIn: parent
            spacing: 5
            Row { id: glifos; anchors.verticalCenter: parent.verticalCenter; property color colorTexto: op.colorTexto }
            Texto { text: op.etiqueta; peso: Font.ExtraBold; tam: 14; alto: 1; color: op.colorTexto; anchors.verticalCenter: parent.verticalCenter }
        }
        MouseArea {
            id: zona
            anchors.fill: parent
            hoverEnabled: true
            enabled: !op.activa
            cursorShape: Qt.PointingHandCursor
            onClicked: selector.elegir(op.clave)
        }
    }
}
