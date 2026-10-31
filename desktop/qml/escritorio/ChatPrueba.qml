import QtQuick
import QtQuick.Window
import Lesco
import "../componentes"

// Solo con --dev. «App simulada / Chat de Windows»: el chat «Soporte UTN» donde
// LESCOCam «escribe» (en la prueba con usuarios). Es una ventana normal de
// Windows, a la izquierda del panel, y refleja lo que LESCOCam escribió según
// la pantalla del prototipo. Los colores y la tipografía son los de la app de
// terceros simulada (no los de LESCOCam), por eso no salen de Tema.
Window {
    id: ventana

    // Texto del campo «Mensaje» por pantalla (frames de Figma)
    readonly property var textos: ({
        "01b": "Hola, yo", "02": "Hola, yo", "03": "Hola, yo", "03y": "Hola, yo",
        "02h": "Hola", "02b": "Hola,", "03b": "Hola, soy", "03c": "Hola, ser", "03d": "Hola, so",
        "03g": "Hola, soy Christian", "03h": "Hola, soy Christian", "17": "Hola, soy Christian",
        "18": "Hola, soy Christian", "21": "Hola, soy Christian", "21b": "Hola, soy Christian",
        "03i": "Hola, Christian",
        "04": "Hola, soy Christian.", "06": "Hola, soy Christian.", "01d": "Hola, soy Christian.",
        "09p": "Hola, soy Christian.", "04c": "Hola, ser."
    })
    readonly property var enviados: ({ "04e": "Hola, soy Christian.", "09e": "Hola, soy Christian." })
    readonly property string pantalla: Nav.pantalla
    readonly property string campo: textos[pantalla] || ""
    readonly property string enviado: enviados[pantalla] || ""
    // Sin texto y con LESCOCam en modo Hablar / ya guardado / ya enviado: el campo muestra el aviso gris
    readonly property bool conMarcador: campo === "" && (enviado !== "" || pantalla === "01e" || /^(07|08|09)/.test(pantalla))
    readonly property bool sinChat: Nav.esPrimerUso(pantalla) || pantalla === "09m" || pantalla === "05"
    readonly property string fuente: "Segoe UI"

    visible: Nav.modoDev && !sinChat
    title: "Soporte UTN — Chat"
    color: "#fafbfc"
    x: Screen.virtualX + 40
    y: Screen.virtualY + 40
    width: Math.max(480, Math.min(820, Screen.desktopAvailableWidth - 400 - 80))
    height: Math.min(640, Screen.desktopAvailableHeight - 80)
    minimumWidth: 480
    minimumHeight: 360

    // Conversación
    Column {
        x: 28; y: 24
        width: parent.width - 56
        spacing: 12

        Rectangle {
            width: recibido.implicitWidth + 30
            height: 40
            color: "#e7ebf0"
            topLeftRadius: 4; topRightRadius: 14; bottomLeftRadius: 14; bottomRightRadius: 14
            Text {
                id: recibido
                x: 15; anchors.verticalCenter: parent.verticalCenter
                text: "Buenas tardes, le saluda Soporte UTN. ¿En qué le podemos ayudar?"
                font.family: ventana.fuente; font.pixelSize: 15
                color: "#1f2933"
            }
        }
        Item {
            visible: ventana.enviado !== ""
            width: parent.width; height: 40
            Rectangle {
                anchors.right: parent.right
                width: enviadoTexto.implicitWidth + 30
                height: 40
                color: "#2563eb"
                topLeftRadius: 14; topRightRadius: 4; bottomLeftRadius: 14; bottomRightRadius: 14
                Text {
                    id: enviadoTexto
                    x: 15; anchors.verticalCenter: parent.verticalCenter
                    text: ventana.enviado
                    font.family: ventana.fuente; font.pixelSize: 15
                    color: "#ffffff"
                }
            }
        }
        Text {
            visible: ventana.enviado !== ""
            width: parent.width
            horizontalAlignment: Text.AlignRight
            text: "Enviado · 3:42 p. m."
            font.family: ventana.fuente; font.pixelSize: 12
            color: "#6b788c"
        }
    }

    // Redactar
    Rectangle {
        id: redactar
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 73
        color: "#ffffff"
        Rectangle { width: parent.width; height: 1; color: "#e4e7eb" }

        Rectangle {
            id: cajaCampo
            x: 18; y: 15
            width: parent.width - 18 * 2 - 44 - 10
            height: 44
            radius: 8
            color: "#ffffff"
            border.width: ventana.conMarcador ? 1 : 2
            border.color: ventana.conMarcador ? "#cbd2d9" : "#2563eb"

            Text {
                id: textoCampo
                x: 15; anchors.verticalCenter: parent.verticalCenter
                text: ventana.conMarcador ? "Escriba un mensaje…" : ventana.campo
                font.family: ventana.fuente; font.pixelSize: 15
                color: ventana.conMarcador ? "#9aa5b1" : "#1f2933"
            }
            Rectangle {   // cursor
                visible: !ventana.conMarcador
                x: textoCampo.x + textoCampo.implicitWidth + 1
                anchors.verticalCenter: parent.verticalCenter
                width: 2; height: 19
                color: "#1f2933"
                SequentialAnimation on opacity {
                    running: !Tema.reducirMovimiento && ventana.visible
                    loops: Animation.Infinite
                    NumberAnimation { to: 0; duration: 500 }
                    NumberAnimation { to: 1; duration: 500 }
                }
            }
        }
        Rectangle {
            x: parent.width - 18 - 44; y: 15
            width: 44; height: 44
            radius: 8
            color: "#2563eb"
            Text { anchors.centerIn: parent; text: "➤"; font.pixelSize: 17; color: "#ffffff" }
            MouseArea {   // 04 · Texto escrito: Enviar → 04e
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: if (ventana.pantalla === "04") Nav.ir("04e")
            }
        }
    }
}
