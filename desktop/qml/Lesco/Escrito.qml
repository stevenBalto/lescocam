pragma Singleton
import QtQuick

// El texto que la persona va armando en el modo Escribir, con teclado o con
// señas. Mientras `real` es false, el panel muestra las pantallas de ejemplo
// del prototipo; al escribir la primera letra pasa a mostrar este texto.
QtObject {
    property bool real: false
    property var palabras: []          // [[texto, estilo], ...]  estilo: "" o "dudosa"
    property string borrador: ""       // palabra que se está escribiendo con el teclado

    readonly property string texto: {
        var p = palabras.map(function (x) { return x[0] })
        if (borrador !== "") p.push(borrador)
        return p.join(" ")
    }

    function iniciar() { real = true }

    // Cierra la palabra en curso. Con `estilo` "dudosa" se marca para corregir.
    function agregar(palabra, estilo) {
        palabra = (palabra || "").trim()
        if (palabra === "") return
        real = true
        palabras = palabras.concat([[palabra, estilo || ""]])
    }

    function confirmarBorrador() {
        agregar(borrador, "")
        borrador = ""
    }

    // Quita lo último que se escribió: primero la palabra en curso, luego la última palabra.
    function borrarUltima() {
        if (borrador !== "") { borrador = ""; return }
        if (palabras.length) palabras = palabras.slice(0, palabras.length - 1)
    }

    function limpiar() { palabras = []; borrador = "" }
}
