import QtQuick
import Lesco
import "../componentes"
import "../ventana"

// «Capa · Detalle de seña»: tarjeta de 460×458 centrada sobre un fondo oscuro.
Item {
    Rectangle { anchors.fill: parent; color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.45) }

    TarjetaModal {
        id: tarjeta
        width: 460; height: 458
        radius: 16

        Rectangle {   // Animación
            x: 24; y: 24
            width: 412; height: 220; radius: 12
            color: Tema.fondoCamara
            Recorte {
                anchors.fill: parent
                radio: 12
                MiniCamara { anchors.fill: parent }
            }
        }
        Texto { x: 24; y: 258; text: Estado.senaActual; peso: Font.ExtraBold; tam: 30; alto: 1.2 }
        Texto {
            x: 24; y: 311
            width: 412
            text: Estado.datosDe(Estado.senaActual).categoria + " · se hace con la mano abierta, de lado a lado"
            color: Tema.textoSecundario
            tam: 14
            alto: 1.3
        }
        Rectangle {   // «Video LESCO»
            x: 24; y: 345
            width: 88; height: 31; radius: 16
            color: Tema.fondoCamara
            Icono { x: 8; anchors.verticalCenter: parent.verticalCenter; nombre: "reproducir"; lado: 14; color: "#ffffff" }
            Texto { x: 28; anchors.verticalCenter: parent.verticalCenter; text: "LESCO"; color: "#ffffff"; peso: Font.Bold; tam: 15; alto: 1.2 }
        }
        Row {
            x: 24; y: 390
            spacing: 8
            Boton {
                texto: "Cerrar"
                onClic: Nav.cerrar()
            }
            Boton {
                texto: "Practicar esta seña"
                estilo: "primario"
                onClic: {
                    Estado.palabra = "Gracias"
                    Estado.etiqueta = "Seña 3 de 5 · Saludos"
                    Estado.siguiente = "Siguiente seña"
                    Estado.enLeccion = true
                    Nav.ir("14a")
                }
            }
        }
    }
}
