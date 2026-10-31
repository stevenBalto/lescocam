import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// Ventana «12 · Historial» y sus variantes: 12 todo, 12e solo escrito,
// 12h solo hablado, 12k copiado.
MarcoVentana {
    id: vista

    readonly property string codigo: Nav.esVentana(Nav.capa) ? Nav.capa : Nav.pantalla
    readonly property string filtro: codigo === "12e" ? "escrito" : codigo === "12h" ? "hablado" : "todo"

    readonly property var frases: [
        { texto: "Hola, soy Christian.", tipo: "escrito", dia: "Hoy", detalle: "Escrito · Soporte UTN · 3:41 p. m.",
          fecha: "Hoy · 3:41 p. m. · Soporte UTN", voz: "Voz Ana · Normal", duracion: "0:03" },
        { texto: "Necesito ayuda con mi matrícula.", tipo: "hablado", dia: "Hoy", detalle: "Hablado · voz Ana · 3:38 p. m.",
          fecha: "Hoy · 3:38 p. m. · voz Ana", voz: "Voz Ana · Normal", duracion: "0:05" },
        { texto: "¿Me pueden enviar el comprobante al correo?", tipo: "escrito", dia: "Hoy", detalle: "Escrito · Soporte UTN · 3:36 p. m.",
          fecha: "Hoy · 3:36 p. m. · Soporte UTN", voz: "Voz Ana · Normal", duracion: "0:07" },
        { texto: "¿Dónde queda el baño?", tipo: "hablado", dia: "Ayer", detalle: "Hablado · voz Diego · 4:15 p. m.",
          fecha: "Ayer · 4:15 p. m. · voz Diego", voz: "Voz Diego · Normal", duracion: "0:04" },
        { texto: "Gracias, hasta luego.", tipo: "escrito", dia: "Ayer", detalle: "Escrito · Soporte UTN · 11:02 a. m.",
          fecha: "Ayer · 11:02 a. m. · Soporte UTN", voz: "Voz Ana · Normal", duracion: "0:03" }
    ]
    readonly property var alturas: [8, 32, 14, 30, 20, 27, 25, 23, 29, 18, 31, 12, 32, 11, 31, 17, 29, 22, 25, 27, 21, 30, 15, 32, 9, 32, 13, 31, 19, 28, 24, 24, 28, 18, 31, 13]

    // Búsqueda + filtro por tipo
    property string busqueda: ""
    readonly property var visibles: frases.filter(function (f) {
        return (filtro === "todo" || f.tipo === filtro)
            && (busqueda === "" || f.texto.toLowerCase().indexOf(busqueda.toLowerCase()) >= 0)
    })
    // Filas de la lista: etiquetas de día entre las frases
    readonly property var filas: {
        var r = [], ultimo = ""
        for (var i = 0; i < visibles.length; i++) {
            if (visibles[i].dia !== ultimo) { r.push({ etiqueta: visibles[i].dia.toUpperCase() }); ultimo = visibles[i].dia }
            r.push({ frase: visibles[i] })
        }
        return r
    }

    property string elegida: frases[0].texto
    property bool sonando: false
    readonly property var actual: {
        for (var i = 0; i < visibles.length; i++) if (visibles[i].texto === elegida) return visibles[i]
        return visibles.length ? visibles[0] : null
    }
    onFiltroChanged: { if (visibles) { elegida = visibles.length ? visibles[0].texto : ""; sonando = false } }

    function pegar() { Nav.ir("06") }
    function copiar() { Nav.abrir("Capa · Aviso del historial · copiado") }
    function descargarAudio() { Nav.abrir("Capa · Aviso del historial · audio") }

    Timer {   // la reproducción de ejemplo termina sola
        running: vista.sonando
        interval: 3000
        onTriggered: vista.sonando = false
    }

    CabeceraVentana {
        id: cabecera
        titulo: "Historial"
        onAbrirPanel: Nav.ir("02a")
        onCerrar: Nav.cerrar()
    }

    // ── Lista ─────────────────────────────────────────────────────────
    Rectangle {
        id: lista
        y: 65
        width: 400; height: 585
        color: Tema.fondoColumna
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
                Accessible.name: "Buscar en lo dicho o escrito"
                Texto {
                    visible: campo.text === ""
                    text: "Buscar en lo dicho o escrito"
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

        Rectangle {   // filtros Todo / Escrito / Hablado
            x: 16; y: 70
            width: 367; height: 50; radius: 18
            color: Tema.fondoChip
            Row {
                x: 5; y: 5
                spacing: 4
                Repeater {
                    model: [
                        { id: "todo", texto: "Todo", codigo: "12", n: 5 },
                        { id: "escrito", texto: "Escrito", codigo: "12e", n: 3 },
                        { id: "hablado", texto: "Hablado", codigo: "12h", n: 2 }
                    ]
                    Rectangle {
                        id: pestana
                        readonly property bool activa: vista.filtro === modelData.id
                        width: 116.33; height: 40; radius: 13
                        color: activa ? Tema.fondoSeleccion : "transparent"
                        activeFocusOnTab: true
                        Accessible.role: Accessible.RadioButton
                        Accessible.name: modelData.texto
                        Accessible.checked: activa
                        Row {
                            anchors.centerIn: parent
                            spacing: 7
                            GlifoTipo {
                                visible: modelData.id !== "todo"
                                tipo: modelData.id
                                tam: 14
                                anchors.verticalCenter: parent.verticalCenter
                                color: pestana.activa ? Tema.textoSobreSeleccion : Tema.textoPrincipal
                            }
                            Texto {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.texto
                                peso: Font.Bold
                                tam: 14
                                alto: 1.3
                                color: pestana.activa ? Tema.textoSobreSeleccion : Tema.textoPrincipal
                            }
                            Rectangle {
                                anchors.verticalCenter: parent.verticalCenter
                                width: 22; height: 20; radius: 10
                                color: pestana.activa ? Qt.rgba(1, 1, 1, 0.2) : Tema.fondoTarjeta
                                Texto {
                                    anchors.centerIn: parent
                                    text: modelData.n
                                    peso: Font.ExtraBold
                                    tam: 12
                                    alto: 1
                                    color: pestana.activa ? Tema.textoSobreSeleccion : Tema.textoPrincipal
                                }
                            }
                        }
                        Rectangle {
                            anchors.fill: parent; anchors.margins: -3; radius: 16
                            color: "transparent"; border.width: 3; border.color: Tema.foco
                            visible: pestana.activeFocus
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: Nav.ir(modelData.codigo)
                        }
                        Keys.onReturnPressed: Nav.ir(modelData.codigo)
                        Keys.onSpacePressed: Nav.ir(modelData.codigo)
                    }
                }
            }
        }

        Column {
            x: 16; y: 130
            width: 367
            spacing: 10
            Repeater {
                model: vista.filas
                Item {
                    id: celda
                    readonly property var f: modelData.frase
                    readonly property bool elegida: !!f && !!vista.actual && vista.actual.texto === f.texto
                    width: 367
                    height: f ? 60 : etiqueta.implicitHeight
                    activeFocusOnTab: !!f
                    Accessible.role: Accessible.Button
                    Accessible.name: f ? f.texto : ""

                    Texto {   // HOY / AYER
                        id: etiqueta
                        visible: !celda.f
                        text: modelData.etiqueta || ""
                        color: Tema.textoSecundario
                        peso: Font.ExtraBold
                        tam: 13
                        alto: 1.3
                    }

                    Item {   // fila de una frase
                        anchors.fill: parent
                        visible: !!celda.f
                        Rectangle {
                            anchors.fill: parent
                            radius: 14
                            color: celda.elegida ? Tema.fondoTarjeta : zonaFila.containsMouse ? Tema.fondoChip : "transparent"
                            layer.enabled: celda.elegida
                            layer.effect: MultiEffect {
                                shadowEnabled: true
                                shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.14)
                                shadowVerticalOffset: 2
                                shadowBlur: 0.3
                            }
                            Rectangle {
                                visible: celda.elegida
                                width: 3; height: parent.height
                                color: Tema.acentoNaranja
                            }
                        }
                        GlifoTipo {
                            x: 12; anchors.verticalCenter: parent.verticalCenter
                            tipo: celda.f ? celda.f.tipo : "escrito"
                            tam: 15
                        }
                        Column {
                            x: 52; y: 11
                            width: 303
                            spacing: 2
                            Texto { width: parent.width; text: celda.f ? celda.f.texto : ""; peso: Font.Bold; tam: 15; alto: 1.3; elide: Text.ElideRight }
                            Texto { width: parent.width; text: celda.f ? celda.f.detalle : ""; color: Tema.textoSecundario; tam: 12.5; alto: 1.3; elide: Text.ElideRight }
                        }
                        Rectangle {
                            anchors.fill: parent; anchors.margins: -3; radius: 17
                            color: "transparent"; border.width: 3; border.color: Tema.foco
                            visible: celda.activeFocus
                        }
                        MouseArea {
                            id: zonaFila
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: celda.elegir()
                        }
                    }
                    function elegir() { if (f) { vista.elegida = f.texto; vista.sonando = false } }
                    Keys.onReturnPressed: elegir()
                    Keys.onSpacePressed: elegir()
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
            readonly property var f: vista.actual
            readonly property bool escrito: f && f.tipo === "escrito"
            anchors.centerIn: parent
            width: 540
            height: columna.implicitHeight + 32 + 28

            Column {
                id: columna
                x: 34; y: 32
                width: 472
                spacing: 16

                Row {   // Datos
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 10
                    Rectangle {
                        height: 24; radius: 12
                        width: tipoFila.implicitWidth + 20
                        color: Tema.fondoChip
                        Row {
                            id: tipoFila
                            x: 10
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 6
                            GlifoTipo { tipo: carta.f ? carta.f.tipo : "escrito"; tam: 12.5; anchors.verticalCenter: parent.verticalCenter }
                            Texto { text: carta.escrito ? "Escrito" : "Hablado"; peso: Font.ExtraBold; tam: 12.5; alto: 1.3 }
                        }
                    }
                    Texto { anchors.verticalCenter: parent.verticalCenter; text: carta.f ? carta.f.fecha : ""; color: Tema.textoSecundario; tam: 14; alto: 1.3 }
                }

                Texto {
                    width: parent.width
                    text: carta.f ? carta.f.texto : ""
                    peso: Font.ExtraBold
                    tam: 34
                    alto: 1.2
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                }

                Rectangle {   // Reproductor
                    width: parent.width; height: 64; radius: 18
                    color: Tema.fondoPanel
                    Rectangle {
                        x: 10; y: 10
                        width: 44; height: 44; radius: 22
                        color: Tema.fondoSeleccion
                        activeFocusOnTab: true
                        Accessible.role: Accessible.Button
                        Accessible.name: vista.sonando ? "Pausar" : "Escuchar"
                        Icono {
                            anchors.centerIn: parent
                            nombre: vista.sonando ? "pausar" : "reproducir"
                            lado: vista.sonando ? 16 : 16
                            color: Tema.acentoNaranja
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: vista.sonando = !vista.sonando
                        }
                        Keys.onReturnPressed: vista.sonando = !vista.sonando
                        Keys.onSpacePressed: vista.sonando = !vista.sonando
                    }
                    Row {   // onda
                        x: 68; y: 16
                        width: vista.sonando ? 309 : 300
                        height: 32
                        spacing: 4
                        Repeater {
                            model: vista.alturas
                            Rectangle {
                                width: (parent.width - 35 * 4) / 36
                                height: modelData
                                y: (32 - modelData) / 2
                                radius: 2
                                color: vista.sonando && index < 18 ? Tema.fondoSeleccion : Tema.fondoOnda
                            }
                        }
                    }
                    Texto {
                        x: vista.sonando ? 391 : 382
                        anchors.verticalCenter: parent.verticalCenter
                        text: vista.sonando ? "Sonando…" : "0:00 / " + (carta.f ? carta.f.duracion : "0:00")
                        peso: Font.ExtraBold
                        tam: 13
                        alto: 1.3
                    }
                }

                Texto {
                    width: parent.width
                    text: carta.f ? carta.f.voz : ""
                    color: Tema.textoSecundario
                    tam: 13
                    alto: 1.3
                    horizontalAlignment: Text.AlignHCenter
                }

                Column {   // Acciones
                    width: parent.width
                    spacing: 10
                    Boton {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 280
                        alto: 46
                        pastilla: true
                        estilo: "oscuro"
                        texto: carta.escrito ? "Pegar en Soporte UTN" : "Escuchar"
                        icono: carta.escrito ? "" : "reproducir"
                        colorIcono: Tema.acentoNaranja
                        ladoIcono: 16
                        onClic: carta.escrito ? vista.pegar() : vista.sonando = true
                    }
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 8
                        Boton {
                            width: 113; alto: 46; pastilla: true
                            texto: "Copiar"; icono: "copiar"; ladoIcono: 14
                            onClic: vista.copiar()
                        }
                        Boton {
                            visible: carta.escrito
                            width: 132; alto: 46; pastilla: true
                            texto: "Escuchar"; icono: "reproducir"; ladoIcono: 14
                            onClic: vista.sonando = true
                        }
                        Boton {
                            width: 183; alto: 46; pastilla: true
                            texto: "Descargar audio"; icono: "descargar"; ladoIcono: 14
                            onClic: vista.descargarAudio()
                        }
                    }
                }

                Texto {
                    visible: carta.escrito
                    width: parent.width
                    text: "Se pega en el campo «Mensaje», donde estaba escribiendo."
                    color: Tema.textoSecundario
                    tam: 13.5
                    alto: 1.3
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        Texto {   // sin resultados
            visible: vista.actual === null
            anchors.centerIn: parent
            text: "No hay frases que coincidan."
            color: Tema.textoSecundario
            tam: 15
        }
    }
}
