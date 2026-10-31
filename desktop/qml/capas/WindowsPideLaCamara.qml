import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// «Capa · Windows pide la cámara»: diálogo del sistema que aparece al tocar
// «Permitir cámara». Es de Windows, no de LESCOCam: no sigue el modo oscuro.
Item {
    id: capa

    // Velo oscuro sobre toda la pantalla
    Rectangle { anchors.fill: parent; color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.35) }
    MouseArea { anchors.fill: parent }   // el velo bloquea los clics de abajo

    Item {
        id: dialogo
        width: 400
        height: columna.implicitHeight + 40
        x: (parent.width - width) / 2
        y: (parent.height - 48 - height) / 2    // centrado sobre el área sin la barra de tareas

        Rectangle {
            anchors.fill: parent
            radius: 10
            color: "#ffffff"
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.35)
                shadowVerticalOffset: 20
                shadowBlur: 1.0
            }
        }

        Column {
            id: columna
            x: 22; y: 22
            width: parent.width - 44
            spacing: 8

            Texto {
                text: "¿Permitir que LESCOCam use la cámara?"
                peso: Font.Bold; tam: 16; alto: 1; color: "#000000"
            }
            Texto {
                text: "LESCOCam necesita la cámara para reconocer sus señas."
                tam: 13.5; alto: 1; color: "#444444"
            }
            Item {
                width: parent.width
                height: 42
                Row {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    spacing: 8
                    Boton32 { texto: "No"; fondo: "#f3f3f3"; borde: "#cfcfcf"; colorTexto: "#1c1b1f"; onClic: Nav.ir("23n") }
                    Boton32 { texto: "Sí"; fondo: "#0f6cbd"; borde: "transparent"; colorTexto: "#ffffff"; onClic: Nav.ir("23b") }
                }
            }
        }
    }

    // Botón del diálogo de Windows (32 px de alto, esquinas de 5 px)
    component Boton32: FocusScope {
        id: b
        property string texto
        property color fondo
        property color borde
        property color colorTexto
        signal clic()
        implicitWidth: etiqueta.implicitWidth + 44
        implicitHeight: 32
        activeFocusOnTab: true
        Rectangle {
            anchors.fill: parent
            radius: 5
            color: zona.pressed ? Qt.darker(b.fondo, 1.1) : zona.containsMouse ? Qt.lighter(b.fondo, 1.08) : b.fondo
            border.width: 1
            border.color: b.borde
        }
        Rectangle {
            anchors.fill: parent; anchors.margins: -3
            radius: 8; color: "transparent"
            border.width: 3; border.color: Tema.foco
            visible: b.activeFocus
        }
        Texto { id: etiqueta; anchors.centerIn: parent; text: b.texto; tam: 13.5; alto: 1; color: b.colorTexto }
        MouseArea {
            id: zona
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: b.clic()
        }
        Keys.onReturnPressed: clic()
        Keys.onSpacePressed: clic()
    }
}
