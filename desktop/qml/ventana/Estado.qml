pragma Singleton
import QtQuick

// Variables del prototipo de Figma que comparten las ventanas 12–15 y sus
// capas (colección «Prototipo»: diccionario-*, practica-pc-*…).
QtObject {
    // Diccionario: seña elegida en la lista
    property string senaActual: "Hola"
    property string categoriaActual: "Saludos"
    // Práctica
    property string palabra: "Gracias"
    property string etiqueta: "Seña 3 de 5 · Saludos"
    property string siguiente: "Siguiente seña"
    property bool enLeccion: true
    // «Enseñar una seña»
    property string palabraNueva: "Matrícula"
    // Voz elegida en Ajustes (para «Escuchar · voz Ana»)
    property string voz: "Ana"

    // Datos de ejemplo del diccionario: [nombre, categoría, propia, cómo se hace, nota]
    readonly property var categorias: ["Saludos", "Familia", "Lugares", "Frecuentes", "Mis señas"]
    readonly property var senas: [
        { nombre: "Hola", categoria: "Saludos" },
        { nombre: "Gracias", categoria: "Saludos" },
        { nombre: "Buenos días", categoria: "Saludos" },
        { nombre: "Adiós", categoria: "Saludos" },
        { nombre: "Buenas noches", categoria: "Saludos" },
        { nombre: "Baño", categoria: "Lugares" },
        { nombre: "Escuela", categoria: "Lugares" },
        { nombre: "Doctor", categoria: "Lugares" },
        { nombre: "Ayuda", categoria: "Frecuentes" },
        { nombre: "Mamá", categoria: "Familia" },
        { nombre: "Papá", categoria: "Familia" },
        { nombre: "Hermano", categoria: "Familia" },
        { nombre: "Sí", categoria: "Frecuentes" },
        { nombre: "No", categoria: "Frecuentes" },
        { nombre: "Agua", categoria: "Frecuentes" },
        { nombre: "Matrícula", categoria: "Mis señas", propia: true,
          como: "Es una seña que usted le enseñó a LESCOCam.", nota: "Enseñada por usted" },
        { nombre: "Christian", categoria: "Mis señas", propia: true,
          como: "Se deletrea letra por letra: C-H-R-I-S-T-I-A-N.", nota: "Nombre propio · deletreo" }
    ]
    function datosDe(nombre) {
        for (var i = 0; i < senas.length; i++)
            if (senas[i].nombre === nombre) return senas[i]
        return senas[0]
    }
}
