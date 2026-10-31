import QtQuick
import QtQuick.Window
import Lesco

// Aviso junto a la burbuja en las pantallas de reposo y «después de escribir»:
// 01e (guardado), 01h (oculta), 04 / 04c (escrito), 06 (pegado).
// Ventana real, sin marco y siempre encima, ubicada como en Figma: pegada al
// borde derecho de la pantalla disponible y 296 px bajo el borde superior.
Window {
    id: ventana

    // [ícono, color del ícono, mensaje, botón, destino, distancia al borde derecho]
    readonly property var avisos: ({
        "01e":  ["historial", Tema.textoSecundario, "El texto quedó guardado en el historial", "Ver", "capa:12", 65],
        "01h":  ["ocultar", Tema.textoSecundario, "LESCOCam se ocultó hasta las 4:41 p. m. Ábrala desde la bandeja.", "", "", 20],
        "04":   ["terminar", Tema.estadoOk, "Escrito en Soporte UTN", "Deshacer", "01r", 110],
        "04c":  ["terminar", Tema.estadoOk, "Escrito en Soporte UTN", "Deshacer", "01r", 110],
        "06":   ["pegar", Tema.estadoOk, "Pegado: «Hola, soy Christian.»", "Deshacer", "01r", 62]
    })
    readonly property var datos: avisos[Nav.pantalla]
    readonly property int margen: 48       // espacio para la sombra

    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint
    color: "transparent"
    title: "Aviso de LESCOCam"
    visible: datos !== undefined
    width: aviso.width + margen * 2
    height: aviso.height + margen * 2
    x: Screen.virtualX + Screen.desktopAvailableWidth - (datos ? datos[5] : 0) - aviso.width - margen
    y: Screen.virtualY + 296 - margen

    Aviso {
        id: aviso
        x: ventana.margen
        y: ventana.margen
        icono: ventana.datos ? ventana.datos[0] : ""
        colorIcono: ventana.datos ? ventana.datos[1] : Tema.textoSecundario
        mensaje: ventana.datos ? ventana.datos[2] : ""
        accion: ventana.datos ? ventana.datos[3] : ""
        onAccionPulsada: {
            var destino = ventana.datos[4]
            if (destino.indexOf("capa:") === 0) Nav.abrir(destino.substring(5))
            else Nav.ir(destino)
        }
    }
}
