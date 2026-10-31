import QtQuick
import QtQuick.Effects
import QtQuick.Window
import Lesco
import "../componentes"

// Modo Hablar (señas a voz): pantallas 07 · Hablar en vivo, 08 · Revisar el
// texto y 09 · Voz con karaoke, con todas sus variantes. Las variantes se
// resuelven leyendo `Nav.pantalla`. 09m (texto en grande) y 09r1/09r2 (cierre
// con el lente) son una ventana aparte, definida al final.
Item {
    id: vista

    readonly property string p: Nav.pantalla
    readonly property bool grande: p === "09m" || p === "09r1" || p === "09r2"
    // Detrás de la ventana grande el panel sigue mostrando la pantalla 09
    readonly property string base: grande ? "09" : p
    readonly property bool enVivo: /^07/.test(base)
    readonly property bool revisar: base === "08"
    readonly property bool voz09: /^09/.test(base)
    readonly property int paso: base === "09s" ? 1 : base === "09s2" ? 2 : base === "09s3" ? 3 : 0
    readonly property bool sonando: paso > 0
    readonly property bool silencio: base === "09v"
    readonly property real k: [1, 1.25, 1.5][Tema.escala]     // escala de texto

    // Datos de ejemplo (compartidos entre pantallas)
    property string frase: "Hola, soy Christian."
    property string voz: "Ana"
    property string velocidad: "Normal"

    readonly property var palabrasVivo: ({
        "07": [["Hola", false], ["Soy", false], ["C-H-R-I-S-T-I-A-N", true]],
        "07a": [],
        "07h": [["Hola", false], ["Soy", false]],
        "07b": [["Hola", false], ["Soy", false]]
    })
    readonly property var rutas: ({
        "09": { grande: "09m", copiar: "09k", mp3: "09g", reproducir: "09s" },
        "09v": { grande: "09m", copiar: "09k", mp3: "09g", reproducir: "09s" }
    })
    readonly property var ruta: rutas[base] || ({})
    function ir(destino) { if (destino) Nav.ir(destino) }
    // Ancho de un botón que llena lo que queda de la fila; si no entra, ocupa una fila entera
    function resto(total, usado, propio) { var r = total - usado; return r >= propio ? r : total }

    readonly property string textoDestino: enVivo ? "Haga sus señas para decirlas en voz alta"
        : revisar ? "Revise el texto. Puede corregirlo con el teclado."
        : "Listo para decir en voz alta. Toque Reproducir."

    // ── «Destino» (línea bajo la cabecera, sobre la banda azul) ───────
    Item {
        id: destino
        width: parent.width
        height: Math.max(enVivo ? 17 : 26, dtexto.implicitHeight) + (enVivo ? 6 : 8)

        Rectangle {
            visible: !vista.enVivo
            x: 16; width: 26; height: 26; radius: 13
            color: Qt.rgba(1, 1, 1, atras.pressed ? 0.28 : atras.containsMouse ? 0.2 : 0.12)
            Canvas {
                x: 6; y: 6; width: 14; height: 14
                onPaint: {
                    var c = getContext("2d")
                    c.reset()
                    c.strokeStyle = "#ffffff"; c.lineWidth = 1.925
                    c.lineCap = "round"; c.lineJoin = "round"
                    c.beginPath(); c.moveTo(9, 2); c.lineTo(4, 7); c.lineTo(9, 12); c.stroke()
                }
            }
            MouseArea {
                id: atras
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                Accessible.name: "Atrás"
                Accessible.role: Accessible.Button
                onClicked: vista.ir(vista.revisar ? "07h" : "08")
            }
        }
        Texto {
            id: dtexto
            x: vista.enVivo ? 16 : 50
            y: vista.enVivo ? 0 : Math.max(0, (26 - implicitHeight) / 2)
            width: parent.width - x - 16
            text: vista.textoDestino
            wrapMode: Text.Wrap
            color: "#c9d6ee"
            tam: 12.5 * vista.k
        }
    }

    // ── Contenido ─────────────────────────────────────────────────────
    Column {
        id: contenido
        x: 16
        y: destino.height
        width: parent.width - 32
        spacing: 10

        // 07 · cámara + texto que se dirá
        Camara {
            visible: vista.enVivo
            Item {
                anchors.fill: parent
                visible: Nav.camaraPausada
                Rectangle { anchors.fill: parent; color: Qt.rgba(10 / 255, 23 / 255, 48 / 255, 0.86) }
                Column {
                    anchors.centerIn: parent
                    spacing: 6
                    Texto { anchors.horizontalCenter: parent.horizontalCenter; text: "❚❚  En pausa"; color: "#ffffff"; peso: Font.DemiBold; tam: 18 }
                    Texto { anchors.horizontalCenter: parent.horizontalCenter; text: "La cámara no ve nada. Lo escrito sigue aquí."; color: Qt.rgba(1, 1, 1, 0.85); tam: 13 }
                }
            }
        }
        Texto {
            visible: vista.enVivo
            width: parent.width
            text: vista.base === "07a" ? "Esperando su primera seña…" : "Lo que se dirá en voz alta"
            wrapMode: Text.Wrap
            color: Tema.textoSecundario
            tam: 13 * vista.k
        }
        Tarjeta {
            visible: vista.enVivo
            width: parent.width
            minimo: 132
            Flow {
                id: flujoPalabras
                width: parent.width
                spacing: 2     // vertical; el espacio de 9 px entre palabras va en cada palabra
                Repeater {
                    model: vista.palabrasVivo[vista.base] || []
                    Item {
                        width: Math.min(palabra.implicitWidth + 9, flujoPalabras.width)
                        height: palabra.implicitHeight
                        Texto {
                            id: palabra
                            width: parent.width - 9
                            fontSizeMode: Text.HorizontalFit
                            minimumPixelSize: 12
                            text: modelData[0]
                            peso: Font.ExtraBold
                            tam: Tema.tamTitulo
                            font.letterSpacing: -0.3
                            alto: 1.3
                            color: modelData[1] ? Tema.textoApagado : Tema.textoPrincipal
                        }
                    }
                }
                Item {   // cursor
                    width: 4; height: Tema.tamTitulo * 1.3
                    Rectangle {
                        width: 2.5; height: Tema.tamTitulo; radius: 2
                        anchors.centerIn: parent
                        color: Tema.acentoNaranja
                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            running: !Tema.reducirMovimiento
                            NumberAnimation { to: 0; duration: 500; easing.type: Easing.InOutQuad }
                            NumberAnimation { to: 1; duration: 500; easing.type: Easing.InOutQuad }
                        }
                    }
                }
            }
        }

        // 08 · revisar el texto
        Tarjeta {
            visible: vista.revisar
            width: parent.width
            minimo: 80
            Column {
                width: parent.width
                TextEdit {
                    id: editor
                    width: parent.width
                    text: vista.frase
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    color: Tema.textoPrincipal
                    selectionColor: Tema.fondoSeleccion
                    selectedTextColor: Tema.textoSobreSeleccion
                    font.family: Tema.fuente
                    font.pointSize: 26 * vista.k * 0.75
                    font.weight: Font.ExtraBold
                    Accessible.name: "Texto que se dirá en voz alta"
                    onTextChanged: if (activeFocus) vista.frase = text
                    Keys.onReturnPressed: focus = false
                    Keys.onEnterPressed: focus = false
                }
                Row {
                    spacing: 4
                    Icono { nombre: "escribir"; lado: 13; color: Tema.textoSecundario; anchors.verticalCenter: parent.verticalCenter }
                    Texto { text: "Toque el texto para corregirlo con el teclado"; color: Tema.textoSecundario; tam: 13 * vista.k }
                }
            }
        }
        Grupo {
            visible: vista.revisar
            titulo: "Voz"
            opciones: ["Ana", "Diego", "Lucía"]
            valor: vista.voz
            onElegir: (o) => vista.voz = o
        }
        Grupo {
            visible: vista.revisar
            titulo: "Velocidad"
            opciones: ["Lenta", "Normal", "Rápida"]
            valor: vista.velocidad
            onElegir: (o) => vista.velocidad = o
        }
        Texto {
            visible: vista.revisar
            topPadding: 8
            width: parent.width
            text: "Se genera en este equipo y queda en el historial."
            wrapMode: Text.Wrap
            color: Tema.textoSecundario
            tam: 12.5 * vista.k
        }

        // 09 · voz con karaoke
        Rectangle {
            id: tarjetaVoz
            visible: vista.voz09
            width: parent.width
            height: columnaVoz.implicitHeight + 30
            radius: 16
            color: Tema.fondoTarjeta

            Column {
                id: columnaVoz
                x: 16; y: 16
                width: parent.width - 32
                spacing: 14

                Texto {   // la frase, con karaoke cuando suena
                    width: parent.width
                    textFormat: Text.StyledText
                    wrapMode: Text.Wrap
                    peso: Font.Bold
                    tam: Tema.tamPalabraActual
                    lineHeightMode: Text.FixedHeight
                    lineHeight: Tema.tamPalabraActual * 1.07
                    height: Math.round(lineCount * lineHeight)
                    text: {
                        var pal = vista.frase.split(" ")
                        var activa = vista.paso - 1
                        var oscuro = String(Tema.textoPrincipal), apagado = String(Tema.textoApagado)
                        return pal.map(function (w, i) {
                            var t = i === activa ? "<u>" + w + "</u>" : w
                            return "<font color='" + (!vista.sonando || i <= activa ? oscuro : apagado) + "'>" + t + "</font>"
                        }).join(" ")
                    }
                }

                // Salida de audio
                Rectangle {
                    width: parent.width
                    height: Math.max(36, filaSalida.implicitHeight + 16)
                    radius: 8
                    color: vista.silencio ? Tema.fondoAviso : "transparent"
                    Row {
                        id: filaSalida
                        x: vista.silencio ? 10 : 0
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - x - 12
                        spacing: 8
                        Icono {
                            y: 2
                            nombre: vista.silencio ? "alerta" : "hablar"
                            lado: vista.silencio ? 18 : 16
                            color: vista.silencio ? Tema.estadoAviso : Tema.textoSecundario
                        }
                        Texto {
                            width: parent.width - 26
                            wrapMode: Text.Wrap
                            alto: 1.4
                            tam: Tema.tamNota
                            color: vista.silencio ? Tema.textoPrincipal : Tema.textoSecundario
                            text: vista.silencio ? "El equipo está en silencio. Suba el volumen para que la otra persona escuche."
                                : (vista.sonando ? "Sonando en " : "") + "Altavoces Realtek · volumen 70 %"
                        }
                    }
                }

                // Reproductor
                Rectangle {
                    width: parent.width
                    height: Math.max(vista.sonando ? 72 : 60, reproductor.implicitHeight + 24)
                    radius: 18
                    color: Tema.fondoPanel
                    Row {
                        id: reproductor
                        x: 12
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 12
                        Rectangle {   // botón de reproducir (solo suena)
                            visible: vista.sonando
                            width: 48; height: 48; radius: 24
                            color: Tema.fondoSeleccion
                            anchors.verticalCenter: parent.verticalCenter
                            Icono { anchors.centerIn: parent; nombre: "reproducir"; lado: 20; color: Tema.acentoNaranja }
                        }
                        Onda {
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(60, tarjetaVoz.width - 32 - 12 - 14 - 12 - tiempo.implicitWidth
                                            - (vista.sonando ? 60 : 0))
                            barra: vista.sonando ? 4 : 6
                            progreso: vista.paso / 3
                            vivo: vista.sonando
                        }
                        Texto {
                            id: tiempo
                            anchors.verticalCenter: parent.verticalCenter
                            text: "0:0" + vista.paso + " / 0:03"
                            tam: Tema.tamNota
                            alto: 1.4
                            font.family: Tema.fuente
                        }
                    }
                }
            }
        }
        Texto {
            visible: vista.voz09
            width: parent.width
            text: "Voz " + vista.voz + " · " + vista.velocidad
            color: Tema.textoSecundario
            tam: 13 * vista.k
        }
        Boton {
            visible: vista.voz09
            texto: "Mostrar el texto en grande"
            estilo: "texto"
            colorTexto: Tema.textoPrincipal
            onClic: vista.ir(vista.ruta.grande)
        }
    }

    // ── Avisos (07b, 09g, 09k) ────────────────────────────────────────
    Aviso {
        visible: vista.base === "07b"
        icono: "borrar-palabra"
        mensaje: "Se borró «CHRISTIAN»"
        accion: "Deshacer"
        onAccionar: vista.ir("07")
    }
    Aviso {
        visible: vista.base === "09g"
        icono: "descargar"
        mensaje: "MP3 guardado en Descargas"
        accion: "Abrir carpeta"
        onAccionar: vista.ir("09")
    }
    Aviso {
        visible: vista.base === "09k"
        icono: "copiar"
        mensaje: "Texto copiado. Péguelo con Ctrl+V"
    }

    // ── «Acciones» (barra inferior) ───────────────────────────────────
    Rectangle {
        id: acciones
        anchors.bottom: parent.bottom
        width: parent.width
        height: (vista.enVivo ? filaVivo : vista.revisar ? filaRevisar : filaVoz).implicitHeight + 27
        color: Tema.fondoTarjeta
        Rectangle { width: parent.width; height: 1; color: Tema.bordeLinea }

        // 07
        Flow {
            id: filaVivo
            visible: vista.enVivo
            x: 16; y: 13
            width: parent.width - 32
            spacing: 8
            Boton {
                id: bPausar
                texto: Nav.camaraPausada ? "Reanudar" : "Pausar"
                icono: Nav.camaraPausada ? "reproducir" : "pausar"
                pastilla: true
                onClic: Nav.camaraPausada = !Nav.camaraPausada
            }
            Boton {
                id: bBorrar
                icono: "borrar-palabra"; ladoIcono: 22
                pastilla: true
                width: 44
                Accessible.name: "Borrar palabra"
                onClic: if (vista.base !== "07b") vista.ir("07b")
            }
            Boton {
                texto: "Terminar"
                estilo: "oscuro"
                pastilla: true
                imagen: Qt.resolvedUrl("../../assets/imagenes/flechas-terminar.svg")
                width: vista.resto(filaVivo.width, bPausar.width + bBorrar.width + 16, implicitWidth)
                onClic: vista.ir("08")
            }
        }

        // 08
        Flow {
            id: filaRevisar
            visible: vista.revisar
            x: 16; y: 13
            width: parent.width - 32
            spacing: 8
            Boton {
                id: bNuevo
                texto: "Empezar de nuevo"
                pastilla: true
                onClic: vista.ir("07a")
            }
            Boton {
                texto: "Generar voz"
                estilo: "oscuro"
                pastilla: true
                imagen: Qt.resolvedUrl("../../assets/imagenes/chevrones-voz.svg")
                width: vista.resto(filaRevisar.width, bNuevo.width + 8, implicitWidth)
                onClic: vista.ir("09")
            }
        }

        // 09
        Flow {
            id: filaVoz
            visible: vista.voz09
            x: 16; y: 13
            width: parent.width - 32
            spacing: 8
            Boton {
                id: bCopiar
                texto: "Copiar"
                pastilla: true
                onClic: vista.ir(vista.ruta.copiar)
            }
            Boton {
                id: bMp3
                texto: "Guardar MP3"
                pastilla: true
                onClic: vista.ir(vista.ruta.mp3)
            }
            Boton {
                texto: vista.base === "09e" ? "Nuevo texto" : "Reproducir"
                estilo: "oscuro"
                pastilla: true
                icono: vista.base === "09e" ? "" : "reproducir"
                ladoIcono: 20
                colorIcono: Tema.acentoNaranja
                width: vista.resto(filaVoz.width, bCopiar.width + bMp3.width + 16, implicitWidth)
                onClic: vista.ir(vista.base === "09e" ? "07a" : vista.ruta.reproducir)
            }
        }
    }

    // Ctrl+V en 09k pega el texto en el chat (09p); Enter en 09p lo envía (09e)
    Shortcut { sequence: "Ctrl+V"; enabled: vista.base === "09k"; onActivated: Nav.ir("09p") }
    Shortcut { sequences: ["Return", "Enter"]; enabled: vista.base === "09p"; onActivated: Nav.ir("09e") }

    // ── Piezas locales ────────────────────────────────────────────────
    component Tarjeta: Rectangle {
        default property alias contenido: interior.data
        property int minimo: 132
        height: Math.max(minimo, interior.childrenRect.height + 32)
        radius: 16
        color: Tema.fondoTarjeta
        Item { id: interior; x: 18; y: 16; width: parent.width - 36; height: childrenRect.height }
    }

    // Grupo de chips («Voz», «Velocidad»)
    component Grupo: Column {
        id: grupo
        property string titulo
        property var opciones: []
        property string valor
        signal elegir(string opcion)
        width: parent.width
        spacing: 6
        topPadding: 10
        Texto { text: grupo.titulo; peso: Font.Bold; color: Tema.textoSecundario; tam: 13 * vista.k }
        Flow {
            width: parent.width
            spacing: 8
            Repeater {
                model: grupo.opciones
                Rectangle {
                    id: chip
                    readonly property bool marcado: modelData === grupo.valor
                    width: etiqueta.implicitWidth + 28
                    height: Math.max(39, etiqueta.implicitHeight + 16)
                    radius: height / 2
                    color: marcado ? Tema.fondoSeleccion : (zona.containsMouse ? Tema.fondoChip : "transparent")
                    border.width: 1.5
                    border.color: marcado ? Tema.fondoSeleccion : Tema.bordeControl
                    Accessible.role: Accessible.RadioButton
                    Accessible.name: modelData
                    Accessible.checked: marcado
                    Texto {
                        id: etiqueta
                        anchors.centerIn: parent
                        text: modelData
                        peso: chip.marcado ? Font.ExtraBold : Font.Bold
                        tam: Tema.tamBoton
                        alto: 1.3
                        color: chip.marcado ? Tema.textoSobreSeleccion : Tema.textoPrincipal
                    }
                    MouseArea {
                        id: zona
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: grupo.elegir(modelData)
                    }
                }
            }
        }
    }

    // Aviso flotante sobre la barra de acciones
    component Aviso: Rectangle {
        id: aviso
        property string icono
        property string mensaje
        property string accion
        signal accionar()
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: acciones.top
        anchors.bottomMargin: 12
        width: Math.min(parent.width - 32, fila.implicitWidth + 22)
        height: Math.max(accion ? 60 : 36, fila.implicitHeight + 16)
        radius: 12
        color: Tema.fondoTarjeta
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.22)
            shadowVerticalOffset: 6
            shadowBlur: 0.6
        }
        Row {
            id: fila
            x: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12
            Icono { anchors.verticalCenter: parent.verticalCenter; nombre: aviso.icono; lado: 20; color: Tema.estadoOkTexto }
            Texto { anchors.verticalCenter: parent.verticalCenter; text: aviso.mensaje; tam: Tema.tamNota; alto: 1.4 }
            Boton {
                visible: aviso.accion !== ""
                anchors.verticalCenter: parent.verticalCenter
                texto: aviso.accion
                estilo: "texto"
                onClic: aviso.accionar()
            }
        }
    }

    // Forma de onda: barras con las alturas de Figma. Las que ya sonaron van
    // en azul; mientras suena, las azules «respiran».
    component Onda: Item {
        id: onda
        property real barra: 6
        property real progreso: 0
        property bool vivo: false
        property real fase: 0
        readonly property var alturas: [9, 36, 16, 34, 22, 31, 28, 26, 32, 20, 35, 13, 36, 12, 35, 19, 33, 25, 29, 30, 23, 34, 17, 36, 10, 36]
        readonly property int sonadas: Math.round(progreso * 26)
        height: 36
        Behavior on progreso { NumberAnimation { duration: Tema.reducirMovimiento ? 0 : 400; easing.type: Easing.Linear } }
        NumberAnimation on fase {
            from: 0; to: 1; duration: 900
            loops: Animation.Infinite
            running: onda.vivo && !Tema.reducirMovimiento
        }
        Repeater {
            model: 26
            Rectangle {
                required property int index
                readonly property bool activa: index < onda.sonadas
                readonly property real pulso: (onda.vivo && activa && !Tema.reducirMovimiento)
                    ? 1 - 0.22 * (0.5 + 0.5 * Math.sin((onda.fase + index * 0.13) * 2 * Math.PI)) : 1
                x: index * (onda.width - onda.barra) / 25
                width: onda.barra
                height: onda.alturas[index] * pulso
                y: (36 - height) / 2
                radius: 2
                color: activa ? Tema.textoPrincipal : Tema.fondoOnda
            }
        }
    }

    // ── 09m · Texto en grande, y 09r1/09r2 · cierre con el lente ──────
    Window {
        id: ventanaGrande
        transientParent: null
        flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        color: Tema.fondoTarjeta
        title: "LESCOCam · texto en grande"
        visible: vista.grande
        width: Screen.width
        height: Screen.height
        x: Screen.virtualX
        y: Screen.virtualY
        onVisibleChanged: if (visible) raise()

        readonly property bool cerrando: vista.p === "09r1" || vista.p === "09r2"

        // 09m
        Column {
            anchors.centerIn: parent
            spacing: 28
            visible: !ventanaGrande.cerrando
            width: Math.min(parent.width - 64, 1100)

            Texto {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: vista.frase
                peso: Font.ExtraBold
                tam: 96 * vista.k
                alto: 1.08
            }
            Texto {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: "Muéstrele esta pantalla a la otra persona"
                color: Tema.textoSecundario
                tam: 16 * vista.k
            }
            Boton {
                anchors.horizontalCenter: parent.horizontalCenter
                texto: "Cerrar"
                onClic: Nav.ir(Tema.reducirMovimiento ? "09" : "09r1")
            }
        }

        // 09r1: aparece el lente · 09r2: LESCOCam completo
        Row {
            id: logotipo
            anchors.centerIn: parent
            spacing: 1.4
            visible: ventanaGrande.cerrando
            readonly property bool completo: vista.p === "09r2"
            Texto {
                text: "LESC"; peso: Font.ExtraBold; tam: 134.4; alto: 1.3
                opacity: logotipo.completo ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: Tema.animNormal } }
            }
            Item {
                width: 99; height: 99
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: -4
                Rectangle {
                    anchors.fill: parent
                    radius: width / 2
                    color: "transparent"
                    border.width: 20.3
                    border.color: Tema.textoPrincipal
                }
                Rectangle {
                    x: 36; y: 36; width: 27; height: 27; radius: 13.5
                    color: Tema.acentoNaranja
                    opacity: logotipo.completo ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Tema.animNormal } }
                }
            }
            Texto {
                text: "Cam"; tam: 134.4; alto: 1.3
                opacity: logotipo.completo ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: Tema.animNormal } }
            }
        }

        Shortcut { sequence: "Esc"; onActivated: Nav.pulsarEscape() }
    }
}
