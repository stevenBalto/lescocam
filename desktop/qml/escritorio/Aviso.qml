import QtQuick
import QtQuick.Effects
import Lesco
import "../componentes"

// Componente «Aviso» de Figma: tarjeta blanca con ícono, mensaje y, si
// corresponde, un botón de texto («Deshacer», «Ver»).
Item {
    id: aviso

    property string icono
    property color colorIcono: Tema.textoSecundario
    property string mensaje
    property string accion            // texto del botón; vacío = sin botón
    signal accionPulsada()

    implicitWidth: fila.implicitWidth + 14 + (accion !== "" ? 8 : 14)
    implicitHeight: accion !== "" ? 60 : 36
    width: implicitWidth
    height: implicitHeight

    Rectangle {
        id: tarjeta
        anchors.fill: parent
        radius: Tema.radioVentana
        color: Tema.fondoTarjeta
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(13 / 255, 46 / 255, 110 / 255, 0.3)
            shadowVerticalOffset: 12
            shadowBlur: 0.8
            shadowScale: 0.96
        }
    }

    Row {
        id: fila
        x: 14
        height: parent.height
        spacing: 12

        Icono {
            anchors.verticalCenter: parent.verticalCenter
            nombre: aviso.icono
            color: aviso.colorIcono
            lado: 20
        }
        Texto {
            anchors.verticalCenter: parent.verticalCenter
            text: aviso.mensaje
            tam: Tema.tamPequeno
            color: Tema.textoPrincipal
        }
        Boton {
            anchors.verticalCenter: parent.verticalCenter
            visible: aviso.accion !== ""
            estilo: "texto"
            texto: aviso.accion
            onClic: aviso.accionPulsada()
        }
    }
}
