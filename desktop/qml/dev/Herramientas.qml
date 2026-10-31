import QtQuick
import QtQuick.Window
import QtQuick.Controls
import Lesco
import "../componentes"

// Ventana de desarrollo (solo con --dev): saltar a cualquier pantalla del
// prototipo, ver la pantalla y la capa actuales, y probar tema y escala.
Window {
    id: ventana
    width: 300
    height: 640
    x: Screen.virtualX + 24
    y: Screen.virtualY + 24
    visible: true
    title: "LESCOCam · herramientas de desarrollo"
    color: "#ffffff"

    readonly property var grupos: [
        ["A · Escribir", "01 02 03 04 06 04e 01r"],
        ["A+ · Escribir (más)", "01b 01d 01h 01h2 01s 02a 02h 02b 03b 03c 03d 03g 03y 03h 03i 04c"],
        ["B · Hablar", "07 08 09 07a 07h 07b 09s 09s2 09s3 09v 09g 09k 09m 09p 09e 09r1 09r2 01e"],
        ["C · Ventanas", "12 12e 12h 12k 13 13s 13f 13l 13q 13m 14 14a 14c 14d 14e 14f 14g 15a 15b 15c 15d"],
        ["D · Estados y errores", "16 17 18 19 20 21 21b"],
        ["E · Primer uso", "22 23 23b 23n 24 24ok 25 25b 25c 25d 25e 26 26b"],
        ["Animación de inicio", "00a 00b 00c 00d"]
    ]

    ScrollView {
        anchors.fill: parent
        anchors.margins: 12
        contentWidth: availableWidth

        Column {
            width: parent.width
            spacing: 10

            Texto { text: "Pantalla: " + Nav.pantalla + (Nav.capa ? "\nCapa: " + Nav.capa : ""); peso: Font.Bold; color: "#0d2d6d" }

            Row {
                spacing: 6
                CheckBox { text: "Oscuro"; checked: Tema.oscuro; onToggled: Tema.oscuro = checked }
                ComboBox {
                    model: ["100 %", "125 %", "150 %"]
                    currentIndex: Tema.escala
                    onActivated: (i) => Tema.escala = i
                    width: 100
                }
            }
            CheckBox { text: "Primer uso pendiente"; checked: Nav.primerUso; onToggled: Nav.primerUso = checked }

            Repeater {
                model: ventana.grupos
                Column {
                    width: parent.width
                    spacing: 4
                    Texto { text: modelData[0]; peso: Font.Bold; color: "#4b5b7c"; tam: 12 }
                    Flow {
                        width: parent.width
                        spacing: 4
                        Repeater {
                            model: modelData[1].split(" ")
                            Button {
                                text: modelData
                                highlighted: Nav.pantalla === modelData
                                width: 46
                                onClicked: Nav.ir(modelData)
                            }
                        }
                    }
                }
            }
        }
    }
}
