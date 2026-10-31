import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// Base de las cuatro «Capa · Bandeja…» (Burbuja = Visible / Oculta × Destello =
// Encendido / Apagado). Es la tarjeta que se abre al tocar el ícono de LESCOCam
// en la bandeja de Windows, pegada abajo a la derecha, sobre la barra de tareas.
Item {
    id: raiz

    property bool cerrarAlTocarFuera: true
    property bool oculta: false      // Burbuja = Oculta
    property bool apagado: false     // Destello = Apagado

    readonly property string miNombre: "Capa · Bandeja" + (oculta ? " · burbuja oculta" : "") + (apagado ? " · destello apagado" : "")
    readonly property real alturaBarra: Screen.height - Screen.desktopAvailableHeight

    function irA(codigo) { Nav.ir(codigo) }
    // «SWAP» de Figma: reemplaza esta capa por otra
    function cambiarPor(capa) { Nav.cerrar(); Nav.abrir(capa) }

    // Sombra
    Rectangle {
        x: tarjeta.x; y: tarjeta.y
        width: tarjeta.width; height: tarjeta.height
        radius: tarjeta.radius
        color: Tema.fondoTarjeta
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.4)
            shadowVerticalOffset: 24
            shadowBlur: 1
            shadowScale: 0.95
        }
    }

    Rectangle {
        id: tarjeta
        width: 380
        height: 597
        radius: Tema.radioPanel
        color: Tema.fondoTarjeta
        anchors.right: parent.right
        anchors.rightMargin: 62
        anchors.bottom: parent.bottom
        anchors.bottomMargin: raiz.alturaBarra + 8

        MouseArea { anchors.fill: parent }   // los clics dentro no cierran la capa

        // ── Fondo de la parte alta ────────────────────────────────────
        Rectangle { y: 0; width: parent.width; height: 336; radius: Tema.radioPanel; color: Tema.fondoPanel }
        Rectangle { y: 168; width: parent.width; height: 168; color: Tema.fondoPanel }

        // ── Banda azul ────────────────────────────────────────────────
        Rectangle { width: parent.width; height: 86; radius: Tema.radioPanel; color: Tema.fondoBanda }
        Rectangle { y: 43; width: parent.width; height: 43; color: Tema.fondoBanda }

        // Ícono de la app (cuadrado con esquinas de 10)
        Image {
            id: iconoApp
            x: 16; y: 17
            width: 36; height: 36
            source: Qt.resolvedUrl("../../assets/imagenes/icono-app.png")
            sourceSize: Qt.size(72, 72)
            smooth: true
            visible: false
        }
        Item {
            id: mascara
            x: 16; y: 17; width: 36; height: 36
            layer.enabled: true
            visible: false
            Rectangle { anchors.fill: parent; radius: 10 }
        }
        MultiEffect {
            x: 16; y: 17; width: 36; height: 36
            source: iconoApp
            maskEnabled: true
            maskSource: mascara
        }

        Column {
            x: 62; y: 14
            spacing: 3
            Row {   // logotipo LESCOCam (en blanco: sobre la banda azul)
                spacing: 0.2
                Texto { text: "LESC"; tam: 17.66; peso: Font.ExtraBold; alto: 1.3; color: "#ffffff" }
                Item {
                    width: 13; height: 23
                    Image {
                        y: 5; width: 13; height: 13
                        source: Qt.resolvedUrl("../../assets/imagenes/lente-blanco.svg")
                        sourceSize: Qt.size(26, 26)
                    }
                }
                Texto { text: "Cam"; tam: 17.66; alto: 1.3; color: "#ffffff" }
            }
            Row {
                spacing: 6
                Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 8; height: 8; radius: 4; color: Tema.estadoCamaraLista }
                Texto { text: "Cámara lista"; tam: 12.5; alto: 1.3; color: "#c9d6ee" }
            }
        }

        // Burbuja visible / oculta
        Rectangle {
            id: cajaBurbuja
            anchors.right: parent.right; anchors.rightMargin: 16
            y: 14
            width: cajaFila.implicitWidth + 16
            height: 42
            radius: 14
            color: Qt.rgba(1, 1, 1, 0.1)
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.18)

            Row {
                id: cajaFila
                x: 10
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Texto { text: "Burbuja"; tam: 11.5; peso: Font.Bold; alto: 1.3; color: "#ffffff" }
                    Row {
                        spacing: 4
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 7; height: 7; radius: 3.5
                            color: raiz.oculta ? Tema.interruptorApagado : Tema.estadoCamaraLista
                        }
                        Texto { text: raiz.oculta ? "Oculta" : "Visible"; tam: 11.5; peso: Font.ExtraBold; alto: 1.3; color: "#ffffff" }
                    }
                }
                Interruptor {
                    anchors.verticalCenter: parent.verticalCenter
                    encendido: !raiz.oculta
                    onAlternar: raiz.alternarBurbuja()
                }
            }
            MouseArea {
                anchors.fill: parent
                z: -1
                cursorShape: Qt.PointingHandCursor
                onClicked: raiz.alternarBurbuja()
            }
        }

        // ── Tarjeta «Escribir» ────────────────────────────────────────
        Item {
            id: tarjetaEscribir
            x: 12; y: 68
            width: 356; height: 149

            Rectangle {
                anchors.fill: parent
                radius: Tema.radioPanel
                color: Tema.fondoTarjeta
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.3)
                    shadowVerticalOffset: 12
                    shadowBlur: 0.6
                    shadowScale: 0.92
                }
            }
            Texto { x: 16; y: 14; text: "Escribir"; tam: 22; peso: Font.ExtraBold; alto: 1.3 }
            Texto {
                x: 16; y: 43; width: 215
                text: "Sus señas aparecen como texto en la app abierta."
                tam: 13.5; alto: 1.2
                color: Tema.textoSecundario
                wrapMode: Text.WordWrap
            }
            Row {   // glifo grande «Aa|»
                x: 280; y: 10
                spacing: 2.75
                Texto { text: "Aa"; tam: 44; peso: Font.ExtraBold; alto: 1.3 }
                Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 2.5; height: 42; radius: 1.25; color: Tema.acentoNaranja }
            }
            Rectangle {
                id: botonEscribir
                x: 16; y: 91
                width: 326; height: 44
                radius: 22
                color: zonaEscribir.pressed ? Qt.darker(Tema.fondoSeleccion, 1.2)
                     : zonaEscribir.containsMouse ? Qt.lighter(Tema.fondoSeleccion, 1.25) : Tema.fondoSeleccion
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.18)
                    shadowVerticalOffset: 4
                    shadowBlur: 0.5
                }
                Row {
                    x: 16; anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1
                        Texto { anchors.verticalCenter: parent.verticalCenter; text: "Aa"; tam: 15; peso: Font.ExtraBold; alto: 1.3; color: Tema.textoSobreSeleccion }
                        Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 2; height: 12; radius: 1; color: Tema.acentoNaranja }
                    }
                    Texto { anchors.verticalCenter: parent.verticalCenter; text: "Empezar a escribir"; tam: 15; peso: Font.ExtraBold; alto: 1.3; color: Tema.textoSobreSeleccion }
                }
                Rectangle {
                    anchors.right: parent.right; anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    width: atajoE.implicitWidth + 14; height: 22; radius: 7
                    color: Qt.rgba(1, 1, 1, 0.18)
                    Texto { id: atajoE; anchors.centerIn: parent; text: "Ctrl+Alt+E"; tam: 11.5; peso: Font.ExtraBold; alto: 1.3; color: Tema.textoSobreSeleccion }
                }
                MouseArea {
                    id: zonaEscribir
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: raiz.irA("02a")
                }
            }
        }

        // ── Fila «Hablar» ─────────────────────────────────────────────
        Item {
            id: filaHablar
            x: 12; y: 227
            width: 356; height: 59

            Rectangle {
                anchors.fill: parent
                radius: 14
                color: zonaHablar.pressed ? Tema.fondoChip : Tema.fondoTarjeta
                border.width: zonaHablar.containsMouse ? 1 : 0
                border.color: Tema.bordeControl
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.12)
                    shadowVerticalOffset: 2
                    shadowBlur: 0.3
                }
            }
            Row {
                x: 14; anchors.verticalCenter: parent.verticalCenter
                spacing: 0
                Texto { text: "«"; tam: 20; peso: Font.ExtraBold; color: Tema.acentoNaranja; alto: 1.3 }
                Texto { text: "»"; tam: 20; peso: Font.ExtraBold; alto: 1.3 }
            }
            Column {
                x: 52; anchors.verticalCenter: parent.verticalCenter
                spacing: 1
                Texto { text: "Hablar"; tam: 15.5; peso: Font.ExtraBold; alto: 1.1 }
                Texto { text: "Sus señas, en voz alta"; tam: 12.5; alto: 1.1; color: Tema.textoSecundario }
            }
            Rectangle {
                x: 250; anchors.verticalCenter: parent.verticalCenter
                width: atajoH.implicitWidth + 14; height: 22; radius: 7
                color: Tema.fondoChip
                Texto { id: atajoH; anchors.centerIn: parent; text: "Ctrl+Alt+H"; tam: 11.5; peso: Font.ExtraBold; alto: 1.3 }
            }
            Canvas {   // flecha ›
                x: 336; anchors.verticalCenter: parent.verticalCenter
                width: 8; height: 13
                property color trazo: Tema.textoPrincipal
                onTrazoChanged: requestPaint()
                onPaint: {
                    var c = getContext("2d")
                    c.clearRect(0, 0, width, height)
                    c.strokeStyle = trazo
                    c.lineWidth = 2
                    c.lineCap = "round"; c.lineJoin = "round"
                    c.beginPath(); c.moveTo(1.5, 1.5); c.lineTo(6.5, 6.5); c.lineTo(1.5, 11.5); c.stroke()
                }
            }
            MouseArea {
                id: zonaHablar
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: raiz.irA("07a")
            }
        }

        // ── Destello al reconocer ─────────────────────────────────────
        Item {
            x: 12; y: 296
            width: 356; height: 28

            Texto { x: 14; y: 3; text: "Destello al reconocer"; tam: 13.5; peso: Font.ExtraBold; alto: 1.3 }
            Texto {
                anchors.right: parent.right; anchors.rightMargin: 64
                y: 4
                text: raiz.apagado ? "Apagado" : "Encendido"
                tam: 12.5; alto: 1.3
                color: Tema.textoSecundario
            }
            Interruptor {
                x: 302; y: 4
                encendido: !raiz.apagado
                onAlternar: raiz.alternarDestello()
            }
            MouseArea {
                anchors.fill: parent
                z: -1
                cursorShape: Qt.PointingHandCursor
                onClicked: raiz.alternarDestello()
            }
        }

        // ── Lo último ─────────────────────────────────────────────────
        Rectangle { y: 336; width: parent.width; height: 202; color: Tema.fondoTarjeta }
        Texto { x: 16; y: 348; text: "LO ÚLTIMO"; tam: 12.5; peso: Font.ExtraBold; alto: 1.3; color: Tema.textoSecundario }

        Repeater {
            model: [
                { frase: "Hola, soy Christian.", detalle: "Escrito · Soporte UTN · 3:41 p. m.", boton: "Pegar", y: 370, alto: 54 },
                { frase: "Necesito ayuda con mi matrícula.", detalle: "Hablado · voz Ana · 3:38 p. m.", boton: "Reproducir", y: 424, alto: 55 },
                { frase: "¿Me pueden enviar el comprobante?", detalle: "Escrito · Soporte UTN · 3:36 p. m.", boton: "Pegar", y: 479, alto: 55 }
            ]
            delegate: Item {
                required property var modelData
                y: modelData.y
                width: tarjeta.width
                height: modelData.alto

                Rectangle { visible: modelData.y > 370; width: parent.width; height: 1; color: Tema.bordeLinea }
                Column {
                    x: 16; anchors.verticalCenter: parent.verticalCenter
                    spacing: 1
                    Texto { text: modelData.frase; tam: 14.5; peso: Font.Bold; alto: 1.1 }
                    Texto { text: modelData.detalle; tam: 12.5; alto: 1.1; color: Tema.textoSecundario }
                }
                Pastilla {
                    anchors.right: parent.right; anchors.rightMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    texto: modelData.boton
                    icono: modelData.boton === "Reproducir" ? "reproducir" : ""
                    onClic: raiz.irA(modelData.boton === "Reproducir" ? "09s" : "06")
                }
            }
        }

        // ── Enlaces ───────────────────────────────────────────────────
        Rectangle { y: 538; width: parent.width; height: 59; radius: Tema.radioPanel; color: Tema.fondoColumna }
        Rectangle { y: 538; width: parent.width; height: 30; color: Tema.fondoColumna }
        Rectangle { y: 538; width: parent.width; height: 1; color: Tema.bordeLinea }

        Repeater {
            model: [
                { texto: "Historial", icono: "historial", capa: "12" },
                { texto: "Diccionario", icono: "diccionario", capa: "13" },
                { texto: "Práctica", icono: "practica", capa: "14a" },
                { texto: "Ajustes", icono: "ajustes", capa: "15" }
            ]
            delegate: Item {
                id: enlace
                required property var modelData
                required property int index
                x: index * 95; y: 539
                width: 95; height: 58
                activeFocusOnTab: true

                Rectangle {
                    anchors.fill: parent
                    color: zonaEnlace.containsMouse ? Tema.fondoChip : "transparent"
                    border.width: enlace.activeFocus ? 3 : 0
                    border.color: Tema.foco
                }
                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 9
                    spacing: 3
                    Icono { anchors.horizontalCenter: parent.horizontalCenter; nombre: enlace.modelData.icono; lado: 20 }
                    Texto { text: enlace.modelData.texto; tam: 12; peso: Font.ExtraBold; alto: 1.3 }
                }
                MouseArea {
                    id: zonaEnlace
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: raiz.cambiarPor(enlace.modelData.capa)
                }
                Keys.onReturnPressed: raiz.cambiarPor(modelData.capa)
                Keys.onSpacePressed: raiz.cambiarPor(modelData.capa)
            }
        }
    }

    // Interruptor «Burbuja»: visible → 01h; oculta → 01r
    function alternarBurbuja() {
        if (oculta) {
            Nav.burbujaVisible = true
            Nav.ir("01r")
        } else {
            Nav.burbujaVisible = false
            Nav.ir("01h")
        }
    }
    // Interruptor «Destello al reconocer»: cambia a la variante apagado / encendido
    function alternarDestello() {
        Nav.destello = !Nav.destello
        var nueva = "Capa · Bandeja" + (oculta ? " · burbuja oculta" : "") + (Nav.destello ? "" : " · destello apagado")
        cambiarPor(nueva)
    }
}
