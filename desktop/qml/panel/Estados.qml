import QtQuick
import Lesco
import "../componentes"

// D · Estados y errores (pantallas 16–21b). La cabecera ya la dibuja el panel.
// Cada variante se resuelve leyendo Nav.pantalla.
Item {
    id: vista

    readonly property string p: Nav.pantalla
    // Pantallas con el texto escrito y los botones Pausar / Borrar / Terminar
    readonly property bool conTexto: ["17", "18", "21", "21b"].indexOf(p) >= 0

    // Estado de la cámara (pastilla de arriba a la izquierda) por pantalla
    readonly property var camaras: ({
        "16":  { estado: "Cargando", punto: "#aab8d0" },
        "17":  { estado: "En pausa · manos fuera", punto: "#ffc857" },
        "18":  { estado: "Poca luz", punto: "#ffc857" },
        "19":  { estado: "Cámara ocupada", punto: "#aab8d0" },
        "20":  { estado: "Sin permiso", punto: "#ff6b6b" },
        "21":  { estado: "Cámara · solo en este equipo", punto: "#ff6b6b" },
        "21b": { estado: "Cámara · solo en este equipo", punto: "#ff6b6b" }
    })
    readonly property var cam: camaras[p] || camaras["21"]

    // Aviso en el panel (17, 18, 19)
    readonly property var avisos: ({
        "17": { icono: "alerta", color: Tema.estadoAviso, titulo: "Sus manos salieron por la derecha",
                texto: "Mueva las manos al centro. Lo escrito sigue aquí." },
        "18": { icono: "luz", color: Tema.estadoAviso, titulo: "Hay poca luz",
                texto: "Ponga una luz frente a usted. Su cara también comunica." },
        "19": { icono: "camara", color: Tema.estadoEnVivo, titulo: "Otra app usa la cámara",
                texto: "Windows deja usar la cámara a una sola app a la vez. Puede elegir otra cámara." }
    })
    readonly property var aviso: avisos[p]

    readonly property var borrar: ({ "17": "03b", "18": "03b", "21": "03g", "21b": "03g" })

    Column {
        id: arriba
        width: parent.width

        // «Destino»: a qué app y campo va el texto
        Row {
            x: 16
            height: 23
            spacing: 7
            Rectangle { width: 7; height: 7; radius: 3.5; color: "#4cc38a"; y: 6 }
            Linea {
                textFormat: Text.StyledText
                text: "Escribe en <b><font color='#ffffff'>Soporte UTN</font></b> · campo «Mensaje»"
                color: "#c9d6ee"
                tam: 12.5
            }
        }

        Column {
            x: 16
            width: parent.width - 32
            spacing: 10

            // ── Cámara ────────────────────────────────────────────────
            Camara {
                estado: vista.cam.estado
                colorPunto: vista.cam.punto
                mostrarEscena: vista.conTexto && vista.p !== "17" || vista.p === "18"

                // 16 · Cargando el reconocimiento
                Column {
                    visible: vista.p === "16"
                    anchors.centerIn: parent
                    spacing: 10
                    Image {
                        anchors.horizontalCenter: parent.horizontalCenter
                        source: Qt.resolvedUrl("../../assets/imagenes/sena-abierta.svg")
                        width: 42; height: 50.4
                        sourceSize: Qt.size(width * 2, height * 2)
                    }
                    Linea {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Preparando el reconocimiento…"
                        peso: Font.Bold; tam: Tema.tamBoton; lh: 1.3
                        color: "#f2f5fa"
                    }
                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 200; height: 6; radius: 3
                        color: "#2a4170"
                        Rectangle { width: 124; height: 6; radius: 3; color: Tema.acentoNaranja }
                    }
                    Linea {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Solo la primera vez · 62 %"
                        tam: Tema.tamNota
                        color: "#aab8d0"
                    }
                }

                // 17 · Manos fuera del cuadro: escena sin manos y borde iluminado
                Image {
                    visible: vista.p === "17"
                    anchors.fill: parent
                    source: Qt.resolvedUrl("../../assets/imagenes/camara-escena-sin-manos.svg")
                    sourceSize: Qt.size(width * 2, height * 2)
                }
                Rectangle {
                    visible: vista.p === "17"
                    x: 304; width: 64; height: parent.height
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: Qt.rgba(255 / 255, 199 / 255, 87 / 255, 0) }
                        GradientStop { position: 1; color: Qt.rgba(255 / 255, 199 / 255, 87 / 255, 0.55) }
                    }
                }
                Linea {
                    visible: vista.p === "17"
                    x: 342; y: 88
                    text: "›"
                    peso: Font.Bold; tam: 40; alto: 0.65
                    color: "#ffe8b0"
                }

                // 19 y 20: ícono de cámara y mensaje al centro
                Column {
                    visible: vista.p === "19" || vista.p === "20"
                    anchors.centerIn: parent
                    spacing: 10
                    Icono {
                        anchors.horizontalCenter: parent.horizontalCenter
                        nombre: "camara"; lado: 36
                        color: "#aab8d0"
                    }
                    Linea {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: vista.p === "19" ? "Otra app está usando la cámara" : "LESCOCam no tiene permiso"
                        peso: Font.Bold; tam: Tema.tamBoton; lh: 1.3
                        color: "#f2f5fa"
                    }
                }
            }

            // 16 · explicación debajo de la cámara
            Parrafo {
                visible: vista.p === "16"
                width: parent.width
                text: "Preparando LESCOCam. Solo pasa la primera vez y tarda menos de 1 minuto. No necesita internet."
                color: Tema.textoSecundario
                tam: 13
            }

            // ── Aviso en el panel (17, 18, 19) ────────────────────────
            Rectangle {
                visible: !!vista.aviso
                width: parent.width
                height: textos.implicitHeight + 24
                radius: Tema.radioControl
                color: Tema.fondoAviso

                Icono {
                    x: 14; y: 12
                    nombre: vista.aviso ? vista.aviso.icono : "alerta"
                    color: vista.aviso ? vista.aviso.color : Tema.estadoAviso
                    lado: 22
                }
                Column {
                    id: textos
                    x: 48; y: 12
                    width: parent.width - 48 - 12 - 88 - 14
                    spacing: 2
                    Parrafo {
                        width: parent.width
                        text: vista.aviso ? vista.aviso.titulo : ""
                        peso: Font.Bold; tam: Tema.tamBoton; lh: 1.3
                    }
                    Parrafo {
                        width: parent.width
                        text: vista.aviso ? vista.aviso.texto : ""
                        color: Tema.textoSecundario
                        tam: Tema.tamPequeno
                    }
                }
                VerLesco { x: parent.width - 14 - width; y: 12 }
            }

            // ── 20 · Pasos para dar permiso ───────────────────────────
            Rectangle {
                visible: vista.p === "20"
                width: parent.width
                height: pasos.implicitHeight + 28
                radius: Tema.radioControl
                color: Tema.fondoTarjeta

                Column {
                    id: pasos
                    x: 14; y: 14
                    width: parent.width - 28
                    spacing: 8
                    Linea {
                        text: "Para dar permiso en Windows"
                        peso: Font.Bold; tam: Tema.tamBoton; lh: 1.3
                    }
                    Paso { n: "1"; texto: "Abra Configuración › Privacidad y seguridad › Cámara." }
                    Paso { n: "2"; texto: "Active «Permitir que las aplicaciones accedan a la cámara»." }
                    Paso { n: "3"; texto: "Active «LESCOCam» en la lista y vuelva aquí." }
                }
            }

            // ── 17, 18, 21, 21b · texto escrito ───────────────────────
            Linea {
                visible: vista.conTexto
                width: parent.width
                text: vista.p === "21b" ? "Deletree letra por letra" : "Últimas señas"
                color: Tema.textoSecundario
                tam: 13
            }

            Rectangle {
                visible: vista.conTexto
                width: parent.width
                height: Math.max(71, frase.implicitHeight + 32)
                radius: 16
                color: Tema.fondoTarjeta

                Column {
                    id: frase
                    x: 18; y: 16
                    width: parent.width - 36
                    spacing: 2
                    Flow {
                        width: parent.width
                        spacing: 9
                        Palabra { texto: "Soy" }
                        Palabra { texto: "Christian"; dudosa: vista.p === "18" }
                        Cursor { visible: vista.p !== "21b" }
                    }
                    Row {
                        visible: vista.p === "21b"
                        spacing: 9
                        Palabra { texto: "G · R · A ·"; color: Tema.textoApagado }
                        Cursor { }
                    }
                }
            }

            // 18 · leyenda de la palabra dudosa
            Row {
                visible: vista.p === "18"
                x: 2
                spacing: 8
                Rectangle { width: 14; height: 3; radius: 2; color: Tema.acentoNaranja; anchors.verticalCenter: parent.verticalCenter }
                Linea { text: "Dudosa: tóquela para corregir"; color: Tema.textoSecundario; tam: 12.5; lh: 1.2 }
            }

            // ── 21 · Seña desconocida (en 21b queda oculta, como en Figma) ──
            Item {
                visible: vista.p === "21"
                width: parent.width
                height: interior.implicitHeight + 27

                Rectangle { anchors.fill: parent; radius: Tema.radioControl; color: Tema.fondoTarjeta }
                Discontinuo { anchors.fill: parent; radio: Tema.radioControl; color: Tema.estadoAviso }

                Column {
                    id: interior
                    x: 15.5; y: 13.5
                    width: parent.width - 31
                    spacing: 10
                    Parrafo {
                        width: parent.width
                        text: "LESCOCam no reconoció esta seña. ¿Qué quiso decir?"
                        peso: Font.Bold; tam: Tema.tamBoton; lh: 1.3
                    }
                    Row {
                        spacing: 8
                        Item {
                            width: 24; height: 28.8
                            clip: true
                            Image {
                                source: Qt.resolvedUrl("../../assets/imagenes/sena-indice.svg")
                                width: 24; height: 30.68
                                sourceSize: Qt.size(width * 2, height * 2)
                            }
                        }
                        Linea {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "El índice no se vio bien"
                            color: Tema.textoSecundario
                            tam: Tema.tamNota
                        }
                    }
                    Flow {
                        id: opciones
                        width: parent.width
                        spacing: 6
                        Item {
                            width: deletrear.width + 2; height: deletrear.height
                            Boton {
                                id: deletrear
                                texto: "Deletrear"; icono: "deletrear"
                                onClic: Nav.ir("21b")
                            }
                        }
                        Boton {
                            texto: "Enseñarla en Mis señas"; estilo: "texto"
                            onClic: Nav.abrir("Capa · Enseñar una seña · 1")
                        }
                        Boton {
                            texto: "Ignorar"; estilo: "texto"
                            onClic: Nav.ir("03g")
                        }
                    }
                }
            }
        }
    }

    // ── «Acciones» ────────────────────────────────────────────────────
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 71
        color: Tema.fondoTarjeta
        Rectangle { width: parent.width; height: 1; color: Tema.bordeLinea }

        // 17, 18, 21, 21b: Pausar, Borrar palabra y Terminar
        Item {
            visible: vista.conTexto
            anchors.fill: parent
            Row {
                x: 16; y: 13
                spacing: 8
                Boton {
                    texto: Nav.camaraPausada ? "Seguir" : "Pausar"
                    icono: Nav.camaraPausada ? "reproducir" : "pausar"
                    pastilla: true
                    width: 108
                    onClic: Nav.camaraPausada = !Nav.camaraPausada
                }
                Boton {
                    icono: "borrar-palabra"; ladoIcono: 22
                    pastilla: true
                    width: 44
                    Accessible.name: "Borrar palabra"
                    onClic: Nav.ir(vista.borrar[vista.p] || "03g")
                }
            }
            Boton {
                x: 185; y: 13
                width: parent.width - x - 16
                texto: "Terminar"
                estilo: "oscuro"
                pastilla: true
                imagen: Qt.resolvedUrl("../../assets/imagenes/flechas-terminar.svg")
                onClic: Nav.ir("04")
            }
        }

        // 16: Cancelar y Terminar
        Item {
            visible: vista.p === "16"
            anchors.fill: parent
            Boton {
                id: cancelar
                x: 16; y: 13
                texto: "Cancelar"
                onClic: Nav.ir("01r")
            }
            Boton {
                x: cancelar.x + cancelar.width + 8; y: 13
                width: parent.width - x - 16
                texto: "Terminar"
                estilo: "oscuro"
                pastilla: true
                imagen: Qt.resolvedUrl("../../assets/imagenes/flechas-terminar.svg")
            }
        }

        // 19: Usar otra cámara y Reintentar
        Item {
            visible: vista.p === "19"
            anchors.fill: parent
            Boton {
                id: otra
                x: 16; y: 13
                texto: "Usar otra cámara"
                onClic: Nav.ir("02a")
            }
            Boton {
                x: otra.x + otra.width + 8; y: 13
                width: parent.width - x - 16
                texto: "Reintentar"
                estilo: "oscuro"
                pastilla: true
                onClic: Nav.ir("02a")
            }
        }

        // 20: Cerrar y Abrir configuración
        Item {
            visible: vista.p === "20"
            anchors.fill: parent
            Boton {
                id: cerrar
                x: 16; y: 13
                texto: "Cerrar"
                onClic: Nav.ir("01r")
            }
            Boton {
                x: cerrar.x + cerrar.width + 8; y: 13
                width: parent.width - x - 16
                texto: "Abrir configuración"
                estilo: "oscuro"
                pastilla: true
                onClic: Nav.ir("02a")
            }
        }
    }

    // ── Piezas locales ────────────────────────────────────────────────

    // Texto con el interlineado exacto de Figma (múltiplo del tamaño en px).
    // `Texto.alto` multiplica la altura natural de la fuente, que ya es ~1,3 em.
    component Linea: Texto {
        property real lh: 1.4
        lineHeightMode: Text.FixedHeight
        lineHeight: tam * lh
    }

    component Parrafo: Linea {
        wrapMode: Text.WordWrap
    }

    // Palabra del texto escrito; `dudosa` la pinta de acento con una ola
    component Palabra: Item {
        property string texto
        property bool dudosa: false
        property color color: dudosa ? Tema.textoAcento : Tema.textoPrincipal
        width: palabra.implicitWidth
        height: palabra.implicitHeight
        Linea {
            id: palabra
            text: parent.texto
            peso: Font.ExtraBold
            tam: 30
            font.letterSpacing: -0.3
            lineHeight: 39
            color: parent.color
        }
        Ola {
            visible: parent.dudosa
            width: parent.width
            anchors.top: palabra.baseline
            anchors.topMargin: 3
        }
    }

    component Cursor: Item {
        width: 4; height: 39
        Rectangle {
            width: 2.5; height: 30; radius: 2
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

    // «Video LESCO» en botón: junto a cada aviso
    component VerLesco: Rectangle {
        width: 88
        height: etiqueta.implicitHeight + 12
        radius: height / 2
        color: Tema.fondoCamara
        Row {
            x: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Icono { anchors.verticalCenter: parent.verticalCenter; nombre: "reproducir"; lado: 14; color: Tema.acentoNaranja }
            Linea { id: etiqueta; text: "LESCO"; peso: Font.Bold; tam: Tema.tamBoton; lh: 1.3; color: "#ffffff" }
        }
    }

    // Paso numerado de «Para dar permiso en Windows»
    component Paso: Row {
        property string n
        property string texto
        width: parent.width
        spacing: 10
        Rectangle {
            width: 22; height: 22; radius: 11
            color: Tema.fondoPanel
            Linea { anchors.centerIn: parent; text: n; tam: Tema.tamNota }
        }
        Parrafo {
            width: parent.width - 32
            text: parent.texto
            tam: Tema.tamPequeno
        }
    }

    // Borde de 1,5 px a rayas
    component Discontinuo: Canvas {
        property real radio: 10
        property color color: "#000000"
        onColorChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = color
            ctx.lineWidth = 1.5
            ctx.setLineDash([5, 4])
            var o = 0.75, w = width - 1.5, h = height - 1.5, r = radio
            ctx.beginPath()
            ctx.moveTo(o + r, o)
            ctx.arcTo(o + w, o, o + w, o + h, r)
            ctx.arcTo(o + w, o + h, o, o + h, r)
            ctx.arcTo(o, o + h, o, o, r)
            ctx.arcTo(o, o, o + w, o, r)
            ctx.closePath()
            ctx.stroke()
        }
    }
}
