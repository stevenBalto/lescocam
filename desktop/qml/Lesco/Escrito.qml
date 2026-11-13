pragma Singleton
import QtQuick

// El texto que la persona va armando en el modo Escribir, con teclado o con
// señas. Mientras `real` es false, el panel muestra las pantallas de ejemplo
// del prototipo; al escribir la primera letra pasa a mostrar este texto.
QtObject {
    property bool real: false
    property var palabras: []          // [[texto, estilo, destino, opciones], ...]  estilo: "" o "dudosa"
    property int seleccion: -1         // índice de la palabra dudosa tocada (panel de alternativas)
    readonly property bool hayDudosa: palabras.some(function (x) { return x[1] === "dudosa" })
    property string borrador: ""       // palabra que se está escribiendo con el teclado

    readonly property string texto: {
        var p = palabras.map(function (x) { return x[0] })
        if (borrador !== "") p.push(borrador)
        return p.join(" ")
    }

    // Aviso «corrija las palabras con ola»: lo enciende exigirCorregidas() y lo muestra Escribir.
    property bool avisarDudosa: false

    // Antes de terminar, hablar o enviar el texto: devuelve true si se puede seguir. Con palabras
    // dudosas sin corregir devuelve false, selecciona la primera (abre sus alternativas) y activa el aviso.
    function exigirCorregidas() {
        if (!real || !hayDudosa) { avisarDudosa = false; return true }
        seleccionar(palabras.findIndex(function (x) { return x[1] === "dudosa" }))
        avisarDudosa = true
        return false
    }

    function iniciar() { real = true }

    // Cierra la palabra en curso. Con `estilo` "dudosa" se marca para corregir.
    function agregar(palabra, estilo) {
        palabra = (palabra || "").trim()
        if (palabra === "") return
        real = true
        palabras = palabras.concat([[palabra, estilo || ""]])
    }

    // Una seña que no se aceptó con seguridad: la primera opción queda como
    // palabra dudosa y todas las opciones se guardan para corregirla después.
    function agregarDudosa(opciones) {
        var ops = (opciones || []).map(function (o) { return String(o).trim() }).filter(function (o) { return o !== "" })
        if (!ops.length) return
        real = true
        palabras = palabras.concat([[ops[0], "dudosa", "", ops]])
    }

    function seleccionar(i) { seleccion = (i >= 0 && i < palabras.length) ? i : -1 }

    // Cambia una palabra dudosa por la opción elegida (queda como palabra segura)
    function elegir(i, texto) {
        if (i < 0 || i >= palabras.length) return
        var p = palabras.slice()
        p[i] = [texto, ""]
        palabras = p
        seleccion = -1
    }

    function quitar(i) {
        if (i < 0 || i >= palabras.length) return
        palabras = palabras.filter(function (x, k) { return k !== i })
        seleccion = -1
    }

    function confirmarBorrador() {
        agregar(borrador, "")
        borrador = ""
    }

    // Quita lo último que se escribió: primero la palabra en curso, luego la última palabra.
    function borrarUltima() {
        if (borrador !== "") { borrador = ""; return }
        if (palabras.length) palabras = palabras.slice(0, palabras.length - 1)
        if (seleccion >= palabras.length) seleccion = -1
    }

    // Cambia todo el texto de una vez (por ejemplo al corregirlo con el teclado)
    function reemplazar(texto) {
        real = true
        borrador = ""
        seleccion = -1
        palabras = texto.split(/\s+/).filter(function (p) { return p !== "" }).map(function (p) { return [p, ""] })
    }

    function limpiar() { avisarDudosa = false; palabras = []; borrador = ""; seleccion = -1; real = false }
}
