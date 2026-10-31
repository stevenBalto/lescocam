import QtQuick
import Lesco
import "ventanas"

// Raíz de la app: crea las ventanas. Cada una se muestra sola según la
// pantalla actual del prototipo (ver Lesco/Nav.qml).
QtObject {
    id: raiz

    required property bool modoDev
    required property string pantallaInicial
    required property string assets
    property bool oscuro: false
    property int escala: 0
    property string pantallaActual: Nav.pantalla   // lo lee app.py al recargar

    property var burbuja: Burbuja { }
    property var panel: Panel { }
    property var ventana: Ventana { }
    property var primerUso: PrimerUso { }
    property var capa: Capa { }

    // Lo que pasa «en el escritorio» con el panel cerrado: avisos junto a la
    // burbuja (01*, 04*, 06), la app cerrada (01s) y, con --dev, el chat de
    // prueba «Soporte UTN» y el botón «Solo para la prueba».
    property var escritorio: Loader { source: "escritorio/Escritorio.qml" }
    property var herramientas: Loader { active: raiz.modoDev; source: "dev/Herramientas.qml" }

    // Para las pruebas automáticas (tests/test_desktop_pantallas.py)
    function irA(codigo) { Nav.ir(codigo) }
    function abrirCapa(nombre) { Nav.abrir(nombre) }

    Component.onCompleted: {
        Tema.oscuro = oscuro
        Tema.escala = escala
        Nav.modoDev = modoDev
        Nav.ir(pantallaInicial || "01")
    }
}
