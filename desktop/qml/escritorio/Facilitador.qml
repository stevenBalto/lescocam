import QtQuick
import QtQuick.Window
import Lesco
import "../componentes"

// Solo con --dev. «Facilitador» de Figma: la pastilla gris de abajo a la
// izquierda («Solo para la prueba · Simular: …») con la que quien conduce la
// prueba hace aparecer cada estado. Aparece solo en las pantallas que la tienen.
Window {
    id: ventana

    // pantalla → [texto de la acción, pantalla a la que lleva]
    readonly property var acciones: ({
        "02": ["Simular: manos fuera ▸", "17"],
        "17": ["Simular: poca luz ▸", "18"],
        "18": ["Simular: cámara ocupada ▸", "19"],
        "19": ["Simular: sin permiso ▸", "20"],
        "20": ["Simular: seña desconocida ▸", "21"],
        "21": ["Fin de los estados · volver al inicio ▸", "01r"],
        "09": ["Simular: equipo en silencio ▸", "09v"],
        // No está en Figma: reemplaza al botón «Inicio» de la barra de tareas de Windows (01s → 01)
        "01s": ["Simular: abrir desde Inicio ▸", "01"]
    })
    readonly property var datos: acciones[Nav.pantalla]
    readonly property int margen: 12

    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint
    color: "transparent"
    title: "Facilitador"
    visible: Nav.modoDev && datos !== undefined
    width: pastilla.width + margen * 2
    height: pastilla.height + margen * 2
    x: Screen.virtualX + 16 - margen
    y: Screen.virtualY + Screen.desktopAvailableHeight - 92 - pastilla.height - margen

    Rectangle {
        id: pastilla
        x: ventana.margen; y: ventana.margen
        width: fila.implicitWidth + 28
        height: 38
        radius: Tema.radioPastilla
        color: Qt.rgba(0, 0, 0, 0.45)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.7)

        Row {
            id: fila
            anchors.centerIn: parent
            spacing: 8
            Texto { anchors.verticalCenter: parent.verticalCenter; text: "Solo para la prueba"; tam: 14; color: "#d5deec" }
            Texto { anchors.verticalCenter: parent.verticalCenter; text: ventana.datos ? ventana.datos[0] : ""; tam: 15; peso: Font.Bold; color: "#ffffff" }
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                if (Nav.pantalla === "01s") Nav.burbujaVisible = true
                Nav.ir(ventana.datos[1])
            }
        }
    }
}
