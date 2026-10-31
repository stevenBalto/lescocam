import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// Ventana «14 · Práctica» y sus variantes:
// 14 reconocida (seña 3), 14a esperando, 14c casi, 14d seña 4 esperando,
// 14e seña 4 reconocida, 14f seña 5 esperando, 14g práctica completa.
MarcoVentana {
    id: vista

    readonly property string codigo: Nav.esVentana(Nav.capa) ? Nav.capa : Nav.pantalla
    // Estado de la seña: "reconocida", "esperando", "casi" o "completa"
    readonly property string estado: {
        switch (codigo) {
        case "14": case "14e": return "reconocida"
        case "14c": return "casi"
        case "14g": return "completa"
        default: return "esperando"
        }
    }
    // Paso actual de la lección (1 a 5)
    readonly property int paso: codigo === "14d" || codigo === "14e" ? 4 : codigo === "14f" || codigo === "14g" ? 5 : 3
    readonly property bool completa: estado === "completa"
    readonly property bool mensajeAlto: estado === "casi" || completa
    readonly property bool pausada: pausa
    readonly property color colorBorde: estado === "reconocida" || completa ? Tema.estadoOk
                                      : estado === "casi" ? Tema.acentoNaranja : "transparent"

    property bool pausa: false          // practica-pc-pausada
    property bool referencia: false     // practica-pc-referencia (video de referencia sonando)
    onCodigoChanged: { pausa = false; referencia = false }

    // Siguiente pantalla automática de las variantes «esperando» (AFTER_TIMEOUT 2.5 s)
    readonly property var automatico: ({ "14a": "14c", "14d": "14e", "14f": "14g" })
    Timer {
        running: vista.automatico[vista.codigo] !== undefined
        interval: 2500
        onTriggered: Nav.ir(vista.automatico[vista.codigo])
    }

    function repetir() {
        pausa = false; referencia = false
        var destino = { "14": "14a", "14a": "14c", "14c": "14", "14d": "14e", "14e": "14d" }[codigo]
        if (destino) Nav.ir(destino)
    }
    function siguiente() {
        pausa = false; referencia = false
        if (codigo === "14") {
            if (Estado.enLeccion) {
                Estado.palabra = "Buenos días"
                Estado.etiqueta = "Seña 4 de 5 · Saludos"
                Nav.ir("14d")
            } else {
                Estado.palabra = "Gracias"
                Estado.etiqueta = "Seña 3 de 5 · Saludos"
                Estado.siguiente = "Siguiente seña"
                Estado.enLeccion = true
                Nav.ir("13")
            }
        } else if (codigo === "14e") {
            Estado.palabra = "Adiós"
            Estado.etiqueta = "Seña 5 de 5 · Saludos"
            Nav.ir("14f")
        }
    }
    function practicarDeNuevo() {
        Estado.palabra = "Gracias"
        Estado.etiqueta = "Seña 3 de 5 · Saludos"
        Estado.siguiente = "Siguiente seña"
        Estado.enLeccion = true
        pausa = false; referencia = false
        Nav.ir("14a")
    }
    function elegirOtraCategoria() { pausa = false; referencia = false; Nav.ir("13") }

    CabeceraVentana {
        titulo: "Práctica"
        onAbrirPanel: { vista.pausa = false; vista.referencia = false; Nav.ir("02a") }
        onCerrar: { vista.pausa = false; vista.referencia = false; Nav.cerrar() }
    }

    Item {   // Cuerpo
        y: 65
        width: 1060; height: 585

        // ── Su cámara ─────────────────────────────────────────────────
        Item {
            x: 26; y: 22
            width: 608; height: 541

            Recorte {
                anchors.fill: parent
                radio: 18
                Rectangle { anchors.fill: parent; color: Tema.fondoCamara }
                Camara {
                    estado: ""
                    x: -126.2; y: -5.4
                    width: 860.5; height: 551.8
                }
                Rectangle {   // etiqueta
                    x: 14; y: 14
                    width: 193; height: 26; radius: 9
                    color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.6)
                    Rectangle { x: 9; y: 9.5; width: 7; height: 7; radius: 3.5; color: "#ff6b6b" }
                    Texto { x: 22; anchors.verticalCenter: parent.verticalCenter; text: "Usted · solo en este equipo"; color: "#ffffff"; peso: Font.Bold; tam: 12.5; alto: 1.2 }
                }
                Rectangle {   // En pausa
                    visible: vista.pausa
                    anchors.fill: parent
                    color: Qt.rgba(10 / 255, 23 / 255, 48 / 255, 0.9)
                    Column {
                        anchors.centerIn: parent
                        spacing: 6
                        Texto { anchors.horizontalCenter: parent.horizontalCenter; text: "❚❚  En pausa"; color: "#ffffff"; peso: Font.Bold; tam: 18; alto: 1.2 }
                        Texto { anchors.horizontalCenter: parent.horizontalCenter; text: "La cámara no ve nada."; color: "#c9d6ee"; tam: 14; alto: 1.2 }
                    }
                }
            }
            Rectangle {   // borde de estado (4 px)
                anchors.fill: parent
                radius: 18
                color: "transparent"
                border.width: 4
                border.color: vista.colorBorde
            }
        }

        // ── Columna derecha ───────────────────────────────────────────
        Item {
            x: 654; y: 22
            width: 380; height: 541

            Rectangle {   // Carta de la seña
                id: carta
                width: 380
                height: vista.mensajeAlto ? 341 : 360
                radius: 22
                color: Tema.fondoTarjeta

                Texto { x: 18; y: 18; text: vista.completa ? "Seña 5 de 5 · Saludos" : Estado.etiqueta; color: Tema.textoSecundario; peso: Font.Bold; tam: 13.5; alto: 1.3 }

                Row {   // Avance
                    x: 18; y: 46
                    spacing: 5
                    Repeater {
                        model: 5
                        Rectangle {
                            width: 64.8; height: 7; radius: 4
                            color: vista.completa || index + 1 < vista.paso ? Tema.acentoNaranja
                                 : index + 1 === vista.paso ? Tema.textoPrincipal : Tema.fondoOnda
                        }
                    }
                }

                Texto {
                    visible: !vista.completa
                    x: 18; y: 63
                    text: "Haga la seña de"
                    color: Tema.textoSecundario
                    peso: Font.Bold
                    tam: 15
                    alto: 1.3
                }
                Texto {
                    visible: !vista.completa
                    x: 18; y: 93
                    text: "«" + Estado.palabra + "»"
                    peso: Font.ExtraBold
                    tam: 40
                    alto: 1.05
                }
                Texto {
                    visible: vista.completa
                    x: 18; y: 63
                    width: 344
                    text: "¡Terminó la práctica de Saludos!"
                    peso: Font.ExtraBold
                    tam: 30
                    alto: 0.88
                    wrapMode: Text.WordWrap
                }

                Rectangle {   // Referencia
                    id: ref
                    x: 18
                    y: vista.completa ? 139 : 145
                    width: 344
                    height: carta.height - y - 18
                    radius: 16
                    color: Tema.fondoCamara
                    Recorte {
                        anchors.fill: parent
                        radio: 16
                        Camara {
                            estado: ""
                            x: -3.4; y: (ref.height - 225) / 2
                            width: 350.9; height: 225
                        }
                        Rectangle {
                            x: 12; y: 12
                            width: 82; height: 26; radius: 9
                            color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.55)
                            Texto { anchors.centerIn: parent; text: "Referencia"; color: "#ffffff"; peso: Font.Bold; tam: 12.5; alto: 1.2 }
                        }
                        Rectangle {   // Botón Ver referencia
                            visible: !vista.referencia
                            x: 146; y: (ref.height - 52) / 2
                            width: 52; height: 52; radius: 26
                            color: Qt.rgba(1, 1, 1, zonaRef.containsMouse ? 0.26 : 0.16)
                            border.width: 1
                            border.color: Qt.rgba(1, 1, 1, 0.30)
                            activeFocusOnTab: true
                            Accessible.role: Accessible.Button
                            Accessible.name: "Ver referencia"
                            Icono { anchors.centerIn: parent; anchors.horizontalCenterOffset: 2; nombre: "reproducir"; lado: 17; color: "#ffffff" }
                            MouseArea {
                                id: zonaRef
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: vista.referencia = true
                            }
                            Keys.onReturnPressed: vista.referencia = true
                            Keys.onSpacePressed: vista.referencia = true
                        }
                        Rectangle {   // Avance del video
                            visible: vista.referencia
                            y: ref.height - 4
                            width: 206.4; height: 4
                            color: Tema.acentoNaranja
                        }
                        Rectangle {   // Botón Detener referencia
                            visible: vista.referencia
                            x: 204; y: 12
                            width: 128; height: 28; radius: 14
                            color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.7)
                            activeFocusOnTab: true
                            Accessible.role: Accessible.Button
                            Accessible.name: "Detener referencia"
                            Icono { x: 9; anchors.verticalCenter: parent.verticalCenter; nombre: "pausar"; lado: 14; color: "#ffffff" }
                            Texto { x: 28; anchors.verticalCenter: parent.verticalCenter; text: "Reproduciendo"; color: "#ffffff"; peso: Font.Bold; tam: 12.5; alto: 1.2 }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: vista.referencia = false
                            }
                            Keys.onReturnPressed: vista.referencia = false
                            Keys.onSpacePressed: vista.referencia = false
                        }
                    }
                }
            }

            Rectangle {   // Mensaje
                y: carta.height + 12
                width: 380
                height: vista.mensajeAlto ? 66 : 47
                radius: 16
                color: vista.estado === "reconocida" || vista.completa ? Tema.fondoOk
                     : vista.estado === "casi" ? Tema.fondoNaranjaSuave : Tema.fondoTarjeta
                Rectangle {
                    x: 16; anchors.verticalCenter: parent.verticalCenter
                    width: 10; height: 10; radius: 5
                    color: vista.estado === "reconocida" || vista.completa ? Tema.estadoOk
                         : vista.estado === "casi" ? Tema.acentoNaranja : Tema.bordeBoton
                }
                Texto {
                    x: 36; y: 14
                    width: 328
                    text: vista.completa ? "Las 5 señas de Saludos quedaron reconocidas. ¡Muy bien!"
                        : vista.estado === "reconocida" ? "¡Bien hecha! LESCOCam la reconoció."
                        : vista.estado === "casi" ? "Casi. Su índice quedó doblado: estírelo un poco más."
                        : "Haga la seña frente a la cámara…"
                    color: vista.estado === "reconocida" || vista.completa ? Tema.textoOk
                         : vista.estado === "casi" ? Tema.textoAcento : Tema.textoSecundario
                    peso: Font.Bold
                    tam: 14.5
                    alto: 1.1
                    wrapMode: Text.WordWrap
                }
            }

            Column {   // Acciones
                y: 431
                width: 380
                spacing: 10
                Row {
                    visible: !vista.completa
                    spacing: 10
                    Boton {
                        width: 185; alto: 50; pastilla: true
                        texto: vista.pausa ? "Reanudar" : "Pausar"
                        icono: vista.pausa ? "reproducir" : ""
                        ladoIcono: 14
                        onClic: vista.pausa = !vista.pausa
                    }
                    Boton {
                        width: 185; alto: 50; pastilla: true
                        texto: "Repetir"
                        onClic: vista.repetir()
                    }
                }
                Boton {
                    visible: !vista.completa
                    width: 380; alto: 50; pastilla: true
                    estilo: "oscuro"
                    texto: Estado.siguiente
                    onClic: vista.siguiente()
                }
                Boton {
                    visible: vista.completa
                    width: 380; alto: 50; pastilla: true
                    estilo: "oscuro"
                    texto: "Practicar de nuevo"
                    onClic: vista.practicarDeNuevo()
                }
                Boton {
                    visible: vista.completa
                    width: 380; alto: 50; pastilla: true
                    texto: "Elegir otra categoría"
                    onClic: vista.elegirOtraCategoria()
                }
            }
        }
    }
}
