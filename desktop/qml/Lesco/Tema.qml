pragma Singleton
import QtQuick

// Variables de Figma («Color», «Medidas», «Escala de texto», «Modo»).
// Cambiar `oscuro` o `escala` repinta toda la app.
QtObject {
    id: tema

    property bool oscuro: false
    property int escala: 0          // 0 = 100 %, 1 = 125 %, 2 = 150 %
    property bool reducirMovimiento: false

    readonly property string fuente: "Atkinson Hyperlegible Next"

    function c(claro, osc) { return oscuro ? osc : claro }
    function t(a, b, d) { return [a, b, d][escala] }

    // Color
    readonly property color fondoPanel: c("#eef1f5", "#0b1630")
    readonly property color fondoTarjeta: c("#ffffff", "#14254a")
    readonly property color fondoBarra: c("#f7f9fb", "#0b1630")
    readonly property color fondoCamara: "#0b1630"
    readonly property color fondoSeleccion: c("#0d2d6d", "#adc5e6")
    readonly property color fondoAviso: c("#fff4db", "#3a2e10")
    readonly property color fondoEnCurso: c("#fff8f0", "#2e2410")
    readonly property color fondoChip: c("#e6ebf3", "#1e3159")
    readonly property color fondoColumna: c("#f7f8fb", "#0f1d3b")
    readonly property color fondoNaranjaSuave: c("#fff4e8", "#3a2a14")
    readonly property color fondoOk: c("#e3f4eb", "#123a2a")
    readonly property color fondoOnda: c("#c9d3e3", "#2f4573")
    readonly property color fondoBanda: c("#0d2d6d", "#13264f")
    readonly property color bordeSuave: c("#d5deec", "#2a4170")
    readonly property color bordeControl: c("#8494b0", "#5a74a6")
    readonly property color bordeBoton: c("#c3ccd9", "#3a5285")
    readonly property color bordeLinea: c("#e3e7ed", "#22365f")
    readonly property color textoPrincipal: c("#0d2d6d", "#f2f5fa")
    readonly property color textoSecundario: c("#4b5b7c", "#aab8d0")
    readonly property color textoSobreSeleccion: c("#ffffff", "#0b1630")
    readonly property color textoSobreNaranja: "#0d2d6d"
    readonly property color textoAcento: c("#a04e06", "#ffb566")
    readonly property color textoApagado: c("#9aa6bd", "#7a8bb0")
    readonly property color textoOk: c("#11643f", "#7fe0ae")
    readonly property color acentoNaranja: "#f68b1f"
    readonly property color estadoOk: c("#1e8e5a", "#4cc38a")
    readonly property color estadoOkTexto: c("#137047", "#4cc38a")
    readonly property color estadoAviso: c("#8a5a00", "#ffc857")
    readonly property color estadoEnVivo: c("#c92a2a", "#ff6b6b")
    readonly property color foco: "#2f7de1"
    // Valores de la bandeja en Figma que no tienen variable propia
    readonly property color interruptorApagado: "#b7c1d3"
    readonly property color estadoCamaraLista: "#2fbf71"
    readonly property string logotipo: oscuro ? "blanco" : "azul"

    // Acento por modo (variable «Modo»)
    readonly property color acentoEscribir: "#2f7de1"
    readonly property color acentoHablar: "#9b4dca"

    // Dedos de la mano (ilustraciones)
    readonly property color dedoPulgar: "#f68b1f"
    readonly property color dedoIndice: c("#2f7de1", "#5aa2ff")
    readonly property color dedoMedio: c("#1e9e6a", "#4cc38a")
    readonly property color dedoAnular: c("#9b4dca", "#c49bff")
    readonly property color dedoMenique: c("#d6336c", "#ff7aa8")
    readonly property color dedoPalma: c("#9fb3d9", "#c9d6ee")

    // Escala de texto
    readonly property real tamCuerpo: t(16, 20, 24)
    readonly property real tamPequeno: t(14, 18, 21)
    readonly property real tamNota: t(14, 18, 21)
    readonly property real tamBoton: t(15, 19, 23)
    readonly property real tamPalabra: t(20, 25, 30)
    readonly property real tamPalabraActual: t(28, 35, 42)
    readonly property real tamSubtitulo: t(20, 25, 30)
    readonly property real tamTitulo: t(30, 38, 45)
    readonly property string etiquetaEscala: ["100 %", "125 %", "150 %"][escala]

    // Medidas
    readonly property int espacio4: 4
    readonly property int espacio8: 8
    readonly property int espacio12: 12
    readonly property int espacio16: 16
    readonly property int espacio20: 20
    readonly property int espacio24: 24
    readonly property int espacio28: 28
    readonly property int espacio32: 32
    readonly property int espacio48: 48
    readonly property int radioChico: 6
    readonly property int radioControl: 10
    readonly property int radioTarjeta: 12
    readonly property int radioPanel: 16
    readonly property int radioVentana: 12
    readonly property int radioPastilla: 999

    // Duraciones (Figma usa «smart animate» y «disolver»)
    readonly property int animRapida: reducirMovimiento ? 0 : 150
    readonly property int animNormal: reducirMovimiento ? 0 : 250

    function icono(nombre, color) {
        return "image://icono/" + nombre + "?color=" + encodeURIComponent(String(color))
    }
}
