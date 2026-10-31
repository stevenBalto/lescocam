import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// Ventana «13 · Diccionario» y sus variantes por categoría:
// 13 todas, 13s Saludos, 13f Familia, 13l Lugares, 13q Frecuentes, 13m Mis señas.
// La seña elegida y el video son variables del prototipo (diccionario-*).
MarcoVentana {
    id: vista

    readonly property string codigo: Nav.esVentana(Nav.capa) ? Nav.capa : Nav.pantalla
    readonly property var categorias: [
        { texto: "Todas", codigo: "13", n: 42, primera: "Hola" },
        { texto: "Saludos", codigo: "13s", n: 5, primera: "Hola" },
        { texto: "Familia", codigo: "13f", n: 3, primera: "Mamá" },
        { texto: "Lugares", codigo: "13l", n: 3, primera: "Baño" },
        { texto: "Frecuentes", codigo: "13q", n: 4, primera: "Ayuda" },
        { texto: "Mis señas", codigo: "13m", n: 2, primera: "Matrícula" }
    ]
    readonly property var actualCat: {
        for (var i = 0; i < categorias.length; i++) if (categorias[i].codigo === codigo) return categorias[i]
        return categorias[0]
    }
    // Orden de la lista «Todas» tal como aparece en Figma
    readonly property var ordenTodas: ["Hola", "Gracias", "Buenos días", "Baño", "Ayuda", "Mamá", "Papá", "Sí", "No", "Matrícula", "Christian"]

    property string busqueda: ""
    property bool video: false

    readonly property var lista: {
        var r = []
        if (actualCat.codigo === "13") {
            for (var i = 0; i < ordenTodas.length; i++) r.push(Estado.datosDe(ordenTodas[i]))
        } else {
            for (var j = 0; j < Estado.senas.length; j++)
                if (Estado.senas[j].categoria === actualCat.texto) r.push(Estado.senas[j])
        }
        var q = busqueda.toLowerCase()
        return q === "" ? r : r.filter(function (s) { return s.nombre.toLowerCase().indexOf(q) >= 0 })
    }
    readonly property var actual: {
        for (var i = 0; i < lista.length; i++) if (lista[i].nombre === Estado.senaActual) return lista[i]
        return lista.length ? lista[0] : null
    }

    function elegirCategoria(c) {
        Estado.senaActual = c.primera
        Estado.categoriaActual = c.texto === "Todas" ? "Saludos" : c.texto
        video = false
        Nav.ir(c.codigo)
    }
    function elegirSena(s) {
        Estado.senaActual = s.nombre
        Estado.categoriaActual = s.categoria
        video = false
    }
    function practicar() {
        Estado.palabra = actual && actual.nombre === "Hola" ? "Hola" : "Gracias"
        Estado.etiqueta = "Del Diccionario · Saludos"
        Estado.siguiente = "Volver al Diccionario"
        Estado.enLeccion = false
        video = false
        Nav.ir("14a")
    }

    CabeceraVentana {
        titulo: "Diccionario"
        onAbrirPanel: { vista.video = false; Nav.ir("02a") }
        onCerrar: { vista.video = false; Nav.cerrar() }
    }

    // ── Lista ─────────────────────────────────────────────────────────
    Rectangle {
        y: 65
        width: 400; height: 585
        color: Tema.fondoColumna
        clip: true
        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Tema.bordeLinea }

        Rectangle {   // buscar
            x: 16; y: 16
            width: 367; height: 44; radius: 22
            color: Tema.fondoTarjeta
            border.width: 1.5
            border.color: campo.activeFocus ? Tema.foco : Tema.bordeBoton
            Icono { x: 17.5; anchors.verticalCenter: parent.verticalCenter; nombre: "buscar"; lado: 18; color: Tema.textoPrincipal }
            TextInput {
                id: campo
                x: 45.5; width: 253
                anchors.verticalCenter: parent.verticalCenter
                font.family: Tema.fuente
                font.pointSize: 15 * 0.75
                color: Tema.textoPrincipal
                clip: true
                onTextChanged: vista.busqueda = text
                Accessible.name: "Buscar una seña"
                Texto {
                    visible: campo.text === ""
                    text: "Buscar una seña"
                    color: Tema.textoSecundario
                    tam: 15
                }
            }
            Rectangle {
                x: 308.5; anchors.verticalCenter: parent.verticalCenter
                width: 49; height: 19; radius: 6
                color: Tema.fondoChip
                Texto { anchors.centerIn: parent; text: "Ctrl+F"; peso: Font.ExtraBold; tam: 11.5; alto: 1 }
            }
        }

        Flow {   // categorías
            x: 16; y: 70
            width: 367
            spacing: 6
            Repeater {
                model: vista.categorias
                Rectangle {
                    id: chip
                    readonly property bool activa: vista.actualCat.codigo === modelData.codigo
                    height: 36; radius: 18
                    width: fila.implicitWidth + 24
                    color: activa ? Tema.fondoSeleccion : Tema.fondoChip
                    activeFocusOnTab: true
                    Accessible.role: Accessible.RadioButton
                    Accessible.name: modelData.texto
                    Accessible.checked: activa
                    Row {
                        id: fila
                        x: 12
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 6
                        Texto {
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.texto
                            peso: Font.Bold
                            tam: 13.5
                            alto: 1.3
                            color: chip.activa ? Tema.textoSobreSeleccion : Tema.textoPrincipal
                        }
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: contador.implicitWidth + 14; height: 20; radius: 10
                            color: chip.activa ? Qt.rgba(1, 1, 1, 0.2) : Tema.fondoTarjeta
                            Texto {
                                id: contador
                                anchors.centerIn: parent
                                text: modelData.n
                                peso: Font.ExtraBold
                                tam: 12
                                alto: 1
                                color: chip.activa ? Tema.textoSobreSeleccion : Tema.textoPrincipal
                            }
                        }
                    }
                    Rectangle {
                        anchors.fill: parent; anchors.margins: -3; radius: 21
                        color: "transparent"; border.width: 3; border.color: Tema.foco
                        visible: chip.activeFocus
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: vista.elegirCategoria(modelData)
                    }
                    Keys.onReturnPressed: vista.elegirCategoria(modelData)
                    Keys.onSpacePressed: vista.elegirCategoria(modelData)
                }
            }
        }

        Flickable {   // señas
            id: desplazable
            y: 156
            width: 399; height: 362
            contentWidth: width
            contentHeight: columnaSenas.height + 8
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: columnaSenas
                x: 10; y: 4
                width: 379
                spacing: 2
                Repeater {
                    model: vista.lista
                    Item {
                        id: fila
                        readonly property bool elegida: vista.actual && vista.actual.nombre === modelData.nombre
                        width: 379; height: 60
                        activeFocusOnTab: true
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData.nombre
                        Rectangle {
                            anchors.fill: parent
                            radius: 14
                            color: fila.elegida ? Tema.fondoTarjeta : zona.containsMouse ? Tema.fondoChip : "transparent"
                            layer.enabled: fila.elegida
                            layer.effect: MultiEffect {
                                shadowEnabled: true
                                shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.14)
                                shadowVerticalOffset: 2
                                shadowBlur: 0.3
                            }
                            Rectangle { visible: fila.elegida; width: 3; height: parent.height; color: Tema.acentoNaranja }
                        }
                        Rectangle {   // miniatura
                            x: 8; y: 8
                            width: 64; height: 44; radius: 10
                            color: Tema.fondoCamara
                            MiniCamara { anchors.centerIn: parent; width: 60; height: 40 }
                        }
                        Column {
                            x: 84; y: modelData.propia ? 8 : 10
                            spacing: 3
                            Texto { text: modelData.nombre; peso: Font.ExtraBold; tam: 16; alto: 1.2 }
                            Texto { visible: !modelData.propia; text: modelData.categoria; color: Tema.textoSecundario; tam: 12.5; alto: 1.2 }
                            Rectangle {
                                visible: !!modelData.propia
                                height: 20; radius: 10
                                width: propiaFila.implicitWidth + 20
                                color: Tema.fondoNaranjaSuave
                                Row {
                                    id: propiaFila
                                    x: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 5
                                    Rectangle { width: 7; height: 7; radius: 3.5; color: Tema.acentoNaranja; anchors.verticalCenter: parent.verticalCenter }
                                    Texto { text: modelData.nota || ""; peso: Font.ExtraBold; tam: 12; alto: 1.2; color: Tema.textoAcento }
                                }
                            }
                        }
                        Rectangle {
                            anchors.fill: parent; anchors.margins: -3; radius: 17
                            color: "transparent"; border.width: 3; border.color: Tema.foco
                            visible: fila.activeFocus
                        }
                        MouseArea {
                            id: zona
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: vista.elegirSena(modelData)
                        }
                        Keys.onReturnPressed: vista.elegirSena(modelData)
                        Keys.onSpacePressed: vista.elegirSena(modelData)
                    }
                }
            }
        }

        Rectangle {   // pie: enseñar una seña nueva
            y: 518
            width: 399; height: 67
            color: Tema.fondoColumna
            Rectangle { width: parent.width; height: 1; color: Tema.bordeLinea }
            Boton {
                x: 16; y: 11
                width: 367
                alto: 42
                pastilla: true
                Accessible.name: "Enseñar una seña nueva"
                onClic: Nav.abrir("Capa · Enseñar una seña · 1")
                Row {
                    anchors.centerIn: parent
                    spacing: 8
                    Item {   // «+»
                        width: 14; height: 14
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle { anchors.centerIn: parent; width: 10; height: 2.2; radius: 1; color: Tema.textoPrincipal }
                        Rectangle { anchors.centerIn: parent; width: 2.2; height: 10; radius: 1; color: Tema.textoPrincipal }
                    }
                    Texto { anchors.verticalCenter: parent.verticalCenter; text: "Enseñar una seña nueva"; peso: Font.ExtraBold; tam: 14; alto: 1.3 }
                }
            }
        }
    }

    // ── Detalle ───────────────────────────────────────────────────────
    Item {
        x: 400; y: 65
        width: 660; height: 585

        Tarjeta {
            id: carta
            visible: vista.actual !== null
            readonly property var s: vista.actual
            x: 60; y: 22.5
            width: 540; height: 540

            Rectangle {   // video
                x: 20; y: 20
                width: 500; height: 250
                radius: 18
                color: Tema.fondoCamara
                Item {
                    x: 51.2; y: -2.5
                    width: 397.6; height: 255
                    MiniCamara { anchors.fill: parent }
                }
                Rectangle {   // Botón Ver video
                    visible: !vista.video
                    x: 222; y: 97
                    width: 56; height: 56; radius: 28
                    color: Qt.rgba(1, 1, 1, zonaVer.containsMouse ? 0.26 : 0.16)
                    border.width: 1
                    border.color: Qt.rgba(1, 1, 1, 0.30)
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Button
                    Accessible.name: "Ver video"
                    Icono { anchors.centerIn: parent; anchors.horizontalCenterOffset: 2; nombre: "reproducir"; lado: 18; color: "#ffffff" }
                    MouseArea {
                        id: zonaVer
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: vista.video = true
                    }
                    Keys.onReturnPressed: vista.video = true
                    Keys.onSpacePressed: vista.video = true
                }
                Rectangle {   // Avance
                    visible: vista.video
                    y: 246
                    width: 320; height: 4
                    color: Tema.acentoNaranja
                }
                Rectangle {   // Botón Pausar video
                    visible: vista.video
                    x: 362; y: 12
                    width: 126; height: 28; radius: 14
                    color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.7)
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Button
                    Accessible.name: "Pausar video"
                    Icono { x: 9; anchors.verticalCenter: parent.verticalCenter; nombre: "pausar"; lado: 14; color: "#ffffff" }
                    Texto { x: 28; anchors.verticalCenter: parent.verticalCenter; text: "Reproduciendo"; color: "#ffffff"; peso: Font.Bold; tam: 12.5; alto: 1.2 }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: vista.video = false
                    }
                    Keys.onReturnPressed: vista.video = false
                    Keys.onSpacePressed: vista.video = false
                }
            }

            Row {   // Datos
                y: 284
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8
                Rectangle {
                    height: 24; radius: 12
                    width: catTexto.implicitWidth + 20
                    color: Tema.fondoChip
                    Texto { id: catTexto; anchors.centerIn: parent; text: carta.s ? carta.s.categoria : ""; peso: Font.ExtraBold; tam: 12.5; alto: 1.2 }
                }
                Rectangle {
                    visible: !!(carta.s && carta.s.propia)
                    height: 24; radius: 12
                    width: propiaTexto.implicitWidth + 36
                    color: Tema.fondoNaranjaSuave
                    Rectangle { x: 9; y: 8.5; width: 7; height: 7; radius: 3.5; color: Tema.acentoNaranja }
                    Texto { id: propiaTexto; x: 21; anchors.verticalCenter: parent.verticalCenter; text: carta.s && carta.s.nota ? carta.s.nota : ""; peso: Font.ExtraBold; tam: 12.5; alto: 1.2; color: Tema.textoAcento }
                }
            }

            Texto {
                y: 322
                width: parent.width
                text: carta.s ? carta.s.nombre : ""
                peso: Font.ExtraBold
                tam: 40
                alto: 1.1
                horizontalAlignment: Text.AlignHCenter
            }
            Texto {
                x: 20; y: 380
                width: 500
                text: carta.s ? (carta.s.como || "Mire el video y repítala frente a la cámara.") : ""
                color: Tema.textoSecundario
                tam: 14
                alto: 1.3
                horizontalAlignment: Text.AlignHCenter
            }

            Column {   // Acciones
                x: 90; y: 412
                width: 360
                spacing: 10
                Boton {
                    width: 360
                    alto: 46
                    pastilla: true
                    estilo: "oscuro"
                    texto: "Practicar «" + (carta.s ? carta.s.nombre : "") + "»"
                    icono: "practica"; colorIcono: Tema.textoSobreSeleccion
                    ladoIcono: 22
                    onClic: vista.practicar()
                }
                Row {
                    spacing: 10
                    Boton {
                        width: 175; alto: 46; pastilla: true
                        texto: "Copiar"; icono: "copiar"; ladoIcono: 15
                        onClic: Nav.abrir("Capa · Aviso del diccionario · copiado")
                    }
                    Boton {
                        width: 175; alto: 46; pastilla: true
                        texto: "Escuchar"; icono: "reproducir"; ladoIcono: 16
                        onClic: Nav.abrir("Capa · Aviso del diccionario · escuchar")
                    }
                }
            }
        }

        Texto {
            visible: vista.actual === null
            anchors.centerIn: parent
            text: "No hay señas que coincidan."
            color: Tema.textoSecundario
            tam: 15
        }
    }
}
