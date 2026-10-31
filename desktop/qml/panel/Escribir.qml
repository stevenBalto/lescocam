import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// Modo Escribir (pantallas 02a, 02h, 02, 02b y 03, 03b, 03c, 03d, 03g, 03y,
// 03h, 03i). Lo que cambia entre variantes está en `datos`, por código de
// pantalla; los destinos son los de las interacciones de Figma.
Item {
    id: vista

    // Variantes de Figma.
    //   palabras: [texto, estilo, destino al tocarla]
    //     estilo: "" normal · "dudosa" (ola) · "caja" (seleccionada) · "apagada" (deletreando)
    //   panel: lo que va debajo de la tarjeta de texto
    //     "" nada · "leyenda" · "alternativas" · "palabra" (acciones de la palabra)
    readonly property var datos: ({
        "02a": { hint: "Esperando su primera seña…", palabras: [],
                 borrar: "02b", terminar: "01b" },
        "02h": { hint: "Toque una palabra para corregirla", palabras: [["Hola"]],
                 borrar: "02b", terminar: "01b" },
        "02":  { hint: "Toque una palabra con ola para corregirla",
                 palabras: [["Hola"], ["Yo", "dudosa", "03"]], panel: "leyenda",
                 borrar: "02b", terminar: "01b" },
        "02b": { hint: "Toque una palabra para corregirla", palabras: [["Hola"]],
                 aviso: "Se borró «YO»", terminar: "01b" },
        "03":  { hint: "¿Era «YO»? Déjela, cámbiela o deletréela",
                 palabras: [["Hola"], ["Yo", "caja"]], panel: "alternativas",
                 borrar: "02b", terminar: "01b" },
        "03b": { hint: "Toque una palabra para corregirla",
                 palabras: [["Hola"], ["Soy", "", "03"]], borrar: "02b" },
        "03c": { hint: "Toque una palabra para corregirla",
                 palabras: [["Hola"], ["Ser", "", "03"]], borrar: "02b", terminar: "04c" },
        "03d": { hint: "Deletree letra por letra. Reemplaza a «YO» al terminar.",
                 palabras: [["Hola"], ["S · O ·", "apagada"]] },
        "03g": { hint: "Toque una palabra para borrarla o corregirla",
                 palabras: [["Hola"], ["Soy", "", "03h"], ["Christian"]],
                 borrar: "03b", terminar: "04" },
        "03y": { hint: "Toque una palabra para corregirla",
                 palabras: [["Hola"], ["Yo", "", "03"]], borrar: "02b" },
        "03h": { hint: "Palabra seleccionada",
                 palabras: [["Hola"], ["Soy", "caja", "03g"], ["Christian"]], panel: "palabra",
                 borrarEsta: "03i", listo: "03g", borrar: "03b", terminar: "04" },
        "03i": { hint: "Se borró «SOY». Toque una palabra para borrarla o corregirla",
                 palabras: [["Hola"], ["Christian"]], borrar: "03b", terminar: "04" }
    })
    readonly property var d: datos[Nav.pantalla] || datos["02"]
    readonly property real tamHint: Tema.escala === 0 ? 13 : Tema.tamNota
    readonly property real tamPalabra: Tema.tamTitulo

    Column {
        id: arriba
        width: parent.width

        // «Destino»: a qué app y campo va el texto
        Row {
            x: 16
            height: 23
            spacing: 7
            Rectangle { width: 7; height: 7; radius: 3.5; color: "#4cc38a"; y: 6 }
            Texto {
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

            Camara {
                // «Cámara en pausa»
                Rectangle {
                    anchors.fill: parent
                    visible: Nav.camaraPausada
                    color: Qt.rgba(10 / 255, 23 / 255, 48 / 255, 0.86)
                    Column {
                        anchors.centerIn: parent
                        spacing: 6
                        Texto {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "❚❚  En pausa"
                            peso: Font.DemiBold
                            tam: 18
                            alto: 1
                            color: "#ffffff"
                        }
                        Texto {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "La cámara no ve nada. Lo escrito sigue aquí."
                            tam: 13
                            alto: 1
                            color: Qt.rgba(1, 1, 1, 0.85)
                        }
                    }
                }
            }

            Texto {
                width: parent.width
                text: vista.d.hint
                color: Tema.textoSecundario
                tam: vista.tamHint
                wrapMode: Tema.escala === 0 ? Text.NoWrap : Text.WordWrap
            }

            // «Texto»: lo escrito hasta ahora
            Rectangle {
                width: parent.width
                height: Math.max(132, flujo.height + 32)
                radius: 16
                color: Tema.fondoTarjeta
                Flow {
                    id: flujo
                    x: 18; y: 16
                    width: parent.width - 36
                    spacing: 9
                    Repeater {
                        model: vista.d.palabras
                        Palabra {
                            texto: modelData[0]
                            estilo: modelData[1] || ""
                            destino: modelData[2] || ""
                            tamLetra: vista.tamPalabra
                        }
                    }
                    Item {   // cursor
                        width: 4; height: vista.tamPalabra * 1.3
                        Rectangle {
                            width: 2.5; height: vista.tamPalabra; radius: 2
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

            // «Leyenda» (02)
            Row {
                x: 2
                spacing: 8
                visible: vista.d.panel === "leyenda"
                Rectangle { width: 14; height: 3; radius: 2; color: Tema.acentoNaranja; anchors.verticalCenter: parent.verticalCenter }
                Texto { text: "Dudosa: tóquela para corregir"; color: Tema.textoSecundario; tam: 12.5; alto: 1.2 }
            }

            // «Alternativas» (03)
            Rectangle {
                width: parent.width
                height: alternativas.height + 20
                radius: 16
                color: Tema.fondoTarjeta
                visible: vista.d.panel === "alternativas"
                Flow {
                    id: alternativas
                    x: 12; y: 10
                    width: parent.width - 24
                    spacing: 6
                    Alternativa { texto: "YO"; sena: "sena-indice-mediana.svg"; destino: "03y" }
                    Alternativa { texto: "SOY"; sena: "sena-indice-chica.svg"; destino: "03b" }
                    Alternativa { texto: "SER"; sena: "sena-v-chica.svg"; destino: "03c" }
                    Boton {
                        texto: "Deletrear"
                        icono: "deletrear"
                        alto: 36
                        onClic: Nav.ir("03d")
                    }
                }
            }

            // «Acciones de palabra» (03h)
            Row {
                spacing: 8
                visible: vista.d.panel === "palabra"
                Boton {
                    texto: "Borrar «SOY»"
                    icono: "borrar-palabra"
                    onClic: Nav.ir(vista.d.borrarEsta)
                }
                Boton {
                    texto: "Listo"
                    estilo: "texto"
                    onClic: Nav.ir(vista.d.listo)
                }
            }
        }
    }

    // «Aviso» con «Deshacer» (02b)
    Rectangle {
        id: aviso
        visible: !!vista.d.aviso
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: acciones.top
        anchors.bottomMargin: 12
        height: 60
        width: filaAviso.implicitWidth + 22
        radius: Tema.radioTarjeta
        color: Tema.fondoTarjeta
        layer.enabled: visible
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(13 / 255, 46 / 255, 110 / 255, 0.3)
            shadowVerticalOffset: 12
            shadowBlur: 1
        }
        Row {
            id: filaAviso
            x: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: Tema.espacio12
            Icono { anchors.verticalCenter: parent.verticalCenter; nombre: "borrar-palabra"; lado: 20; color: Tema.textoSecundario }
            Texto { anchors.verticalCenter: parent.verticalCenter; text: vista.d.aviso || ""; tam: Tema.tamPequeno; color: Tema.textoPrincipal }
            Boton {
                anchors.verticalCenter: parent.verticalCenter
                texto: "Deshacer"
                estilo: "texto"
                onClic: Nav.ir("02")
            }
        }
    }

    // «Acciones»
    Rectangle {
        id: acciones
        anchors.bottom: parent.bottom
        width: parent.width
        height: 71
        color: Tema.fondoTarjeta
        Rectangle { width: parent.width; height: 1; color: Tema.bordeLinea }

        Row {
            id: secundarias
            x: 16; y: 13
            spacing: 8
            Boton {
                texto: Nav.camaraPausada ? "Reanudar" : "Pausar"
                icono: Nav.camaraPausada ? "reproducir" : "pausar"
                pastilla: true
                onClic: Nav.camaraPausada = !Nav.camaraPausada
            }
            Boton {
                icono: "borrar-palabra"; ladoIcono: 22
                pastilla: true
                width: 44
                Accessible.name: "Borrar palabra"
                onClic: if (vista.d.borrar) Nav.ir(vista.d.borrar)
            }
        }
        // Con texto grande «Terminar» se ajusta a su contenido y queda a la derecha
        Boton {
            y: 13
            x: Tema.escala === 0 ? 185 : parent.width - 16 - width
            width: Tema.escala === 0 ? parent.width - 185 - 16 : implicitWidth
            texto: "Terminar"
            estilo: "oscuro"
            pastilla: true
            imagen: Qt.resolvedUrl("../../assets/imagenes/flechas-terminar.svg")
            onClic: if (vista.d.terminar) Nav.ir(vista.d.terminar)
        }
    }

    // Una palabra de la tarjeta de texto
    component Palabra: Item {
        id: p
        property string texto
        property string estilo
        property string destino
        property real tamLetra: 30
        readonly property bool caja: estilo === "caja"

        width: letras.implicitWidth + (caja ? 8 : 0)
        height: letras.implicitHeight

        Rectangle {
            anchors.fill: parent
            visible: p.caja
            radius: Tema.radioChico
            color: Tema.fondoNaranjaSuave
            border.width: 2
            border.color: Tema.acentoNaranja
        }
        Texto {
            id: letras
            x: p.caja ? 4 : 0
            text: p.texto
            peso: Font.ExtraBold
            tam: p.tamLetra
            font.letterSpacing: -0.3
            alto: 1.3
            color: p.estilo === "dudosa" ? Tema.textoAcento
                 : p.estilo === "apagada" ? Tema.textoApagado
                 : Tema.textoPrincipal
        }
        Ola {
            visible: p.estilo === "dudosa"
            width: parent.width
            anchors.top: letras.baseline
            anchors.topMargin: 3
        }
        MouseArea {
            anchors.fill: parent
            enabled: p.destino !== ""
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: Nav.ir(p.destino)
        }
    }

    // «Alternativa»: una opción para corregir la palabra dudosa
    component Alternativa: FocusScope {
        id: alt
        property string texto
        property string sena
        property string destino

        width: fila.implicitWidth + 20
        height: 40.8
        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: texto

        Rectangle {
            anchors.fill: parent
            radius: Tema.radioControl
            color: zona.pressed ? Tema.fondoChip : Tema.fondoTarjeta
            border.width: 1
            border.color: (zona.containsMouse || zona.pressed) ? Tema.textoPrincipal : Tema.bordeSuave
        }
        Rectangle {   // anillo de foco
            anchors.fill: parent
            anchors.margins: -3
            radius: Tema.radioControl + 3
            color: "transparent"
            border.width: 3
            border.color: Tema.foco
            visible: alt.activeFocus
        }
        Row {
            id: fila
            x: 7
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Item {
                width: 24; height: 28.8
                anchors.verticalCenter: parent.verticalCenter
                Image {
                    width: 24; height: parent.height * 1.0653
                    source: Qt.resolvedUrl("../../assets/imagenes/" + alt.sena)
                    sourceSize: Qt.size(width * 3, height * 3)
                }
            }
            Texto {
                anchors.verticalCenter: parent.verticalCenter
                text: alt.texto
                peso: Font.Bold
                tam: Tema.tamBoton
                alto: 1.3
            }
            Item { width: 5; height: 1 }
        }
        MouseArea {
            id: zona
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: Nav.ir(alt.destino)
        }
        Keys.onReturnPressed: Nav.ir(destino)
        Keys.onSpacePressed: Nav.ir(destino)
    }
}
