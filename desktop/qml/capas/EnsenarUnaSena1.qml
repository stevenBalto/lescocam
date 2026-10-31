import QtQuick
import Lesco
import "../componentes"
import "../ventana"

// «Capa · Enseñar una seña · 1»: ¿qué palabra quiere enseñar?
Item {
    Rectangle { anchors.fill: parent; color: Qt.rgba(8 / 255, 20 / 255, 51 / 255, 0.45) }

    function siguiente() {
        if (campo.text.trim() !== "") Estado.palabraNueva = campo.text.trim()
        Nav.cerrar()
        Nav.abrir("Capa · Enseñar una seña · 2")
    }

    TarjetaModal {
        width: 520; height: 303
        radius: 20

        Texto { x: 32; y: 28; text: "Enseñar una seña · paso 1 de 3"; color: Tema.textoSecundario; peso: Font.Bold; tam: 13; alto: 1.3 }
        Texto { x: 32; y: 61; width: 456; text: "¿Qué palabra quiere enseñar?"; peso: Font.Bold; tam: 24; alto: 1.2 }
        Texto {
            x: 32; y: 108; width: 456
            text: "Escríbala como quiere que aparezca. Después hará la seña frente a la cámara."
            color: Tema.textoSecundario
            tam: 15
            alto: 1.2
            wrapMode: Text.WordWrap
        }
        Rectangle {   // Campo Palabra
            x: 32; y: 164
            width: 456; height: 51; radius: 10
            color: Tema.fondoTarjeta
            border.width: 2
            border.color: Tema.foco
            TextInput {
                id: campo
                x: 16; width: parent.width - 32
                anchors.verticalCenter: parent.verticalCenter
                text: Estado.palabraNueva
                font.family: Tema.fuente
                font.pointSize: 18 * 0.75
                font.weight: Font.DemiBold
                color: Tema.textoPrincipal
                selectByMouse: true
                clip: true
                focus: true
                Accessible.name: "Palabra que quiere enseñar"
                Component.onCompleted: { forceActiveFocus(); selectAll() }
                Keys.onReturnPressed: siguiente()
            }
        }
        Row {
            x: 32 + 456 - width; y: 231
            spacing: 8
            Boton { texto: "Cancelar"; onClic: Nav.cerrar() }
            Boton { texto: "Siguiente"; estilo: "primario"; onClic: siguiente() }
        }
    }
}
