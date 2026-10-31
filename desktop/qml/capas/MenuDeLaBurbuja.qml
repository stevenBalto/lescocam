import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// «Capa · Menú de la burbuja»: clic derecho en la burbuja o Shift+F10.
// Se abre junto a la burbuja (a su izquierda y un poco más arriba).
Item {
    id: raiz

    property bool cerrarAlTocarFuera: true

    // «SWAP» de Figma: reemplaza esta capa por otra
    function cambiarPor(capa) { Nav.cerrar(); Nav.abrir(capa) }

    // [ícono, texto, atajo, color, acción]
    readonly property var opciones: [
        { icono: "escribir", texto: "Escribir", atajo: "Ctrl+Alt+E", suave: false, accion: "ir:02a" },
        { icono: "hablar", texto: "Hablar", atajo: "Ctrl+Alt+H", suave: false, accion: "ir:07a" },
        { icono: "pegar", texto: "Pegar lo último", atajo: "Ctrl+Alt+V", suave: false, accion: "ir:06" },
        { divisor: true },
        { icono: "inicio", texto: "Abrir historial", atajo: "", suave: false, accion: "capa:12" },
        { divisor: true },
        { icono: "ocultar", texto: "Ocultar 1 hora", atajo: "", suave: true, accion: "ocultar" },
        { icono: "cerrar", texto: "Salir de LESCOCam", atajo: "", suave: true, accion: "ir:01s" }
    ]

    function ejecutar(accion) {
        if (accion.indexOf("ir:") === 0) Nav.ir(accion.substring(3))
        else if (accion.indexOf("capa:") === 0) cambiarPor(accion.substring(5))
        else if (accion === "ocultar") { Nav.burbujaVisible = false; Nav.ir("01h") }
    }

    Rectangle {
        x: menu.x; y: menu.y
        width: menu.width; height: menu.height
        radius: menu.radius
        color: Tema.fondoTarjeta
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(13 / 255, 46 / 255, 110 / 255, 0.3)
            shadowVerticalOffset: 12
            shadowBlur: 0.8
            shadowScale: 0.96
        }
    }

    Rectangle {
        id: menu
        width: 260
        height: 242
        radius: Tema.radioVentana
        color: Tema.fondoTarjeta
        anchors.right: parent.right
        anchors.rightMargin: 62
        anchors.top: parent.top
        anchors.topMargin: 200

        MouseArea { anchors.fill: parent }   // los clics dentro no cierran la capa

        Column {
            x: 6; y: 6
            width: 248

            Repeater {
                model: raiz.opciones
                delegate: Item {
                    id: opcion
                    required property var modelData
                    readonly property bool esDivisor: modelData.divisor === true
                    width: 248
                    height: esDivisor ? 1 : 38
                    activeFocusOnTab: !esDivisor

                    Rectangle {   // divisor
                        visible: opcion.esDivisor
                        anchors.fill: parent
                        color: Tema.fondoOnda
                    }
                    Rectangle {   // fondo de la opción
                        visible: !opcion.esDivisor
                        anchors.fill: parent
                        radius: 8
                        color: zona.pressed ? Qt.darker(Tema.fondoChip, 1.06) : zona.containsMouse || opcion.activeFocus ? Tema.fondoChip : "transparent"
                        border.width: opcion.activeFocus ? 2 : 0
                        border.color: Tema.foco
                    }
                    Icono {
                        visible: !opcion.esDivisor
                        x: 10; anchors.verticalCenter: parent.verticalCenter
                        nombre: opcion.esDivisor ? "" : opcion.modelData.icono
                        color: !opcion.esDivisor && opcion.modelData.suave ? Tema.textoSecundario : Tema.textoPrincipal
                        lado: 18
                    }
                    Texto {
                        visible: !opcion.esDivisor
                        x: 40; anchors.verticalCenter: parent.verticalCenter
                        text: opcion.esDivisor ? "" : opcion.modelData.texto
                        tam: 14; alto: 1
                        color: !opcion.esDivisor && opcion.modelData.suave ? Tema.textoSecundario : Tema.textoPrincipal
                    }
                    Texto {
                        visible: !opcion.esDivisor
                        anchors.right: parent.right; anchors.rightMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        text: opcion.esDivisor ? "" : opcion.modelData.atajo
                        tam: 14; alto: 1
                        color: Tema.textoSecundario
                    }
                    MouseArea {
                        id: zona
                        enabled: !opcion.esDivisor
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: raiz.ejecutar(opcion.modelData.accion)
                    }
                    Keys.onReturnPressed: if (!esDivisor) raiz.ejecutar(modelData.accion)
                    Keys.onSpacePressed: if (!esDivisor) raiz.ejecutar(modelData.accion)
                }
            }
        }
    }
}
