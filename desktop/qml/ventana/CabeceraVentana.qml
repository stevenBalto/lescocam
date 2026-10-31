import QtQuick
import QtQuick.Shapes
import QtQuick.Effects
import Lesco
import "../componentes"

// «Cabecera» de las ventanas grandes (1060×65): ícono, logotipo, título,
// «Abrir panel» y Cerrar.
Rectangle {
    id: cabecera
    property string titulo
    signal abrirPanel()
    signal cerrar()

    width: 1060
    height: 65
    color: Tema.fondoTarjeta
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Tema.bordeLinea }

    Image {
        x: 22; y: 15
        width: 34; height: 34
        source: Qt.resolvedUrl("../../assets/imagenes/icono-app.png")
        sourceSize: Qt.size(68, 68)
        smooth: true
    }

    Row {   // logotipo LESC + lente + Cam
        x: 70; y: 20
        height: 24
        spacing: 0.2
        Texto { text: "LESC"; peso: Font.ExtraBold; tam: 18.4; alto: 1; height: 24; verticalAlignment: Text.AlignVCenter }
        Item {
            width: 13.6; height: 24
            Image {
                y: 5.2
                width: 13.6; height: 13.6
                source: Qt.resolvedUrl("../../assets/imagenes/lente-" + Tema.logotipo + ".svg")
                sourceSize: Qt.size(40, 40)
            }
        }
        Texto { text: "Cam"; tam: 18.4; alto: 1; height: 24; verticalAlignment: Text.AlignVCenter }
    }

    Rectangle { x: 179; y: 19; width: 1; height: 26; color: Tema.bordeBoton }
    Texto {
        x: 194; y: 17.5
        text: cabecera.titulo
        peso: Font.ExtraBold
        tam: 22
        alto: 1.3
    }

    // «Botón Abrir panel» (859,12 · 129×40)
    Rectangle {
        id: abrir
        x: 859; y: 12
        width: 129; height: 40
        radius: 20
        color: zonaAbrir.pressed ? "#d9750f" : zonaAbrir.containsMouse ? "#ff9a3d" : Tema.acentoNaranja
        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: "Abrir panel"
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.18)
            shadowVerticalOffset: 4
            shadowBlur: 0.4
        }
        Texto { x: 18; anchors.verticalCenter: parent.verticalCenter; text: "Abrir panel"; color: Tema.textoSobreNaranja; peso: Font.ExtraBold; tam: 14.5; alto: 1.3 }
        Shape {
            x: 106; y: 14.5
            width: 7; height: 11
            ShapePath {
                strokeColor: Tema.textoSobreNaranja
                strokeWidth: 1.9
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                joinStyle: ShapePath.RoundJoin
                startX: 1.4; startY: 1.3
                PathLine { x: 5.6; y: 5.5 }
                PathLine { x: 1.4; y: 9.7 }
            }
        }
        Rectangle {
            anchors.fill: parent; anchors.margins: -3; radius: 23
            color: "transparent"; border.width: 3; border.color: Tema.foco
            visible: abrir.activeFocus
        }
        MouseArea {
            id: zonaAbrir
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: cabecera.abrirPanel()
        }
        Keys.onReturnPressed: cabecera.abrirPanel()
        Keys.onSpacePressed: cabecera.abrirPanel()
    }

    // Cerrar (1002,14 · 36×36)
    Rectangle {
        id: cerrar
        x: 1002; y: 14
        width: 36; height: 36
        radius: 18
        color: zonaCerrar.pressed ? Qt.darker(Tema.fondoChip, 1.12) : zonaCerrar.containsMouse ? Qt.darker(Tema.fondoChip, 1.06) : Tema.fondoChip
        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: "Cerrar"
        Icono { anchors.centerIn: parent; nombre: "cerrar"; lado: 16; color: Tema.textoPrincipal }
        Rectangle {
            anchors.fill: parent; anchors.margins: -3; radius: 21
            color: "transparent"; border.width: 3; border.color: Tema.foco
            visible: cerrar.activeFocus
        }
        MouseArea {
            id: zonaCerrar
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: cabecera.cerrar()
        }
        Keys.onReturnPressed: cabecera.cerrar()
        Keys.onSpacePressed: cabecera.cerrar()
    }
}
