pragma Singleton
import QtQuick

// Navegación del prototipo de Figma (página «PC · Pantallas y prototipo»).
//
// Cada pantalla tiene el código de su frame en Figma ("01", "02a", "13s"…).
// `pantalla` es la pantalla de fondo y `capas` lo que se abre encima
// (ventanas 12–15 y las «Capa · …»), igual que los overlays de Figma.
QtObject {
    id: nav

    property string pantalla: "01"
    property var capas: []
    readonly property string capa: capas.length ? capas[capas.length - 1] : ""

    // Variables del prototipo (colección «Prototipo» en Figma)
    property bool primerUso: true
    property bool camaraPausada: false
    property bool burbujaVisible: true
    property bool destello: true

    property bool modoDev: false     // --dev: muestra el chat de prueba y el «Facilitador»

    signal pantallaCambio(string anterior, string nueva)

    // ── Qué ventana muestra cada pantalla ─────────────────────────────
    function esPanel(c) { return /^(0[0-9][a-z0-9]*|1[6-9][a-z]*|2[01][a-z]*)$/.test(c) && !esReposo(c) && !esChat(c) }
    function esReposo(c) { return /^01[a-z0-9]*$/.test(c) }
    function esChat(c) { return ["04", "04c", "04e", "06"].indexOf(c) >= 0 }
    function esVentana(c) { return /^1[2-5][a-z]*$/.test(c) }
    function esPrimerUso(c) { return /^2[2-6][a-z]*$/.test(c) }
    function esCapa(c) { return c.indexOf("Capa · ") === 0 }

    // ── Acciones (las mismas de Figma) ────────────────────────────────
    // NAVIGATE: cambia la pantalla de fondo. Si viene de una ventana y va a
    // otra ventana, la reemplaza (como un overlay que navega en Figma).
    function ir(codigo) {
        if (esVentana(codigo) && capas.length && esVentana(capa)) {
            var c = capas.slice(); c[c.length - 1] = codigo; capas = c
            return
        }
        var anterior = pantalla
        capas = []
        pantalla = codigo
        pantallaCambio(anterior, codigo)
    }
    // OVERLAY: abre una capa encima
    function abrir(codigo) { capas = capas.concat([codigo]) }
    // CLOSE: cierra la capa de arriba
    function cerrar() { capas = capas.slice(0, -1) }

    // Clic en la burbuja (IF de Figma: primer uso → bienvenida)
    function tocarBurbuja() { ir(primerUso ? "22" : "02a") }

    // ── Tiempos automáticos (AFTER_TIMEOUT) ───────────────────────────
    readonly property var tiempos: ({
        "00a": ["00b", 50], "00b": ["00c", 50], "00c": ["00d", 400], "00d": ["02a", 100],
        "01e": ["01r", 6000], "01h": ["01h2", 4000],
        "02a": ["02h", 1200], "02h": ["02", 1200],
        "03b": ["03g", 2200], "03d": ["03b", 2000], "03y": ["03g", 2200],
        "04": ["01d", 6000], "04c": ["01r", 6000], "06": ["01d", 6000],
        "07a": ["07h", 1200], "07h": ["07", 1200],
        "09g": ["09", 4000], "09k": ["09", 8000],
        "09r1": ["09r2", 250], "09r2": ["09", 900],
        "09s": ["09s2", 1000], "09s2": ["09s3", 1000], "09s3": ["09", 1000],
        "16": ["02a", 2000], "21b": ["03g", 2500],
        "24": ["24ok", 2500], "25": ["25b", 2500]
    })
    // Las «Capa · Aviso …» se cierran solas
    readonly property int duracionAviso: 1800

    // ── Esc en el panel (KEY_DOWN 27) ─────────────────────────────────
    readonly property var salidas: ({
        "02": "01b", "02b": "01b", "03": "01b", "03b": "01b", "03c": "01b", "03d": "01b", "03y": "01b", "19": "01b",
        "03g": "01d", "03h": "01d", "03i": "01d", "17": "01d", "18": "01d", "21": "01d", "21b": "01d",
        "07": "01e", "07b": "01e", "08": "01e", "09": "01e", "09v": "01e",
        "20": "01r", "09m": "09"
    })

    // Botón ✕ de la cabecera del panel
    function cerrarPanel() {
        if (salidas[pantalla] && pantalla !== "09m") { ir(salidas[pantalla]); return }
        if (/^0[789]/.test(pantalla)) ir("01e")
        else if (pantalla === "16") ir("01r")
        else ir("01b")
    }

    // Selector de modo de la cabecera
    function elegirModo(modo) {
        if (modo === "hablar") ir(/^(02a|02h|00)/.test(pantalla) ? "07" : "07a")
        else ir(/^(07a|07h)$/.test(pantalla) ? "02" : "02a")
    }

    function pulsarEscape() {
        if (capas.length) { cerrar(); return }
        if (salidas[pantalla]) ir(salidas[pantalla])
    }

    property var reloj: Timer {
        id: temporizador
        onTriggered: {
            var t = nav.tiempos[nav.pantalla]
            if (t) nav.ir(t[0])
        }
    }

    onPantallaChanged: {
        temporizador.stop()
        var t = tiempos[pantalla]
        if (t) { temporizador.interval = t[1]; temporizador.start() }
        if (pantalla === "01r") primerUso = false   // «Empezar» del primer uso lleva a 01r
    }
}
