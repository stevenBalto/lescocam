import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// E · Primer uso (pantallas 22–26b): el asistente centrado de 920×580.
// Cada variante se resuelve leyendo Nav.pantalla. El Window que lo carga toma
// implicitWidth/implicitHeight, que incluyen un margen para la sombra.
Item {
    id: raiz

    readonly property int margen: 60
    implicitWidth: 920 + margen * 2
    implicitHeight: 580 + margen * 2

    readonly property string p: Nav.pantalla
    readonly property bool esPractica: /^25/.test(p)
    readonly property bool esListo: /^26/.test(p)
    readonly property bool movida: p === "26b"   // la burbuja de la miniatura

    // ── Datos por pantalla ────────────────────────────────────────────
    readonly property var datos: ({
        "22":   { paso: 1, titulo: "Sus señas, en texto o en voz", atras: "", sigue: "23" },
        "23":   { paso: 2, titulo: "Así lo verá la cámara", atras: "22", sigue: "" },
        "23n":  { paso: 2, titulo: "Así lo verá la cámara", atras: "22", sigue: "" },
        "23b":  { paso: 2, titulo: "Así lo verá la cámara", atras: "22", sigue: "24" },
        "24":   { paso: 3, titulo: "Ubíquese frente a la cámara", atras: "23b", sigue: "" },
        "24ok": { paso: 3, titulo: "Ubíquese frente a la cámara", atras: "23b", sigue: "25" },
        "25":   { paso: 4, titulo: "Haga la seña de «Hola»", atras: "24ok", sigue: "" },
        "25b":  { paso: 4, titulo: "Ahora toque Terminar", atras: "25", sigue: "" },
        "25c":  { paso: 4, titulo: "Toque la palabra con ola", atras: "25", sigue: "" },
        "25d":  { paso: 4, titulo: "Elija la palabra correcta", atras: "25", sigue: "" },
        "25e":  { paso: 4, titulo: "¡Muy bien! Ya sabe usarlo", atras: "25", sigue: "26" },
        "26":   { paso: 5, titulo: "Todo listo", atras: "25e", sigue: "01r" },
        "26b":  { paso: 5, titulo: "Todo listo", atras: "25e", sigue: "01r" }
    })
    readonly property var d: datos[p] || datos["22"]

    readonly property var explicaciones: ({
        "22": "LESCOCam vive en una <b><font color='#ffffff'>burbuja</font></b> que flota sobre sus apps. Tóquela, haga señas LESCO frente a la cámara y el texto aparece donde usted esté escribiendo.",
        "camara": "Cara, manos y pecho dentro de las esquinas naranjas. Así LESCOCam puede leer cada seña.",
        "encuadre": "Con luz de frente, a un brazo de distancia. Cara, manos y pecho dentro del cuadro.",
        "practica": "Este chat es de práctica: nada se envía.",
        "listo": "La burbuja se queda en la pantalla, encima de sus apps. Muévala a donde le quede cómoda. También puede abrir LESCOCam con el teclado."
    })
    readonly property string explicacion: p === "22" ? explicaciones["22"]
        : /^23/.test(p) ? explicaciones["camara"]
        : /^24/.test(p) ? explicaciones["encuadre"]
        : esPractica ? explicaciones["practica"] : explicaciones["listo"]

    // Medidas de la cabecera y de las cartas (en px de Figma, dentro de la ventana)
    readonly property real alturaBanda: p === "22" ? 284 : /^23/.test(p) ? 284 : /^24/.test(p) ? 260 : esPractica ? 196 : 270
    readonly property real cartasY: p === "22" ? 204 : /^23/.test(p) ? 200 : /^24/.test(p) ? 173 : esPractica ? 154 : 206
    readonly property real pieY: esPractica ? 503 : 497
    readonly property real pieAlto: esPractica ? 77 : 83
    readonly property real botonAlto: esPractica ? 48 : 50

    // Ventana: fondo, esquinas y sombra
    Rectangle {
        x: raiz.margen; y: raiz.margen
        width: 920; height: 580
        radius: 18
        color: Tema.fondoPanel
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.45)
            shadowVerticalOffset: 30
            shadowBlur: 1.0
        }
    }

    Redondeado {
        id: ventana
        x: raiz.margen; y: raiz.margen
        width: 920; height: 580
        radio: 18

        Rectangle { width: parent.width; height: raiz.alturaBanda; color: Tema.fondoBanda }

        // ── Encabezado ────────────────────────────────────────────────
        Item {
            id: marca
            x: 30
            y: raiz.esPractica ? 20 : 22
            width: 860
            height: raiz.esPractica ? 34 : 38

            Redondeado {
                id: iconoApp
                width: marca.height; height: marca.height
                radio: 10
                Image {
                    anchors.fill: parent
                    source: Qt.resolvedUrl("../../assets/imagenes/icono-app.png")
                    sourceSize: Qt.size(width * 2, height * 2)
                    smooth: true
                }
            }
            Logotipo {
                x: marca.height + 12
                anchors.verticalCenter: parent.verticalCenter
                tam: raiz.esPractica ? 17.664 : 19.968
            }
            Row {   // «Paso N de 5» + barritas
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                Linea {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Paso " + raiz.d.paso + " de 5"
                    peso: Font.Bold; tam: 13.5; lh: 1.33
                    color: "#c9d6ee"
                }
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 5
                    Repeater {
                        model: 5
                        Rectangle {
                            width: 30; height: 6; radius: 3
                            color: index < raiz.d.paso ? Tema.acentoNaranja : Qt.rgba(1, 1, 1, 0.2)
                        }
                    }
                }
            }
        }

        // Título (en «Todo listo» va con un círculo naranja y una marca)
        Rectangle {
            visible: raiz.esListo
            x: 30; y: 75
            width: 46; height: 46; radius: 23
            color: Tema.acentoNaranja
            Icono { anchors.centerIn: parent; nombre: "terminar"; lado: 24; color: Tema.textoSobreNaranja }
        }
        Linea {
            x: raiz.esListo ? 90 : 30
            y: raiz.esListo ? 72 : raiz.esPractica ? 64 : p === "22" ? 76 : 74
            text: raiz.d.titulo
            peso: Font.ExtraBold
            tam: raiz.esPractica ? 32 : 40
            lh: 1.06
            font.letterSpacing: raiz.esPractica ? -0.8 : -1
            color: "#ffffff"
        }
        Parrafo {
            x: 30
            y: raiz.esPractica ? 116 : p === "22" ? 134 : raiz.esListo ? 136 : 130
            width: raiz.esListo ? 620 : p === "22" ? 560 : 580
            textFormat: Text.StyledText
            text: raiz.explicacion
            tam: raiz.esPractica ? 15 : 16
            lh: raiz.esPractica ? 1.33 : 1.5
            color: "#c9d6ee"
        }

        // ── Cartas ────────────────────────────────────────────────────
        Item {
            id: cartas
            y: raiz.cartasY
            width: parent.width
            height: parent.height - y

            // 22 · Bienvenida
            Item {
                visible: raiz.p === "22"
                Carta {
                    x: 30; width: 408; height: 275
                    Redondeado {
                        x: 8; y: 8; width: 392; height: 259; radio: 16
                        Rectangle { anchors.fill: parent; color: "#0b1630" }
                        Camara {
                            x: -9.97; y: -2.59
                            scale: 411.94 / 368
                            transformOrigin: Item.TopLeft
                            estado: ""
                        }
                        Rectangle {   // leyenda con degradado
                            y: 181; width: parent.width; height: 78
                            gradient: Gradient {
                                GradientStop { position: 0; color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0) }
                                GradientStop { position: 1; color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.92) }
                            }
                            Linea { x: 16; y: 26; text: "Véalo en LESCO"; peso: Font.Bold; tam: 15; color: "#ffffff" }
                            Linea { x: 16; y: 48; text: "Le explicamos LESCOCam en señas · 40 s"; tam: 12.5; color: "#c9d6ee" }
                        }
                        Rectangle {   // botón «Ver video»
                            x: 166; y: 85.5; width: 60; height: 60; radius: 30
                            color: Tema.acentoNaranja
                            layer.enabled: true
                            layer.effect: MultiEffect {
                                shadowEnabled: true
                                shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.35)
                                shadowVerticalOffset: 6
                                shadowBlur: 0.6
                            }
                            Icono { anchors.centerIn: parent; nombre: "reproducir"; lado: 22; color: "#ffffff" }
                        }
                    }
                }
                Carta {
                    x: 454; width: 436; height: 275
                    Linea { x: 22; y: 20; text: "ASÍ SE VE MIENTRAS HACE SEÑAS"; peso: Font.ExtraBold; tam: 12.5; color: Tema.textoSecundario; font.letterSpacing: 0.375 }
                    Row {
                        x: 22; y: 48; spacing: 7
                        Rectangle { width: 8; height: 8; radius: 4; color: Tema.estadoEnVivo; anchors.verticalCenter: parent.verticalCenter }
                        Linea { text: "En vivo · LESCOCam está leyendo sus manos"; tam: 12.5; color: Tema.textoSecundario }
                    }
                    Row {
                        x: 22; y: 76; spacing: 9
                        Linea { text: "Hola"; peso: Font.ExtraBold; tam: 30; lh: 1.31; font.letterSpacing: -0.3 }
                        Linea { text: "soy"; peso: Font.ExtraBold; tam: 30; lh: 1.31; font.letterSpacing: -0.3 }
                        Linea { text: "C-H-R-I-S"; peso: Font.ExtraBold; tam: 30; lh: 1.31; font.letterSpacing: -0.3; color: Tema.textoApagado }
                        Rectangle { width: 2.5; height: 30; radius: 2; color: Tema.acentoNaranja; anchors.verticalCenter: parent.verticalCenter }
                    }
                    Rectangle {
                        x: 22; y: 127; width: 392; height: 48; radius: 14
                        color: "#ffffff"; border.width: 1.5; border.color: "#3d6be0"
                        Linea { x: 15.5; anchors.verticalCenter: parent.verticalCenter; text: "Hola, soy"; tam: 16; color: "#1c1b1f" }
                    }
                }
            }

            // 23 · 23b · 23n · Cámara
            Item {
                visible: /^23/.test(raiz.p)
                Carta {
                    x: 30; width: 492; height: 279
                    Redondeado {
                        x: 8; y: 8; width: 476; height: 236; radio: 16
                        Rectangle { anchors.fill: parent; color: "#0b1630" }

                        // 23 y 23n: cámara apagada con las cuatro esquinas
                        Item {
                            visible: raiz.p !== "23b"
                            anchors.fill: parent
                            Esquinas { x: 22; y: 40; width: 432; height: 174 }
                            Column {
                                x: (parent.width - width) / 2; y: 86
                                spacing: 10
                                Icono { anchors.horizontalCenter: parent.horizontalCenter; nombre: "camara"; lado: 34; color: "#c9d6ee" }
                                Linea {
                                    text: raiz.p === "23n" ? "No se permitió la cámara" : "La cámara está apagada"
                                    peso: Font.Bold; tam: 15
                                    color: raiz.p === "23n" ? "#ffc58a" : "#ffffff"
                                }
                            }
                            Rectangle {
                                x: 12; y: 12; height: 26; width: etiqueta.implicitWidth + 31; radius: 9
                                color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.55)
                                Rectangle { x: 9; y: 9.5; width: 7; height: 7; radius: 3.5; color: "#aab8d0" }
                                Linea { id: etiqueta; x: 22; anchors.verticalCenter: parent.verticalCenter; text: "Apagada"; peso: Font.Bold; tam: 12.5; color: "#ffffff" }
                            }
                        }

                        // 23b: la cámara se ve, con borde verde y aviso
                        Item {
                            visible: raiz.p === "23b"
                            anchors.fill: parent
                            Camara {
                                x: -4.76; y: -17.68
                                scale: 485.52 / 368
                                transformOrigin: Item.TopLeft
                                estado: ""
                            }
                            Rectangle {
                                anchors.fill: parent; radius: 16
                                color: "transparent"; border.width: 3; border.color: Tema.estadoOk
                            }
                            Rectangle {
                                x: (parent.width - width) / 2; y: 190
                                width: encontrada.implicitWidth + 28; height: 32; radius: 16
                                color: Tema.fondoOk
                                Linea { id: encontrada; anchors.centerIn: parent; text: "✓ Cámara encontrada · Integrada HD"; peso: Font.ExtraBold; tam: 13.5; color: Tema.textoOk }
                            }
                        }
                    }
                    Row {
                        x: 14; y: 252; spacing: 14
                        Compromiso { texto: "No se guarda video" }
                        Compromiso { texto: "Nada sale de este equipo" }
                        Compromiso { texto: "Puede apagarla" }
                    }
                }
                Carta {
                    x: 538; width: 352; height: 279

                    // 23 y 23n: pedir el permiso
                    Column {
                        visible: raiz.p !== "23b"
                        anchors.centerIn: parent
                        width: 304
                        spacing: 14
                        Linea {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: raiz.p === "23n" ? "NO SE PERMITIÓ LA CÁMARA" : "UN PERMISO, UNA SOLA VEZ"
                            peso: Font.ExtraBold; tam: 12.5; font.letterSpacing: 0.375
                            color: raiz.p === "23n" ? Tema.textoAcento : Tema.textoSecundario
                        }
                        Parrafo {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            textFormat: Text.StyledText
                            text: raiz.p === "23n"
                                ? "Sin cámara LESCOCam no puede leer sus señas. Tóquelo otra vez y elija «Sí»."
                                : "Windows le va a preguntar si LESCOCam puede usar la cámara. Elija <b><font color='" + Tema.textoAcento + "'>«Sí»</font></b>."
                            tam: 15; lh: 1.45
                        }
                        Boton {
                            anchors.horizontalCenter: parent.horizontalCenter
                            texto: raiz.p === "23n" ? "Intentar de nuevo" : "Permitir cámara"
                            icono: "camara"; ladoIcono: 18
                            estilo: "primario"; pastilla: true; sombra: true
                            alto: 48; relleno: 22
                            onClic: Nav.abrir("Capa · Windows pide la cámara")
                        }
                    }

                    // 23b: cámara lista
                    Column {
                        visible: raiz.p === "23b"
                        anchors.centerIn: parent
                        width: 304
                        spacing: 14
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 52; height: 52; radius: 26
                            color: Tema.fondoOk
                            Linea { anchors.centerIn: parent; text: "✓"; peso: Font.ExtraBold; tam: 24; color: Tema.textoOk }
                        }
                        Linea { anchors.horizontalCenter: parent.horizontalCenter; text: "Cámara lista"; peso: Font.ExtraBold; tam: 20 }
                        Linea { anchors.horizontalCenter: parent.horizontalCenter; text: "La vemos bien. Ahora ubíquese frente a ella."; tam: 15; color: Tema.textoSecundario }
                    }
                }
            }

            // 24 · 24ok · Encuadre
            Item {
                visible: /^24/.test(raiz.p)
                readonly property bool ok: raiz.p === "24ok"
                Carta {
                    x: 30; width: 492; height: 306
                    Redondeado {
                        x: 8; y: 8; width: 476; height: 290; radio: 16
                        Rectangle { anchors.fill: parent; color: "#0b1630" }
                        Camara {
                            x: -4.76; y: -10.68
                            scale: 485.52 / 368
                            transformOrigin: Item.TopLeft
                            estado: "Cámara · solo en este equipo"
                            colorPunto: "#ff6b6b"
                        }
                        Rectangle {
                            visible: raiz.p === "24ok"
                            anchors.fill: parent; radius: 16
                            color: "transparent"; border.width: 3; border.color: Tema.estadoOk
                        }
                        Aviso { cx: 238; cy: 72.5; texto: "Cara" }
                        Aviso { cx: 79.5; cy: 223.5; texto: "Manos" }
                        Aviso { cx: 442; cy: 26.5; texto: "Luz" }
                    }
                }
                Carta {
                    x: 538; width: 352; height: 306
                    Column {
                        anchors.centerIn: parent
                        width: 304
                        spacing: 12
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 64; height: 64; radius: 32
                            color: raiz.p === "24ok" ? Tema.fondoOk : Tema.fondoChip
                            Linea {
                                anchors.centerIn: parent
                                text: raiz.p === "24ok" ? "✓" : "…"
                                peso: Font.ExtraBold; tam: 28
                                color: raiz.p === "24ok" ? Tema.textoOk : Tema.textoPrincipal
                            }
                        }
                        Linea {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: raiz.p === "24ok" ? "¡Así está perfecto!" : "Revisando…"
                            peso: Font.ExtraBold; tam: 22
                        }
                        Linea {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: raiz.p === "24ok" ? "LESCOCam ve bien su cara y sus manos." : "Quédese quieto un momento."
                            tam: 15; color: Tema.textoSecundario
                        }
                    }
                }
            }

            // 25 … 25e · Práctica
            Item {
                visible: raiz.esPractica
                Practica { }
            }

            // 26 · 26b · Listo
            Item {
                visible: raiz.esListo
                Carta {
                    x: 30; width: 448; height: 273
                    Redondeado {   // escritorio en miniatura
                        x: 8; y: 8; width: 432; height: 257; radio: 16
                        Rectangle {
                            anchors.fill: parent
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: "#1f2f55" }
                                GradientStop { position: 1; color: "#5470a0" }
                            }
                        }
                        Rectangle {   // ventana de chat
                            x: 16; y: 16; width: 242; height: 197; radius: 8
                            color: "#ffffff"
                            Linea { x: 10; y: 8; text: "Soporte UTN"; peso: Font.Bold; tam: 11; color: "#1c1b1f" }
                            Rectangle { y: 28; width: parent.width; height: 1; color: "#e6e8ee" }
                        }
                        Rectangle { y: 229; width: parent.width; height: 28; color: "#1c2333" }

                        // La burbuja: clic o arrastre la mueve (26 ↔ 26b)
                        Item {
                            id: burbuja
                            x: raiz.movida ? 135 : 350
                            y: raiz.movida ? 47 : 93
                            width: 56; height: 56
                            Behavior on x { NumberAnimation { duration: Tema.animNormal; easing.type: Easing.OutCubic } }
                            Behavior on y { NumberAnimation { duration: Tema.animNormal; easing.type: Easing.OutCubic } }
                            Redondeado {
                                anchors.fill: parent
                                radio: 28
                                Image {
                                    anchors.fill: parent
                                    source: Qt.resolvedUrl("../../assets/imagenes/icono-app.png")
                                    sourceSize: Qt.size(112, 112)
                                    smooth: true
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                Accessible.name: "Burbuja"
                                onClicked: (m) => { if (Math.abs(m.x - inicio.x) + Math.abs(m.y - inicio.y) <= 8) Nav.ir(raiz.p === "26" ? "26b" : "26") }
                                // Arrastrar también la mueve: se decide al soltar si se desplazó
                                property point inicio
                                onPressed: (m) => inicio = Qt.point(m.x, m.y)
                                onReleased: (m) => { if (Math.abs(m.x - inicio.x) + Math.abs(m.y - inicio.y) > 8) Nav.ir(raiz.p === "26" ? "26b" : "26") }
                            }
                        }
                        Rectangle {   // indicación junto a la burbuja
                            x: raiz.movida ? 104 : 331.9
                            y: raiz.movida ? 108 : 155
                            width: rotulo.implicitWidth + 18; height: 26; radius: 9
                            color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.92)
                            Behavior on x { NumberAnimation { duration: Tema.animNormal; easing.type: Easing.OutCubic } }
                            Behavior on y { NumberAnimation { duration: Tema.animNormal; easing.type: Easing.OutCubic } }
                            Linea {
                                id: rotulo
                                anchors.centerIn: parent
                                text: raiz.movida ? "¡Así! Quedó aquí" : "Arrástrela ↕"
                                peso: Font.ExtraBold; tam: 12; color: "#ffffff"
                            }
                        }
                    }
                }
                Carta {
                    x: 494; width: 396; height: 273
                    Linea { x: 20; y: 18; text: "ATAJOS DE TECLADO"; peso: Font.ExtraBold; tam: 12.5; color: Tema.textoSecundario; font.letterSpacing: 0.375 }
                    Atajo { y: 34; texto: "Escribir"; teclas: ["Ctrl", "Alt", "E"]; glifo: "escribir" }
                    Atajo { y: 86; texto: "Hablar"; teclas: ["Ctrl", "Alt", "H"]; glifo: "hablar"; linea: true }
                    Atajo { y: 139; texto: "Pegar lo último"; teclas: ["Ctrl", "Alt", "V"]; glifo: "pegar"; linea: true }
                    Atajo { y: 192; texto: "Cerrar el panel sin borrar"; teclas: ["Esc"]; glifo: "cerrar"; linea: true }
                }
            }
        }

        // ── Pie ───────────────────────────────────────────────────────
        Rectangle {
            id: pie
            y: raiz.pieY
            width: parent.width; height: raiz.pieAlto
            color: Tema.fondoTarjeta
            Rectangle { width: parent.width; height: 1; color: Tema.bordeLinea }

            Texto {
                visible: raiz.esListo
                x: 26; anchors.verticalCenter: parent.verticalCenter
                textFormat: Text.StyledText
                alto: 1
                text: "Puede volver a ver esto en <b><font color='" + Tema.textoPrincipal + "'>Ajustes › Acerca de</font></b>"
                tam: 13.5; color: Tema.textoSecundario
            }

            Row {
                anchors.right: parent.right
                anchors.rightMargin: 26
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                Boton {
                    visible: raiz.d.atras !== ""
                    texto: "Atrás"; pastilla: true; alto: raiz.botonAlto
                    width: 92
                    onClic: Nav.ir(raiz.d.atras)
                }
                Boton {
                    texto: raiz.esListo ? "Empezar a usar LESCOCam" : "Continuar"
                    estilo: "oscuro"; pastilla: true; alto: raiz.botonAlto
                    width: raiz.esListo ? 288 : raiz.esPractica ? 210 : 220
                    habilitado: raiz.d.sigue !== ""
                    imagen: Qt.resolvedUrl("../../assets/imagenes/flechas-terminar.svg")
                    onClic: Nav.ir(raiz.d.sigue)
                }
            }
        }
    }

    // ══ Piezas locales ═══════════════════════════════════════════════

    // Texto de una línea con el interlineado de Figma (múltiplo del tamaño)
    component Linea: Texto {
        property real lh: 1.31
        lineHeightMode: Text.FixedHeight
        lineHeight: tam * lh
    }

    // Texto de varias líneas
    component Parrafo: Linea {
        wrapMode: Text.WordWrap
    }

    // Recorte con esquinas redondeadas (el contenido va adentro)
    component Redondeado: Item {
        property real radio: 16
        default property alias contenido: marco.data
        Item {
            id: marco
            anchors.fill: parent
            layer.enabled: true
            layer.effect: MultiEffect { maskEnabled: true; maskSource: mascara }
        }
        Item {
            id: mascara
            anchors.fill: parent
            layer.enabled: true
            visible: false
            Rectangle { anchors.fill: parent; radius: parent.parent.radio }
        }
    }

    // Carta blanca de 22 px de radio con sombra
    component Carta: Item {
        default property alias contenido: interior.data
        height: 275
        Rectangle {
            anchors.fill: parent
            radius: 22
            color: Tema.fondoTarjeta
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.3)
                shadowVerticalOffset: 12
                shadowBlur: 0.8
            }
        }
        Item { id: interior; anchors.fill: parent }
    }

    // Logotipo: «LESC» ExtraBold + lente + «Cam» Regular
    component Logotipo: Row {
        property real tam: 19.968
        spacing: 0.2
        Texto { text: "LESC"; peso: Font.ExtraBold; tam: parent.tam; alto: 1; font.letterSpacing: -tam * 0.035; color: "#ffffff" }
        Image {
            anchors.verticalCenter: parent.verticalCenter
            source: Qt.resolvedUrl("../../assets/imagenes/lente-blanco.svg")
            width: parent.tam * 0.7396; height: width
            sourceSize: Qt.size(width * 3, height * 3)
        }
        Texto { text: "Cam"; tam: parent.tam; alto: 1; font.letterSpacing: -tam * 0.02; color: "#ffffff" }
    }

    // ✓ + texto, bajo la cámara
    component Compromiso: Row {
        property string texto
        spacing: 5
        Linea { text: "✓"; peso: Font.ExtraBold; tam: 13; color: Tema.estadoOk }
        Linea { text: parent.texto; tam: 13; color: Tema.textoSecundario }
    }

    // Cuatro esquinas naranjas de encuadre
    component Esquinas: Item {
        readonly property int lado: 22
        readonly property int grosor: 3
        Repeater {
            model: [[0, 0], [1, 0], [1, 1], [0, 1]]
            Item {
                x: modelData[0] ? parent.width - parent.lado : 0
                y: modelData[1] ? parent.height - parent.lado : 0
                width: parent.lado; height: parent.lado
                Rectangle { width: parent.width; height: parent.parent.grosor; y: modelData[1] ? parent.height - height : 0; color: Tema.acentoNaranja }
                Rectangle { height: parent.height; width: parent.parent.grosor; x: modelData[0] ? parent.width - width : 0; color: Tema.acentoNaranja }
            }
        }
    }

    // Etiqueta sobre la cámara en «Encuadre» («Cara», «Manos», «Luz»)
    component Aviso: Rectangle {
        property real cx
        property real cy
        property string texto
        readonly property bool listo: raiz.p === "24ok"
        x: cx - width / 2; y: cy - height / 2
        width: etiquetaAviso.implicitWidth + 22; height: 29; radius: 14
        color: listo ? Tema.fondoOk : Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.65)
        Linea {
            id: etiquetaAviso
            anchors.centerIn: parent
            text: (parent.listo ? "✓ " : "") + parent.texto
            peso: Font.ExtraBold; tam: 13
            color: parent.listo ? Tema.textoOk : "#ffffff"
        }
    }

    // Fila de «Atajos de teclado»
    component Atajo: Item {
        property string texto
        property var teclas: []
        property string glifo
        property bool linea: false
        x: 20; width: 356; height: 53
        Rectangle { visible: parent.linea; width: parent.width; height: 1; color: Tema.bordeLinea }
        Item {
            x: 0; y: (parent.height - 22) / 2; width: 30; height: 22
            Row {
                visible: glifo === "escribir"
                anchors.centerIn: parent; spacing: 1
                Linea { text: "Aa"; peso: Font.ExtraBold; tam: 16 }
                Rectangle { width: 2; height: 15; color: Tema.acentoNaranja; anchors.verticalCenter: parent.verticalCenter }
            }
            Linea {
                visible: glifo === "hablar"
                anchors.centerIn: parent
                textFormat: Text.StyledText
                text: "<font color='" + Tema.acentoNaranja + "'>«</font>»"
                peso: Font.ExtraBold; tam: 16
            }
            Image {
                visible: glifo === "pegar"
                anchors.centerIn: parent
                source: Qt.resolvedUrl("../../assets/imagenes/atajo-pegar.svg")
                width: 16; height: 16; sourceSize: Qt.size(48, 48)
            }
            Icono { visible: glifo === "cerrar"; anchors.centerIn: parent; nombre: "cerrar"; lado: 13 }
        }
        Linea { x: 42; anchors.verticalCenter: parent.verticalCenter; text: parent.texto; peso: Font.ExtraBold; tam: 15 }
        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            Repeater {
                model: teclas
                Rectangle {
                    width: Math.max(34, tecla.implicitWidth + 18); height: 32; radius: 8
                    color: Tema.fondoTarjeta
                    border.width: 1.5; border.color: Tema.bordeBoton
                    Rectangle { z: -1; x: 0; y: 2; width: parent.width; height: parent.height; radius: 8; color: Tema.bordeBoton }
                    Linea { id: tecla; anchors.centerIn: parent; text: modelData; peso: Font.ExtraBold; tam: 13 }
                }
            }
        }
    }

    // Burbuja de ayuda oscura («Guía»); `punta`: dónde apunta ("" = ninguna)
    component Guia: Item {
        property string texto
        property string punta: ""
        property real puntaPos: 20          // distancia de la punta al borde de la burbuja
        width: etiquetaGuia.implicitWidth + 24
        height: 36
        Rectangle {
            visible: parent.punta !== ""
            width: 14.14; height: 14.14
            rotation: 45
            color: cuerpoGuia.color
            x: parent.punta === "izq" ? -7 : parent.puntaPos - 7
            y: parent.punta === "arriba" ? -7 : parent.punta === "abajo" ? parent.height - 7 : parent.puntaPos - 7
        }
        Rectangle { id: cuerpoGuia; anchors.fill: parent; radius: 10; color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.94) }
        Linea { id: etiquetaGuia; x: 12; anchors.verticalCenter: parent.verticalCenter; text: parent.texto; peso: Font.Bold; tam: 13.5; color: "#ffffff" }
    }

    // Botón pequeño del panel de práctica
    component Mini: Rectangle {
        property string texto
        property string icono
        property string imagen
        property bool oscuro: false
        property bool resaltado: false
        signal clic()
        height: 36; radius: 18
        color: oscuro ? Tema.fondoSeleccion : Tema.fondoTarjeta
        border.width: oscuro ? 0 : 1.5
        border.color: Tema.bordeBoton
        implicitWidth: contenidoMini.implicitWidth + 24
        Rectangle {   // aro naranja de «Toque Terminar»
            visible: parent.resaltado
            anchors.fill: parent; anchors.margins: -3.5; radius: height / 2
            color: "transparent"; border.width: 3; border.color: Tema.acentoNaranja
        }
        Row {
            id: contenidoMini
            anchors.centerIn: parent
            spacing: 6
            Image {
                visible: parent.parent.imagen !== ""
                anchors.verticalCenter: parent.verticalCenter
                source: parent.parent.imagen
                width: 20; height: 16; sourceSize: Qt.size(40, 32)
            }
            Icono {
                visible: parent.parent.icono !== ""
                anchors.verticalCenter: parent.verticalCenter
                nombre: parent.parent.icono
                lado: parent.parent.icono === "pausar" ? 14 : 20
                color: parent.parent.oscuro ? Tema.textoSobreSeleccion : Tema.textoPrincipal
            }
            Linea {
                visible: text !== ""
                anchors.verticalCenter: parent.verticalCenter
                text: parent.parent.texto
                peso: Font.ExtraBold; tam: 13
                color: parent.parent.oscuro ? Tema.textoSobreSeleccion : Tema.textoPrincipal
            }
        }
        MouseArea {
            anchors.fill: parent
            enabled: parent.clicable
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: parent.clic()
        }
        property bool clicable: false
    }

    // Chat de práctica + panel LESCOCam en miniatura (pantallas 25–25e)
    component Practica: Item {
        id: pr
        readonly property string s: raiz.p
        readonly property var estados: ({
            "25":  { palabra: "", campo: "", enviado: false },
            "25b": { palabra: "Hola", campo: "Hola", enviado: false },
            "25c": { palabra: "Yo", campo: "Hola, <u>yo</u>", enviado: true },
            "25d": { palabra: "Yo", campo: "Hola, <u>yo</u>", enviado: true },
            "25e": { palabra: "Soy", campo: "Hola, soy", enviado: true }
        })
        readonly property var e: estados[s] || estados["25"]

        // Chat
        Item {
            x: 30; width: 516; height: 333
            Rectangle {
                anchors.fill: parent; radius: 20; color: Tema.fondoTarjeta
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.3)
                    shadowVerticalOffset: 12; shadowBlur: 0.8
                }
            }
            Row {
                x: 16; y: 12; spacing: 8
                Linea { text: "Soporte UTN"; peso: Font.Bold; tam: 14; color: "#1c1b1f"; lh: 1.31 }
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: practicaTxt.implicitWidth + 16; height: 19; radius: 8
                    color: Tema.fondoNaranjaSuave
                    Linea { id: practicaTxt; anchors.centerIn: parent; text: "Práctica"; peso: Font.ExtraBold; tam: 11.5; color: Tema.textoAcento }
                }
            }
            Rectangle { y: 43; width: parent.width; height: 1; color: Tema.bordeLinea }
            Rectangle {   // mensaje enviado
                visible: pr.e.enviado
                x: parent.width - 16 - width; y: 280 - 12 - 8 - height
                width: enviadoTxt.implicitWidth + 24; height: 33; radius: 14
                color: "#3d6be0"
                Linea { id: enviadoTxt; anchors.centerIn: parent; text: "Hola"; tam: 14; color: "#ffffff" }
            }
            Rectangle {   // campo «Mensaje»
                x: 12; y: 280; width: 492; height: 41; radius: 12
                color: Tema.fondoTarjeta
                border.width: 1.5; border.color: "#3d6be0"
                Row {
                    x: 12; anchors.verticalCenter: parent.verticalCenter
                    spacing: 1
                    Linea { visible: pr.e.campo !== ""; textFormat: Text.StyledText; text: pr.e.campo; tam: 15; color: "#1c1b1f"; anchors.verticalCenter: parent.verticalCenter }
                    Rectangle { width: 2; height: 18; color: "#3d6be0"; anchors.verticalCenter: parent.verticalCenter }
                }
            }
        }

        // Panel LESCOCam
        Item {
            x: 560; width: 330; height: 333
            Redondeado {
                anchors.fill: parent; radio: 20
                Rectangle { anchors.fill: parent; color: Tema.fondoPanel }
                Rectangle { width: parent.width; height: 78; color: Tema.acentoNaranja }
                Rectangle {   // selector de modo
                    x: 12; y: 10; width: 182; height: 32; radius: 14
                    color: Qt.rgba(1, 1, 1, 0.28)
                    Rectangle {
                        x: 3; y: 3; width: 93; height: 26; radius: 11; color: "#ffffff"
                        Row {
                            anchors.centerIn: parent; spacing: 4
                            Linea { text: "Aa"; peso: Font.ExtraBold; tam: 12.5; color: "#0d2d6d"; anchors.verticalCenter: parent.verticalCenter }
                            Rectangle { width: 2; height: 11; color: Tema.acentoNaranja; anchors.verticalCenter: parent.verticalCenter }
                            Linea { text: "Escribir"; peso: Font.ExtraBold; tam: 12.5; color: "#0d2d6d"; anchors.verticalCenter: parent.verticalCenter }
                        }
                    }
                    Row {
                        x: 96 + 10; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                        Linea { text: "«»"; peso: Font.ExtraBold; tam: 12.5; color: "#0d2d6d" }
                        Linea { text: "Hablar"; peso: Font.ExtraBold; tam: 12.5; color: "#0d2d6d" }
                    }
                }
                Redondeado {   // cámara
                    x: 12; y: 52; width: 306; height: 104; radio: 12
                    Rectangle { anchors.fill: parent; color: "#0b1630" }
                    Camara {
                        x: -3.06; y: -48.08
                        scale: 312.12 / 368
                        transformOrigin: Item.TopLeft
                        estado: ""
                    }
                }
                Rectangle {   // texto escrito
                    x: 12; y: 164; width: 306
                    height: Math.max(64, textoPanel.implicitHeight + 20)
                    radius: 12; color: Tema.fondoTarjeta
                    Column {
                        id: textoPanel
                        x: 12; y: 10
                        spacing: 10
                        Linea {
                            visible: pr.e.palabra === ""
                            text: "Esperando su primera seña…"; tam: 13; color: Tema.textoSecundario
                        }
                        Row {
                            visible: pr.e.palabra !== ""
                            spacing: 6
                            Item {
                                width: palabraTxt.implicitWidth; height: palabraTxt.implicitHeight
                                Linea {
                                    id: palabraTxt
                                    text: pr.e.palabra
                                    peso: Font.ExtraBold; tam: 24; lh: 1.31
                                    color: pr.s === "25c" || pr.s === "25d" ? Tema.textoAcento : Tema.textoPrincipal
                                }
                                Ola {
                                    visible: pr.s === "25c" || pr.s === "25d"
                                    width: parent.width
                                    anchors.top: palabraTxt.baseline
                                    anchors.topMargin: 2
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: pr.s === "25c"
                                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: Nav.ir("25d")
                                }
                            }
                            Rectangle { width: 2.5; height: 24; radius: 2; color: Tema.acentoNaranja; anchors.verticalCenter: parent.verticalCenter }
                        }
                        Row {   // alternativas (25d)
                            visible: pr.s === "25d"
                            spacing: 6
                            Repeater {
                                model: ["YO", "SOY", "SER", "Deletrear"]
                                Rectangle {
                                    id: alternativa
                                    width: altTxt.implicitWidth + 24; height: 28; radius: 10
                                    color: Tema.fondoChip
                                    Rectangle {
                                        visible: modelData === "SOY"
                                        anchors.fill: parent; anchors.margins: -2.5; radius: 12.5
                                        color: "transparent"; border.width: 2.5; border.color: Tema.acentoNaranja
                                    }
                                    Linea { id: altTxt; anchors.centerIn: parent; text: modelData; peso: Font.ExtraBold; tam: 14 }
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        Accessible.name: modelData
                                        onClicked: Nav.ir("25e")
                                    }
                                }
                            }
                        }
                    }
                }
                Rectangle {   // acciones
                    y: 274; width: parent.width; height: 59
                    color: Tema.fondoTarjeta
                    Rectangle { width: parent.width; height: 1; color: Tema.bordeLinea }
                    Mini { x: 12; y: 11; width: 86; texto: "Pausar"; icono: "pausar" }
                    Mini { x: 104; y: 11; width: 45; icono: "borrar-palabra" }
                    Mini {
                        x: 155; y: 11; width: 163
                        texto: "Terminar"; oscuro: true
                        imagen: Qt.resolvedUrl("../../assets/imagenes/flechas-terminar.svg")
                        resaltado: pr.s === "25b"
                        clicable: pr.s === "25b"
                        onClic: Nav.ir("25c")
                    }
                }
            }
        }

        // Guías sobre el panel (coordenadas de la ventana − 0, la franja empieza en y = 154)
        Guia {
            visible: pr.s === "25"
            x: 573; y: 266 - 154; texto: "Haga la seña de «Hola» frente a la cámara"
        }
        Guia {
            visible: pr.s === "25b"
            x: 755; y: 393 - 154; texto: "Toque Terminar"
            punta: "abajo"; puntaPos: 42
        }
        Guia {
            visible: pr.s === "25c"
            x: 635; y: 326 - 154; texto: "Tóquela para corregirla"
            punta: "izq"; puntaPos: 18
        }
        Guia {
            visible: pr.s === "25d"
            x: 631; y: 415 - 154; texto: "Elija «SOY»"
            punta: "arriba"; puntaPos: 52
        }
    }
}
