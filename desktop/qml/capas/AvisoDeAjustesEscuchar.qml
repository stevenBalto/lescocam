import QtQuick
import Lesco
import "../ventana"

// «Capa · Aviso de ajustes · escuchar»: aviso que se cierra solo (lo hace ventanas/Capa.qml).
Item {
    AvisoFlotante { texto: "Diciendo «Hola, soy Christian.» con la voz " + Estado.voz }
}
