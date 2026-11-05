import QtQuick
import QtQuick.Effects
import QtQuick.Window
import Lesco

// Componente «Cámara» (368×236): escena con la persona y los 21 puntos de cada
// mano, y la pastilla de estado arriba a la izquierda. Siempre dice su estado
// con texto, no solo con color.
Item {
    id: camara
    property string estado: "Cámara · solo en este equipo"
    property color colorPunto: Tema.estadoEnVivo
    property bool mostrarEscena: true
    // false en los videos de referencia: muestran la ilustración, no la cámara del usuario
    property bool vivo: true
    // La cámara solo se abre mientras este componente se ve y no está en pausa
    // La cámara solo se suelta en pausa MANUAL. En la pausa automática (sin manos /
    // sin luz) sigue prendida para poder detectar cuándo vuelve y reanudar sola.
    readonly property bool pideCamara: vivo && visible && !(Nav.camaraPausada && Nav.pausaManual)
        && Window.window !== null && Window.window.visible
    readonly property bool hayVideo: vivo && !!motor && motor.hayVideo
    property bool _pedida: false
    property int _frame: 0
    default property alias encima: capaEncima.data

    implicitWidth: 368
    implicitHeight: 236

    onPideCamaraChanged: {
        if (pideCamara && !_pedida) { _pedida = true; motor.pedirCamara() }
        else if (!pideCamara && _pedida) { _pedida = false; motor.soltarCamara() }
    }
    Component.onCompleted: if (pideCamara) { _pedida = true; motor.pedirCamara() }
    Component.onDestruction: if (_pedida && motor) motor.soltarCamara()
    Connections {
        target: motor
        function onFrameNuevo(n) { if (camara.hayVideo) camara._frame = n }
    }

    Rectangle {
        id: marco
        anchors.fill: parent
        radius: 16
        color: Tema.fondoCamara
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Qt.rgba(16 / 255, 24 / 255, 40 / 255, 0.3)
            shadowVerticalOffset: 12
            shadowBlur: 0.8
        }
    }

    Item {
        anchors.fill: parent
        layer.enabled: true
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: mascara
        }
        Image {
            anchors.fill: parent
            visible: camara.hayVideo
            source: camara.hayVideo ? "image://camara/frame?" + camara._frame : ""
            fillMode: Image.PreserveAspectCrop
            cache: false
        }
        Image {
            anchors.fill: parent
            visible: camara.mostrarEscena && !camara.hayVideo
            source: Qt.resolvedUrl("../../assets/imagenes/camara-escena.svg")
            sourceSize: Qt.size(width * 2, height * 2)
        }
        Item { id: capaEncima; anchors.fill: parent }
    }
    Item {
        id: mascara
        anchors.fill: parent
        layer.enabled: true
        visible: false
        Rectangle { anchors.fill: parent; radius: 16 }
    }

    Rectangle {
        x: 10; y: 10
        height: filaEstado.implicitHeight + 10
        width: filaEstado.implicitWidth + 19
        radius: height / 2
        color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.75)
        visible: camara.estado !== ""
        Row {
            id: filaEstado
            x: 9
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Rectangle { width: 8; height: 8; radius: 4; color: camara.colorPunto; anchors.verticalCenter: parent.verticalCenter }
            Texto { text: camara.estado; color: "#ffffff"; tam: Tema.tamNota }
        }
    }

    // Aviso del nivel de luz (solo cámara en vivo). «regular»: se está mejorando la
    // imagen; «baja»: ni con la mejora se detecta, hay que pedir más luz. Siempre con texto.
    Rectangle {
        id: pastillaLuz
        visible: camara.vivo && camara.hayVideo && !!motor && motor.nivelLuz !== "buena"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        height: filaLuz.implicitHeight + 10
        width: filaLuz.implicitWidth + 19
        radius: height / 2
        color: Qt.rgba(11 / 255, 22 / 255, 48 / 255, 0.82)
        Row {
            id: filaLuz
            x: 9
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Rectangle {
                width: 8; height: 8; radius: 4
                anchors.verticalCenter: parent.verticalCenter
                color: (!!motor && motor.nivelLuz === "baja") ? Tema.estadoEnVivo : Tema.estadoAviso
            }
            Texto {
                text: (!!motor && motor.nivelLuz === "baja") ? "Necesito más luz" : "Poca luz · mejorando"
                color: "#ffffff"; tam: Tema.tamNota
            }
        }
    }
}
