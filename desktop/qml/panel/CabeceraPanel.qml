import QtQuick
import Lesco
import "../componentes"

// «Cabecera» del panel: selector de modo + Historial, Diccionario, Práctica,
// Ajustes y Cerrar.
Item {
    id: cabecera
    property string modo: "escribir"
    height: 62

    SelectorModo {
        x: 16; y: 14
        modo: cabecera.modo
        onElegir: (m) => Nav.elegirModo(m)
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 16
        y: 18
        spacing: 2
        BotonCabecera { icono: "historial"; nombreAccesible: "Historial"; onClic: Nav.abrir("Capa · Historial rápido") }
        BotonCabecera { icono: "diccionario"; nombreAccesible: "Diccionario"; onClic: Nav.abrir("13") }
        BotonCabecera { icono: "practica"; nombreAccesible: "Práctica"; onClic: Nav.abrir("14") }
        BotonCabecera { icono: "ajustes"; nombreAccesible: "Ajustes"; onClic: Nav.abrir("15a") }
        BotonCabecera { icono: "cerrar"; ladoIcono: 16; nombreAccesible: "Cerrar"; onClic: Nav.cerrarPanel() }
    }
}
