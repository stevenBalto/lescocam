import QtQuick
import QtQuick.Window
import QtQuick.Effects
import QtQuick.Shapes
import Lesco
import "../componentes"

// Animación de inicio (00a → 00b → 00c → 00d → 02a):
//   00a  la burbuja llega borrosa
//   00b  el visor enfoca
//   00c  el nombre enfoca
//   00d  el visor se vuelve panel
// El velo, la burbuja, el nombre y el visor ocupan toda la pantalla, así que
// van en su propia ventana transparente. El panel (la ventana que carga este
// archivo) aparece recién en 00d.
//
// Los tiempos y las duraciones son los de Figma (AFTER_TIMEOUT + SMART_ANIMATE).
// Esta pantalla lleva su propio reloj: frena el de `Nav.tiempos` porque ese
// no cuenta lo que dura cada transición.
Item {
    id: inicio
    implicitWidth: 400
    implicitHeight: 300

    // 0 = 00a, 1 = 00b, 2 = 00c, 3 = 00d, 4 = desvanecer el visor y pasar a 02a
    property int etapa: 0
    readonly property var duraciones: [0, 550, 500, 600, 300]       // lo que dura llegar a cada etapa
    readonly property var esperas: [50, 600, 900, 700, 300]         // cuánto se queda antes de pasar a la siguiente
    readonly property int dur: Tema.reducirMovimiento ? 0 : duraciones[etapa]
    readonly property int curva: etapa === 3 || etapa === 4 ? Easing.OutQuad : Easing.InOutSine

    readonly property Window panelWin: Window.window
    readonly property real ancho: ventanaCompleta.width
    readonly property real alto: ventanaCompleta.height
    // Centro de la escena (en Figma: 683, 376 sobre 1366×768)
    readonly property real cx: ancho / 2
    readonly property real cy: alto / 2 - 8

    function etapaDe(codigo) { return Math.max(0, "abcd".indexOf(codigo.charAt(2))) }
    function pasar(e) {
        etapa = e
        reloj.interval = esperas[e]
        reloj.restart()
    }
    function saltar() { reloj.stop(); Nav.ir("02a") }

    Timer {
        id: reloj
        onTriggered: {
            if (inicio.etapa < 4) inicio.pasar(inicio.etapa + 1)
            else Nav.ir("02a")
        }
    }
    Connections {
        target: Nav
        function onPantallaCambio(anterior, nueva) {
            if (/^00/.test(nueva)) { Nav.reloj.stop(); inicio.pasar(inicio.etapaDe(nueva)) }
        }
    }
    Component.onCompleted: {
        Nav.reloj.stop()
        pasar(etapaDe(Nav.pantalla))
        panelWin.opacity = Qt.binding(function () { return panelOpacidad })
    }
    Component.onDestruction: if (panelWin) panelWin.opacity = 1

    // ── Valores por etapa (cada cambio se anima con la duración de la etapa) ──
    property real panelOpacidad: [0, 0, 0, 1, 1][etapa]
    Behavior on panelOpacidad { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }

    property real veloOp: [0.72, 0.72, 0.72, 0, 0][etapa]
    Behavior on veloOp { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }

    property real logoOp: [0, 0, 1, 0, 0][etapa]
    Behavior on logoOp { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }
    property real logoBlur: [10, 10, 0, 0, 0][etapa]
    Behavior on logoBlur { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }

    property real burbujaOp: [1, 1, 0, 0, 0][etapa]
    Behavior on burbujaOp { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }
    property real burbujaTam: [166.6, 166.6, 107, 107, 107][etapa]
    Behavior on burbujaTam { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }
    property real burbujaBlur: [12, 0, 0, 0, 0][etapa]
    Behavior on burbujaBlur { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }

    property real destelloTam: [120, 300, 400, 400, 400][etapa]
    Behavior on destelloTam { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }
    property real destelloOp: [0, 0.85, 0, 0, 0][etapa]
    Behavior on destelloOp { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }

    property real pistaOp: [1, 1, 1, 0, 0][etapa]
    Behavior on pistaOp { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }

    // El visor: un rectángulo (izq, arriba, der, abajo) con una esquina en cada punta
    readonly property real panelX: panelWin ? panelWin.x - ventanaCompleta.x : ancho - 400
    readonly property real panelY: panelWin ? panelWin.y - ventanaCompleta.y : 0
    readonly property real panelAlto: panelWin ? panelWin.height : alto
    property real visorIzq: [20, cx - 135, cx - 177, panelX + 8, panelX + 8][etapa]
    property real visorArriba: [20, cy - 135, cy - 78, panelY + 8, panelY + 8][etapa]
    property real visorDer: [ancho - 20, cx + 135, cx + 364, panelX + 392, panelX + 392][etapa]
    property real visorAbajo: [alto - 68, cy + 135, cy + 95, panelY + panelAlto - 8, panelY + panelAlto - 8][etapa]
    property real visorOp: [0, 1, 1, 1, 0][etapa]
    Behavior on visorIzq { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }
    Behavior on visorArriba { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }
    Behavior on visorDer { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }
    Behavior on visorAbajo { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }
    Behavior on visorOp { NumberAnimation { duration: inicio.dur; easing.type: inicio.curva } }

    Shortcut { sequence: "Space"; context: Qt.ApplicationShortcut; onActivated: inicio.saltar() }

    Window {
        id: ventanaCompleta
        visible: true
        x: Screen.virtualX
        y: Screen.virtualY
        width: Screen.width
        height: Screen.height
        flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        color: "transparent"
        title: "LESCOCam · inicio"

        // «Velo»
        Rectangle {
            anchors.fill: parent
            color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, inicio.veloOp)
        }

        // «Destello»: el aro que se abre alrededor del logotipo
        Rectangle {
            width: inicio.destelloTam; height: width; radius: width / 2
            x: inicio.cx - width / 2; y: inicio.cy - height / 2
            color: "transparent"
            border.width: 3
            border.color: "#ffffff"
            opacity: inicio.destelloOp
        }

        // «Logotipo»: LESC + lente + Cam, centrado en el visor de 00c
        Item {
            id: logotipo
            width: 489; height: 125
            x: inicio.cx + 93.5 - width / 2
            y: inicio.cy + 8.5 - height / 2
            opacity: inicio.logoOp
            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true
                blurMax: 64
                blur: inicio.logoBlur / 64
            }
            Texto {
                x: 0; width: 226; height: 125
                text: "LESC"
                peso: Font.ExtraBold
                tam: 96
                alto: 1.3
                color: "#ffffff"
                verticalAlignment: Text.AlignVCenter
                font.letterSpacing: -2
            }
            Image {
                x: 227; y: 27
                width: 71; height: 71
                source: Qt.resolvedUrl("../../assets/imagenes/lente-blanco.svg")
                sourceSize: Qt.size(width * 2, height * 2)
            }
            Texto {
                x: 299; width: 190; height: 125
                text: "Cam"
                tam: 96
                alto: 1.3
                color: "#ffffff"
                verticalAlignment: Text.AlignVCenter
                font.letterSpacing: -2
            }
        }

        // «Burbuja»: el ícono de la app, borroso al llegar
        Item {
            id: burbuja
            width: inicio.burbujaTam * 1.6; height: width
            x: inicio.cx - width / 2
            y: inicio.cy - 5 - height / 2
            opacity: inicio.burbujaOp
            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true
                blurMax: 64
                blur: inicio.burbujaBlur / 64
            }
            Item {
                id: disco
                anchors.centerIn: parent
                width: inicio.burbujaTam; height: width
                Item {
                    id: circulo
                    anchors.fill: parent
                    layer.enabled: true
                    visible: false
                    Rectangle { anchors.fill: parent; radius: width / 2 }
                }
                Item {
                    anchors.fill: parent
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        maskEnabled: true
                        maskSource: circulo
                    }
                    Image {
                        anchors.fill: parent
                        source: Qt.resolvedUrl("../../assets/imagenes/icono-app.png")
                        sourceSize: Qt.size(256, 256)
                        smooth: true
                    }
                }
                Rectangle {   // «Borde»
                    anchors.centerIn: parent
                    width: parent.width * 110 / 107; height: width; radius: width / 2
                    color: "transparent"
                    border.width: 3.3 * parent.width / 107
                    border.color: Qt.rgba(1, 1, 1, 0.7)
                }
            }
        }

        // «Visor»: las cuatro esquinas
        Esquina { x: inicio.visorIzq; y: inicio.visorArriba; izquierda: true; arriba: true }
        Esquina { x: inicio.visorDer - 44; y: inicio.visorArriba; izquierda: false; arriba: true }
        Esquina { x: inicio.visorIzq; y: inicio.visorAbajo - 44; izquierda: true; arriba: false }
        Esquina { x: inicio.visorDer - 44; y: inicio.visorAbajo - 44; izquierda: false; arriba: false }

        // «Pista para saltar»
        Texto {
            anchors.horizontalCenter: parent.horizontalCenter
            y: parent.height - 106
            text: "Toque o presione espacio para saltar"
            tam: 14
            color: Tema.textoSecundario
            opacity: inicio.pistaOp
        }

        // «Saltar»: un toque en cualquier lado
        MouseArea {
            anchors.fill: parent
            onClicked: inicio.saltar()
        }
        Item {
            focus: true
            Keys.onSpacePressed: inicio.saltar()
        }
    }

    // Una esquina del visor (44×44), dibujada para la esquina de arriba a la izquierda y espejada
    component Esquina: Shape {
        property bool izquierda: true
        property bool arriba: true
        width: 44; height: 44
        opacity: inicio.visorOp
        layer.enabled: true
        layer.samples: 4
        transform: Scale {
            origin.x: 22; origin.y: 22
            xScale: izquierda ? 1 : -1
            yScale: arriba ? 1 : -1
        }
        ShapePath {
            strokeColor: Tema.acentoNaranja
            strokeWidth: 4
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            startX: 4; startY: 44
            PathLine { x: 4; y: 14 }
            PathQuad { x: 14; y: 4; controlX: 4; controlY: 4 }
            PathLine { x: 44; y: 4 }
        }
    }
}
