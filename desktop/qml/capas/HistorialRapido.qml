import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// «Capa · Historial rápido»: lo último que escribió o dijo LESCOCam, junto al
// panel (se abre desde el panel). Pegar → 06, Reproducir → 09s, Esc cierra.
Item {
    id: raiz

    property bool cerrarAlTocarFuera: true

    Rectangle {
        x: panel.x; y: panel.y
        width: panel.width; height: panel.height
        radius: panel.radius
        color: Tema.fondoPanel
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
        id: panel
        width: 376
        height: 374
        radius: Tema.radioVentana
        color: Tema.fondoPanel
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.top: parent.top
        anchors.topMargin: 58

        MouseArea { anchors.fill: parent }   // los clics dentro no cierran la capa

        Column {
            x: 12; y: 12
            width: 352
            spacing: 8

            Texto { text: "Lo último"; tam: 15; peso: Font.Bold; alto: 1.3 }

            Repeater {
                model: [
                    { frase: "Hola, soy Christian.", detalle: "Escrito · Soporte UTN · 3:41 p. m.", hablado: false },
                    { frase: "Necesito ayuda con mi matrícula.", detalle: "Hablado · voz Ana · 3:38 p. m.", hablado: true },
                    { frase: "¿Me pueden enviar el comprobante?", detalle: "Escrito · Soporte UTN · 3:36 p. m.", hablado: false }
                ]
                delegate: Rectangle {
                    id: entrada
                    required property var modelData
                    width: 352
                    height: 85
                    radius: Tema.radioControl
                    color: Tema.fondoTarjeta

                    Texto { x: 12; y: 12; text: entrada.modelData.frase; tam: 16; alto: 1.3 }
                    Item {
                        x: 12; y: 41
                        width: 332; height: 32

                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 8; height: 8
                            radius: entrada.modelData.hablado ? 4 : 2
                            color: entrada.modelData.hablado ? Tema.acentoHablar : Tema.acentoEscribir
                        }
                        Texto {
                            x: 14; anchors.verticalCenter: parent.verticalCenter
                            text: entrada.modelData.detalle
                            tam: 14
                            color: Tema.textoSecundario
                            width: parent.width - 14 - botones.width - 6
                            elide: Text.ElideRight
                        }
                        Row {
                            id: botones
                            anchors.right: parent.right
                            spacing: 6
                            Boton {
                                visible: !entrada.modelData.hablado
                                estilo: "texto"; alto: 32; texto: "Copiar"
                            }
                            Boton {
                                visible: !entrada.modelData.hablado
                                estilo: "texto"; alto: 32; texto: "Pegar"
                                onClic: Nav.ir("06")
                            }
                            Boton {
                                visible: entrada.modelData.hablado
                                estilo: "texto"; alto: 32; texto: "Reproducir"
                                onClic: Nav.ir("09s")
                            }
                            Boton {
                                visible: entrada.modelData.hablado
                                estilo: "texto"; alto: 32; texto: "MP3"
                            }
                        }
                    }
                }
            }

            Boton {
                estilo: "texto"
                texto: "Ver todo el historial →"
                onClic: { Nav.cerrar(); Nav.abrir("12") }   // «SWAP» de Figma
            }
        }
    }
}
