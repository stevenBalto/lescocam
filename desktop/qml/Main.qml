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

    // «Pausar si no hay manos» (Ajustes › Cámara): el motor avisa y se pausa la cámara del
    // panel de forma AUTOMÁTICA (no manual): la cámara sigue prendida y se reanuda sola.
    property var vigiaManos: Connections {
        target: motor
        function onSinManos() {
            if (Nav.esPanel(Nav.pantalla) && !Nav.pausaManual) {
                Nav.pausaManual = false
                Nav.camaraPausada = true
            }
        }
        // Al volver a ver una mano, se reanuda sola (salvo que la pausa sea manual).
        // La señal de cambio de hayMano es manoCambio.
        function onManoCambio() {
            if (motor.hayMano && Nav.camaraPausada && !Nav.pausaManual) Nav.camaraPausada = false
        }
    }

    // El asistente de primer uso se muestra una sola vez (se guarda en el equipo).
    // Al terminarlo (Nav.primerUso pasa a false), se marca como visto.
    property var vigiaPrimerUso: Connections {
        target: Nav
        function onPrimerUsoChanged() { if (!Nav.primerUso && motor) motor.marcarPrimerUsoVisto() }
    }

    // Para las pruebas automáticas (tests/test_desktop_pantallas.py)
    function irA(codigo) { Nav.ir(codigo) }
    function abrirCapa(nombre) { Nav.abrir(nombre) }
    function textoEscrito() { return Escrito.texto }
    function palabrasEscritas() { return Escrito.palabras.length }

    Component.onCompleted: {
        Tema.oscuro = oscuro
        Tema.escala = escala
        Nav.modoDev = modoDev
        // Si ya se vio el primer uso en este equipo, no se vuelve a mostrar solo.
        if (motor && motor.primerUsoVisto) Nav.primerUso = false
        Nav.ir(pantallaInicial || "01")
    }
}
