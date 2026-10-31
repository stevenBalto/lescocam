import QtQuick
import QtQuick.Effects
import Lesco

// Componente «Botón» de Figma: Estilo × Estado.
//   estilo: "primario" (naranja), "secundario" (borde), "texto",
//           "oscuro" (azul, el «Terminar» del panel)
//   pastilla: esquinas redondas completas (botones del panel)
// Hover y Presionado salen del mouse; el foco de teclado pinta el anillo azul.
FocusScope {
    id: boton

    property string texto
    property string icono
    property string estilo: "secundario"
    property bool pastilla: false
    property bool habilitado: true
    property int alto: 44
    property int relleno: estilo === "texto" ? Tema.espacio8 : Tema.espacio16
    property color colorTexto: estilo === "primario" ? Tema.textoSobreNaranja
                             : estilo === "oscuro" ? Tema.textoSobreSeleccion
                             : estilo === "texto" ? Tema.textoAcento
                             : Tema.textoPrincipal
    property color colorIcono: colorTexto
    property int ladoIcono: 18
    property bool sombra: estilo === "oscuro"
    property url imagen             // dibujo propio en vez de ícono (ej. las flechas de «Terminar»)
    property size ladoImagen: Qt.size(20, 16)

    signal clic()

    implicitWidth: texto ? fila.implicitWidth + relleno * 2 : alto
    implicitHeight: alto
    opacity: habilitado ? 1 : 0.4
    activeFocusOnTab: habilitado

    readonly property bool encima: zona.containsMouse
    readonly property bool presionado: zona.pressed

    Rectangle {
        id: fondo
        anchors.fill: parent
        radius: boton.pastilla ? height / 2 : Tema.radioControl
        color: {
            switch (boton.estilo) {
            case "primario": return boton.presionado ? "#d9750f" : boton.encima ? "#ff9a3d" : Tema.acentoNaranja
            case "oscuro": return boton.presionado ? Qt.darker(Tema.fondoSeleccion, 1.2) : boton.encima ? Qt.lighter(Tema.fondoSeleccion, 1.25) : Tema.fondoSeleccion
            case "texto": return boton.presionado ? "#ffe2c2" : boton.encima ? "#fff1e3" : "transparent"
            default: return boton.presionado ? (Tema.oscuro ? "#1e3159" : "#e3e8f0") : Tema.fondoTarjeta
            }
        }
        border.width: boton.estilo === "secundario" ? (boton.pastilla ? 1.5 : 1) : 0
        border.color: (boton.encima || boton.presionado) ? Tema.textoPrincipal
                     : boton.pastilla ? Tema.bordeBoton : Tema.bordeControl
        layer.enabled: boton.sombra
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.18)
            shadowVerticalOffset: 4
            shadowBlur: 0.5
        }
    }

    Rectangle {   // anillo de foco (3 px azul)
        anchors.fill: parent
        anchors.margins: -3
        radius: fondo.radius + 3
        color: "transparent"
        border.width: 3
        border.color: Tema.foco
        visible: boton.activeFocus
    }

    Row {
        id: fila
        anchors.centerIn: parent
        spacing: boton.estilo === "oscuro" ? 7 : Tema.espacio8

        Image {
            anchors.verticalCenter: parent.verticalCenter
            source: boton.imagen
            visible: boton.imagen.toString() !== ""
            width: boton.ladoImagen.width; height: boton.ladoImagen.height
            sourceSize: Qt.size(width * 2, height * 2)
        }
        Icono {
            anchors.verticalCenter: parent.verticalCenter
            nombre: boton.icono
            color: boton.colorIcono
            lado: boton.ladoIcono
            visible: boton.icono !== ""
        }
        Texto {
            anchors.verticalCenter: parent.verticalCenter
            text: boton.texto
            visible: boton.texto !== ""
            peso: boton.estilo === "oscuro" ? Font.ExtraBold : Font.Bold
            tam: Tema.tamBoton
            alto: 1.3
            color: boton.colorTexto
        }
    }

    MouseArea {
        id: zona
        anchors.fill: parent
        hoverEnabled: true
        enabled: boton.habilitado
        cursorShape: Qt.PointingHandCursor
        onClicked: boton.clic()
    }

    Keys.onReturnPressed: if (habilitado) clic()
    Keys.onSpacePressed: if (habilitado) clic()
}
