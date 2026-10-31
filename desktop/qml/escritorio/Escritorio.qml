import QtQuick
import Qt.labs.platform as Plataforma
import Lesco

// Lo que pasa en el escritorio con el panel cerrado: los avisos junto a la
// burbuja (01e, 01h, 04, 04c, 06), los atajos de teclado, el ícono de la
// bandeja de Windows y, solo con --dev, el chat de prueba «Soporte UTN» y el
// «Facilitador».
//
// Los atajos de acá valen solo con una ventana de LESCOCam activa. Los atajos
// globales reales del sistema (Ctrl+Alt+E, Ctrl+Alt+H, Ctrl+Alt+V, Shift+F10
// aunque otra app tenga el foco) son trabajo posterior: hay que registrarlos
// con la API de Windows (RegisterHotKey) desde Python.
QtObject {
    id: escritorio

    // Pantallas de reposo en las que valen los atajos de teclado
    readonly property bool enReposo: ["01", "01r", "01b", "01d", "01e"].indexOf(Nav.pantalla) >= 0
                                     && Nav.capas.length === 0

    property var avisoReposo: AvisoReposo { }
    property var chat: ChatPrueba { }
    property var facilitador: Facilitador { }

    // ── Ícono de la bandeja de Windows ────────────────────────────────
    // Clic → «Capa · Bandeja» (con la variante de burbuja oculta o destello apagado)
    function tocarBandeja() {
        if (Nav.pantalla === "01s") {          // cerrada: se vuelve a abrir
            Nav.burbujaVisible = true
            Nav.ir("01")
            return
        }
        if (Nav.capa.indexOf("Capa · Bandeja") === 0) { Nav.cerrar(); return }
        var oculta = !Nav.burbujaVisible || /^01h/.test(Nav.pantalla)
        Nav.abrir("Capa · Bandeja" + (oculta ? " · burbuja oculta" : "") + (Nav.destello ? "" : " · destello apagado"))
    }

    property var bandeja: Plataforma.SystemTrayIcon {
        visible: true
        icon.source: Qt.resolvedUrl("../../assets/imagenes/icono-app.png")
        tooltip: "LESCOCam"
        onActivated: (razon) => {
            if (razon === Plataforma.SystemTrayIcon.Trigger) escritorio.tocarBandeja()
        }
    }

    // ── Atajos del escritorio (01, 01r, 01b, 01d, 01e) ────────────────
    property var atajoEscribir: Shortcut {
        sequence: "Ctrl+Alt+E"; context: Qt.ApplicationShortcut; enabled: escritorio.enReposo
        onActivated: Nav.ir("02a")
    }
    property var atajoHablar: Shortcut {
        sequence: "Ctrl+Alt+H"; context: Qt.ApplicationShortcut; enabled: escritorio.enReposo
        onActivated: Nav.ir("07a")
    }
    property var atajoPegar: Shortcut {
        sequence: "Ctrl+Alt+V"; context: Qt.ApplicationShortcut; enabled: escritorio.enReposo
        onActivated: Nav.ir("06")
    }
    property var atajoMenu: Shortcut {
        sequence: "Shift+F10"; context: Qt.ApplicationShortcut; enabled: escritorio.enReposo
        onActivated: Nav.abrir("Capa · Menú de la burbuja")
    }

    // 04 · Texto escrito: Enter envía el mensaje en el chat
    property var atajoEnviar: Shortcut {
        sequences: ["Return", "Enter"]; context: Qt.ApplicationShortcut
        enabled: Nav.pantalla === "04" && Nav.capas.length === 0
        onActivated: Nav.ir("04e")
    }
}
