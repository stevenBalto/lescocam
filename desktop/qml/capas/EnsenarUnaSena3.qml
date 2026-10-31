import QtQuick
import Lesco
import "../componentes"
import "../ventana"

// «Capa · Enseñar una seña · 3»: la seña quedó guardada en Mis señas.
Item {
    Rectangle { anchors.fill: parent; color: Qt.rgba(8 / 255, 20 / 255, 51 / 255, 0.45) }

    TarjetaModal {
        width: 520; height: 236
        radius: 20

        Texto { x: 32; y: 28; text: "Enseñar una seña · paso 3 de 3"; color: Tema.textoSecundario; peso: Font.Bold; tam: 13; alto: 1.3 }
        Texto { x: 32; y: 61; width: 456; text: "«" + Estado.palabraNueva + "» ya está en Mis señas"; peso: Font.Bold; tam: 24; alto: 1.2; elide: Text.ElideRight }
        Texto {
            x: 32; y: 108; width: 456
            text: "La reconocerá en el panel como cualquier otra seña. Puede cambiarla o borrarla en Diccionario › Mis señas."
            color: Tema.textoSecundario
            tam: 15
            alto: 1.2
            wrapMode: Text.WordWrap
        }
        Row {
            x: 32 + 456 - width; y: 164
            spacing: 8
            Boton {
                texto: "Ver en Mis señas"
                onClic: { Estado.senaActual = "Matrícula"; Estado.categoriaActual = "Mis señas"; Nav.ir("13m") }
            }
            Boton { texto: "Listo"; estilo: "primario"; onClic: Nav.cerrar() }
        }
    }
}
