import QtQuick
import Lesco
import "../ventana"

// «Capa · Aviso del diccionario · escuchar»: aviso que se cierra solo (lo hace ventanas/Capa.qml).
Item {
    AvisoFlotante { texto: "Diciendo «<b>" + Estado.senaActual + "</b>» con la voz " + Estado.voz }
}
