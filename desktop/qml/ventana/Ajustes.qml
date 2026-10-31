import QtQuick
import QtQuick.Shapes
import QtQuick.Effects
import Lesco
import "../componentes"

// Ventana «15 · Ajustes» y sus pestañas:
// 15 Burbuja y atajos, 15a Voz y audio, 15b Cámara, 15c Accesibilidad, 15d Acerca de.
MarcoVentana {
    id: vista

    readonly property string codigo: Nav.esVentana(Nav.capa) ? Nav.capa : Nav.pantalla
    readonly property var secciones: [
        { texto: "Voz y audio", codigo: "15a", icono: "hablar" },
        { texto: "Cámara", codigo: "15b", icono: "camara" },
        { texto: "Burbuja y atajos", codigo: "15", icono: "burbuja" },
        { texto: "Accesibilidad", codigo: "15c", icono: "accesibilidad" },
        { texto: "Acerca de", codigo: "15d", icono: "info" }
    ]
    readonly property var seccion: {
        for (var i = 0; i < secciones.length; i++) if (secciones[i].codigo === codigo) return secciones[i]
        return secciones[2]
    }

    // Valores de ejemplo (el motor se conecta después)
    property string velocidad: "Normal"
    property string camara: "Integrada HD"
    property string intensidad: "Normal"
    property bool ocultarPantallaCompleta: true
    property bool espejo: true
    property bool puntosMano: true
    property bool pausarSinManos: true
    property bool altoContraste: false

    function escuchar() { Nav.abrir("Capa · Aviso de ajustes · escuchar") }

    CabeceraVentana {
        titulo: "Ajustes"
        onAbrirPanel: Nav.ir("02a")
        onCerrar: Nav.cerrar()
    }

    // ── Secciones ─────────────────────────────────────────────────────
    Rectangle {
        y: 65
        width: 250; height: 585
        color: Tema.fondoColumna
        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Tema.bordeLinea }

        Column {
            x: 12; y: 16
            width: 225
            spacing: 4
            Repeater {
                model: vista.secciones
                Item {
                    id: item
                    readonly property bool activa: vista.seccion.codigo === modelData.codigo
                    width: 225; height: 48
                    activeFocusOnTab: true
                    Accessible.role: Accessible.RadioButton
                    Accessible.name: modelData.texto
                    Accessible.checked: activa

                    Rectangle {
                        anchors.fill: parent
                        radius: 14
                        color: item.activa ? Tema.fondoTarjeta : zona.containsMouse ? Tema.fondoChip : "transparent"
                        layer.enabled: item.activa
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.14)
                            shadowVerticalOffset: 2
                            shadowBlur: 0.3
                        }
                        Rectangle { visible: item.activa; width: 3; height: parent.height - 6; y: 3; radius: 1.5; color: Tema.acentoNaranja }
                    }
                    IconoSeccion {
                        x: item.activa ? 17 : 14
                        anchors.verticalCenter: parent.verticalCenter
                        nombre: modelData.icono
                        color: item.activa ? Tema.textoPrincipal : Tema.textoSecundario
                    }
                    Texto {
                        x: item.activa ? 48 : 45
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.texto
                        peso: item.activa ? Font.ExtraBold : Font.Bold
                        tam: item.activa ? 15 : 14
                        alto: 1.3
                        color: item.activa ? Tema.textoPrincipal : Tema.textoSecundario
                    }
                    Rectangle {
                        anchors.fill: parent; anchors.margins: -3; radius: 17
                        color: "transparent"; border.width: 3; border.color: Tema.foco
                        visible: item.activeFocus
                    }
                    MouseArea {
                        id: zona
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Nav.ir(modelData.codigo)
                    }
                    Keys.onReturnPressed: Nav.ir(modelData.codigo)
                    Keys.onSpacePressed: Nav.ir(modelData.codigo)
                }
            }
        }
    }

    // ── Contenido de la sección ───────────────────────────────────────
    Flickable {
        x: 250; y: 65
        width: 810; height: 585
        contentWidth: width
        contentHeight: contenido.y + contenido.height + 28
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Texto {
            x: 28; y: 22
            text: vista.seccion.texto
            peso: Font.ExtraBold
            tam: 30
            alto: 1.2
        }

        Column {
            id: contenido
            x: 28; y: 73
            width: 754
            spacing: 12

            // «Así se verá y se oirá» (Voz y audio, Accesibilidad)
            Rectangle {
                visible: vista.seccion.codigo === "15a" || vista.seccion.codigo === "15c"
                width: 754; height: 108; radius: 20
                color: Tema.fondoTarjeta
                Column {
                    x: 20; y: 31
                    spacing: 4
                    Texto { text: "ASÍ SE VERÁ Y SE OIRÁ"; color: Tema.textoSecundario; peso: Font.ExtraBold; tam: 12.5; alto: 1.2 }
                    Texto { text: "Hola, soy Christian."; peso: Font.ExtraBold; tam: Tema.tamPalabra; alto: 1.2 }
                }
                Item {
                    x: 488; y: 16
                    width: 246; height: 76
                    Item {   // Tamaño
                        width: 246; height: 26
                        Texto {
                            id: aPequena
                            y: 4.5
                            text: "A"; peso: Font.ExtraBold; tam: 13; alto: 1.2
                            activeFocusOnTab: true
                            Accessible.role: Accessible.Button
                            Accessible.name: "Texto más pequeño"
                            MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: Tema.escala = Math.max(0, Tema.escala - 1) }
                            Keys.onReturnPressed: Tema.escala = Math.max(0, Tema.escala - 1)
                            Keys.onSpacePressed: Tema.escala = Math.max(0, Tema.escala - 1)
                        }
                        Rectangle { x: 22; y: 12; width: 146; height: 2; radius: 1; color: Tema.fondoOnda }
                        Rectangle { x: 22; y: 12; width: 146 * Tema.escala / 2; height: 2; radius: 1; color: Tema.textoPrincipal }
                        Texto {
                            x: 180
                            text: "A"; peso: Font.ExtraBold; tam: 20; alto: 1.2
                            activeFocusOnTab: true
                            Accessible.role: Accessible.Button
                            Accessible.name: "Texto más grande"
                            MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: Tema.escala = Math.min(2, Tema.escala + 1) }
                            Keys.onReturnPressed: Tema.escala = Math.min(2, Tema.escala + 1)
                            Keys.onSpacePressed: Tema.escala = Math.min(2, Tema.escala + 1)
                        }
                        Texto { x: 205; y: 4.5; text: Tema.etiquetaEscala; peso: Font.ExtraBold; tam: 13; alto: 1.2 }
                    }
                    Boton {
                        x: 65; y: 36
                        width: 181
                        alto: 40
                        pastilla: true
                        estilo: "oscuro"
                        texto: "Escuchar · voz " + Estado.voz
                        icono: "reproducir"
                        colorIcono: Tema.acentoNaranja
                        ladoIcono: 14
                        onClic: vista.escuchar()
                    }
                }
            }

            // ── Voz y audio ──
            Fila {
                visible: vista.seccion.codigo === "15a"
                titulo: "Voz"; detalle: "Español latino"; anchoControl: 204
                Row {
                    spacing: 8
                    Repeater {
                        model: ["Ana", "Diego", "Lucía"]
                        Opcion { texto: modelData; activo: Estado.voz === modelData; onElegir: Estado.voz = modelData }
                    }
                }
            }
            Fila {
                visible: vista.seccion.codigo === "15a"
                titulo: "Velocidad"; anchoControl: 236
                Row {
                    spacing: 8
                    Repeater {
                        model: ["Lenta", "Normal", "Rápida"]
                        Opcion { texto: modelData; activo: vista.velocidad === modelData; onElegir: vista.velocidad = modelData }
                    }
                }
            }
            Fila {
                visible: vista.seccion.codigo === "15a"
                titulo: "Carpeta de los MP3"; detalle: "Descargas › LESCOCam"; anchoControl: 93
                Boton { width: 93; alto: 44; pastilla: true; texto: "Cambiar" }
            }

            // ── Cámara ──
            Fila {
                visible: vista.seccion.codigo === "15b"
                titulo: "Cámara"; anchoControl: 249
                Row {
                    spacing: 8
                    Repeater {
                        model: ["Integrada HD", "Logitech C920"]
                        Opcion { texto: modelData; activo: vista.camara === modelData; onElegir: vista.camara = modelData }
                    }
                }
            }
            Fila {
                visible: vista.seccion.codigo === "15b"
                titulo: "Imagen en espejo"
                detalle: "Su mano derecha aparece a la derecha de la pantalla, como al mirarse en un espejo. Así es más fácil acomodar las señas."
                anchoControl: 44
                Interruptor { nombreAccesible: "Imagen en espejo"; activo: vista.espejo; onCambio: (v) => vista.espejo = v }
            }
            Fila {
                visible: vista.seccion.codigo === "15b"
                titulo: "Mostrar los puntos de la mano"; detalle: "Ayuda a ver si la cámara la ve bien"; anchoControl: 44
                Interruptor { nombreAccesible: "Mostrar los puntos de la mano"; activo: vista.puntosMano; onCambio: (v) => vista.puntosMano = v }
            }
            Fila {
                visible: vista.seccion.codigo === "15b"
                titulo: "Pausar si no hay manos"; detalle: "Después de 3 segundos"; anchoControl: 44
                Interruptor { nombreAccesible: "Pausar si no hay manos"; activo: vista.pausarSinManos; onCambio: (v) => vista.pausarSinManos = v }
            }

            // ── Burbuja y atajos ──
            Fila {
                visible: vista.seccion.codigo === "15"
                titulo: "Mostrar la burbuja"; detalle: "Se puede ocultar y usar solo atajos o la bandeja"; anchoControl: 44
                Interruptor { nombreAccesible: "Mostrar la burbuja"; activo: Nav.burbujaVisible; onCambio: (v) => Nav.burbujaVisible = v }
            }
            Fila {
                visible: vista.seccion.codigo === "15"
                titulo: "Ocultar en pantalla completa"; detalle: "Por ejemplo, al ver un video"; anchoControl: 44
                Interruptor { nombreAccesible: "Ocultar en pantalla completa"; activo: vista.ocultarPantallaCompleta; onCambio: (v) => vista.ocultarPantallaCompleta = v }
            }
            Fila {
                visible: vista.seccion.codigo === "15"
                titulo: "Escribir"; detalle: "Abre el panel en modo Escribir"; anchoControl: 122
                Atajo { teclas: ["Ctrl", "Alt", "E"] }
            }
            Fila {
                visible: vista.seccion.codigo === "15"
                titulo: "Hablar"; detalle: "Abre el panel en modo Hablar"; anchoControl: 124
                Atajo { teclas: ["Ctrl", "Alt", "H"] }
            }
            Fila {
                visible: vista.seccion.codigo === "15"
                titulo: "Pegar lo último"; detalle: "Inserta de nuevo el último texto escrito"; anchoControl: 123
                Atajo { teclas: ["Ctrl", "Alt", "V"] }
            }
            Rectangle {
                visible: vista.seccion.codigo === "15"
                width: 754; height: 40; radius: 10
                color: Qt.rgba(173 / 255, 197 / 255, 230 / 255, 0.22)
                Texto {
                    x: 16; anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 32
                    text: "Terminar no tiene atajo: así el texto no se corta por error. Esc cierra el panel y no borra nada."
                    tam: 14
                    alto: 1.3
                    elide: Text.ElideRight
                }
            }

            // ── Accesibilidad ──
            Fila {
                visible: vista.seccion.codigo === "15c"
                titulo: "Tamaño del texto"; detalle: "En el panel y los avisos"; anchoControl: 231
                Row {
                    spacing: 8
                    Repeater {
                        model: ["100 %", "125 %", "150 %"]
                        Opcion { texto: modelData; activo: Tema.escala === index; onElegir: Tema.escala = index }
                    }
                }
            }
            Fila {
                visible: vista.seccion.codigo === "15c"
                titulo: "Destello al reconocer"; detalle: "El borde del panel brilla con cada seña"; anchoControl: 44
                Interruptor { nombreAccesible: "Destello al reconocer"; activo: Nav.destello; onCambio: (v) => Nav.destello = v }
            }
            Fila {
                visible: vista.seccion.codigo === "15c"
                titulo: "Intensidad del destello"; anchoControl: 156
                Row {
                    spacing: 8
                    Repeater {
                        model: ["Suave", "Normal"]
                        Opcion { texto: modelData; activo: vista.intensidad === modelData; onElegir: vista.intensidad = modelData }
                    }
                }
            }
            Fila {
                visible: vista.seccion.codigo === "15c"
                titulo: "Reducir movimiento"; detalle: "Sin animaciones al abrir y cerrar"; anchoControl: 44
                Interruptor { nombreAccesible: "Reducir movimiento"; activo: Tema.reducirMovimiento; onCambio: (v) => Tema.reducirMovimiento = v }
            }
            Fila {
                visible: vista.seccion.codigo === "15c"
                titulo: "Alto contraste"; detalle: "Bordes y textos más marcados"; anchoControl: 44
                Interruptor { nombreAccesible: "Alto contraste"; activo: vista.altoContraste; onCambio: (v) => vista.altoContraste = v }
            }
            Fila {
                visible: vista.seccion.codigo === "15c"
                titulo: "Tema"; anchoControl: 149
                Row {
                    spacing: 8
                    Repeater {
                        model: ["Claro", "Oscuro"]
                        Opcion { texto: modelData; activo: Tema.oscuro === (index === 1); onElegir: Tema.oscuro = index === 1 }
                    }
                }
            }

            // ── Acerca de ──
            Fila {
                visible: vista.seccion.codigo === "15d"
                titulo: "LESCOCam 0.2 · prototipo de diseño"
                detalle: "Hecho en la UTN, sede Guanacaste, por Steven Baltodano Ugarte, Christian Paniagua Castro, Reyman Barquero Ramírez y Johan Morales Chacón."
                anchoControl: 0
            }
            Fila {
                visible: vista.seccion.codigo === "15d"
                titulo: "Privacidad"
                detalle: "El reconocimiento corre en este equipo. La imagen de la cámara nunca se envía ni se guarda."
                anchoControl: 0
            }
            Fila {
                visible: vista.seccion.codigo === "15d"
                titulo: "Videos de referencia"
                detalle: "Videos de referencia de LESCO (fuente por confirmar)"
                anchoControl: 0
            }
            Fila {
                visible: vista.seccion.codigo === "15d"
                titulo: "Volver a ver el primer uso"; alto: 68; anchoControl: 126
                Boton {
                    width: 126; alto: 44; pastilla: true
                    texto: "Ver de nuevo"
                    onClic: { Nav.primerUso = true; Nav.ir("22") }
                }
            }
        }
    }

    // ── Piezas propias de Ajustes ─────────────────────────────────────
    // «Ajuste …»: tarjeta con título, detalle y un control a la derecha
    component Fila: Rectangle {
        id: fila
        property string titulo
        property string detalle
        property int anchoControl: 0
        property int alto: 0
        default property alias control: zonaControl.data

        width: 754
        height: alto > 0 ? alto : Math.max(63, textos.implicitHeight + 24)
        radius: 16
        color: Tema.fondoTarjeta

        Column {
            id: textos
            x: 18
            anchors.verticalCenter: parent.verticalCenter
            width: fila.width - 36 - (fila.anchoControl > 0 ? fila.anchoControl + 16 : 0)
            spacing: 2
            Texto { width: parent.width; text: fila.titulo; peso: Font.Bold; tam: 15; alto: 1; height: 19 }
            Texto {
                visible: fila.detalle !== ""
                width: parent.width
                text: fila.detalle
                color: Tema.textoSecundario
                tam: 14
                lineHeightMode: Text.FixedHeight
                lineHeight: 20
                wrapMode: Text.WordWrap
            }
        }
        Item {
            id: zonaControl
            anchors.right: parent.right
            anchors.rightMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            width: childrenRect.width
            height: childrenRect.height
        }
    }

    // Teclas de un atajo («Ctrl» «Alt» «E»)
    component Atajo: Row {
        property var teclas: []
        spacing: 4
        Repeater {
            model: parent.teclas
            Item {
                width: letra.implicitWidth + 22; height: 34
                Rectangle { y: 3; width: parent.width; height: 31; radius: 6; color: Tema.bordeControl }
                Rectangle {
                    width: parent.width; height: 31; radius: 6
                    color: Tema.fondoBarra
                    border.width: 1
                    border.color: Tema.bordeControl
                    Texto { id: letra; anchors.centerIn: parent; text: modelData; tam: 14; alto: 1.2 }
                }
            }
        }
    }

    // Íconos de 19 px de las secciones
    component IconoSeccion: Item {
        id: ico
        property string nombre
        property color color: Tema.textoPrincipal
        width: 19; height: 19

        Icono { visible: ico.nombre === "hablar" || ico.nombre === "camara"; anchors.centerIn: parent; nombre: ico.nombre; lado: 19; color: ico.color }
        Item {   // burbuja: círculo con punto naranja
            visible: ico.nombre === "burbuja"
            anchors.fill: parent
            Rectangle { anchors.centerIn: parent; width: 16; height: 16; radius: 8; color: "transparent"; border.width: 1.7; border.color: ico.color }
            Rectangle { anchors.centerIn: parent; width: 5; height: 5; radius: 2.5; color: Tema.acentoNaranja }
        }
        Item {   // información
            visible: ico.nombre === "info"
            anchors.fill: parent
            Rectangle { anchors.centerIn: parent; width: 16; height: 16; radius: 8; color: "transparent"; border.width: 1.7; border.color: ico.color }
            Rectangle { x: 8.6; y: 4.6; width: 1.8; height: 1.8; radius: 0.9; color: ico.color }
            Rectangle { x: 8.6; y: 8; width: 1.8; height: 6; radius: 0.9; color: ico.color }
        }
        Shape {   // persona (accesibilidad)
            visible: ico.nombre === "accesibilidad"
            anchors.fill: parent
            ShapePath {
                strokeColor: ico.color; strokeWidth: 1.7; fillColor: "transparent"
                capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                startX: 3; startY: 6.5
                PathLine { x: 9.5; y: 8 }
                PathLine { x: 16; y: 6.5 }
                PathMove { x: 9.5; y: 8 }
                PathLine { x: 9.5; y: 12 }
                PathLine { x: 6.5; y: 17.5 }
                PathMove { x: 9.5; y: 12 }
                PathLine { x: 12.5; y: 17.5 }
            }
            Rectangle { x: 8; y: 1; width: 3; height: 3; radius: 1.5; color: ico.color }
        }
    }
}
