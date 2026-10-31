import QtQuick
import Lesco
import "../componentes"

// Aro de estado y etiqueta de la burbuja («Burbuja» · Estado=… en Figma).
// Mide lo mismo que el disco (64 × 64): ponerlo encima del disco con
// `anchors.fill: disco`. El aro sobresale 5 px y la etiqueta cuelga 6 px
// debajo, así que la ventana de la burbuja tiene que dejar ese espacio.
//
// Estados: reposo, grabando, pausa, listo, cargando, sincamara, atencion,
// revisando, hablando, reconocio. Todas las pantallas de reposo (01*, 04*, 06)
// usan «reposo» (así están en Figma); los demás estados los usará el motor.
Item {
    id: raiz

    property string estado: "reposo"

    // [texto de la etiqueta, color del aro]
    readonly property var estados: ({
        "grabando":  ["En vivo",    "#2f7de1"],
        "pausa":     ["En pausa",   "#ffc857"],
        "listo":     ["Listo",      "#1e8e5a"],
        "cargando":  ["Cargando",   "#aab8d0"],
        "sincamara": ["Sin cámara", "#c92a2a"],
        "atencion":  ["¿Seña?",     "#ffc857"],
        "revisando": ["Revisar",    "#adc5e6"],
        "hablando":  ["Hablando",   "#9b4dca"],
        "reconocio": ["Reconoció",  "#2f7de1"]
    })
    readonly property var datos: estados[estado]
    readonly property bool enReposo: datos === undefined

    width: 64
    height: 64

    // Reposo: solo el borde blanco translúcido
    Rectangle {
        visible: raiz.enReposo
        x: -1; y: -1
        width: 66; height: 66
        radius: 33
        color: "transparent"
        border.width: 2
        border.color: Qt.rgba(1, 1, 1, 0.7)
    }

    // «Reconoció»: el aro destella
    Rectangle {
        visible: raiz.estado === "reconocio"
        x: -8; y: -8
        width: 80; height: 80
        radius: 40
        color: "transparent"
        border.width: 8
        border.color: Qt.rgba(47 / 255, 125 / 255, 225 / 255, 0.3)
    }

    // Aro de estado
    Rectangle {
        visible: !raiz.enReposo
        x: -5; y: -5
        width: 74; height: 74
        radius: 37
        color: "transparent"
        border.width: raiz.estado === "reconocio" ? 5 : 3.5
        border.color: raiz.datos ? raiz.datos[1] : "transparent"
    }

    // Etiqueta: nunca solo color, siempre texto
    Rectangle {
        id: etiqueta
        visible: !raiz.enReposo
        anchors.horizontalCenter: parent.horizontalCenter
        y: 70
        width: fila.implicitWidth + 16
        height: 21
        radius: Tema.radioPastilla
        color: Tema.fondoCamara

        Row {
            id: fila
            anchors.centerIn: parent
            spacing: 4
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 7; height: 7; radius: 3.5
                color: raiz.datos ? raiz.datos[1] : "transparent"
            }
            Texto {
                anchors.verticalCenter: parent.verticalCenter
                text: raiz.datos ? raiz.datos[0] : ""
                tam: 11.5
                peso: Font.Bold
                alto: 1.3
                color: "#ffffff"
            }
        }
    }
}
