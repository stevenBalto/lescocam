import QtQuick
import Lesco
import "../componentes"
import "../ventana"

// «Capa · Enseñar una seña · 2»: hacer la seña 3 veces frente a la cámara.
// Pasa sola al paso 3 a los 2,5 s (AFTER_TIMEOUT de Figma).
Item {
    Rectangle { anchors.fill: parent; color: Qt.rgba(8 / 255, 20 / 255, 51 / 255, 0.45) }

    Timer {
        running: true
        interval: 2500
        onTriggered: { Nav.cerrar(); Nav.abrir("Capa · Enseñar una seña · 3") }
    }

    TarjetaModal {
        width: 520; height: 524.4
        radius: 20
        desplazamientoY: 28.2   // en Figma la tarjeta está en y = 150 de 768

        Texto { x: 32; y: 28; text: "Enseñar una seña · paso 2 de 3"; color: Tema.textoSecundario; peso: Font.Bold; tam: 13; alto: 1.3 }
        Texto { x: 32; y: 61; width: 456; text: "Haga la seña de «" + Estado.palabraNueva + "» 3 veces"; peso: Font.Bold; tam: 24; alto: 1.2; elide: Text.ElideRight }
        Recorte {
            x: 32; y: 108
            width: 456; height: 292.4
            radio: 14
            Camara { estado: ""; anchors.fill: parent }
        }
        Row {   // Repeticiones
            x: 32; y: 416.4
            spacing: 8
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Rectangle { y: 3; width: 14; height: 14; radius: 7; color: Tema.textoOk }
                Rectangle { y: 3; width: 14; height: 14; radius: 7; color: Tema.textoOk }
                Rectangle { y: 3; width: 14; height: 14; radius: 7; color: Tema.oscuro ? "#2f4573" : "#adc5e6" }
            }
            Texto { text: "2 de 3 · hágala otra vez igual"; peso: Font.DemiBold; tam: 15; alto: 1.3 }
        }
        Boton {
            x: 32 + 456 - width; y: 452.4
            texto: "Cancelar"
            onClic: Nav.cerrar()
        }
    }
}
