# Sesión 2026-10-30 — prototipo de Figma a código

**Área:** Frontend escritorio (desktop/)
**Quién:** Reyman

## Objetivo de la sesión
- Pasar a código el prototipo de Figma «Asistente de Reconocimiento Visual LESCO» (página «PC · Pantallas y prototipo»), tal cual: pantallas e interacciones, con datos de ejemplo y sin motor real.

## Lo que se hizo
- Entorno: Python 3.12.10 instalado, `.venv` creado con `requirements-dev.txt`, **PySide6==6.12.0** agregado a `requirements.txt` (pip-audit: sin vulnerabilidades).
- Base de la app en `desktop/` (ver `desktop/README.md`):
  - `app.py` + `__main__.py`: `python -m desktop` con `--dev` (recarga al guardar y ventana de herramientas para saltar de pantalla), `--pantalla`, `--captura`, `--oscuro`, `--escala`.
  - `iconos.py`: los 24 íconos de Figma, con color a pedido (`image://icono/...`).
  - `assets/`: fuente Atkinson Hyperlegible Next (OFL), ícono de la app, escena de cámara, lente del logo.
  - `qml/Lesco/Tema.qml`: todas las variables de Figma (colores claro/oscuro, escala 100/125/150 %, medidas).
  - `qml/Lesco/Nav.qml`: navegación del prototipo con los códigos de Figma (`Nav.ir`, `abrir`, `cerrar`), tiempos automáticos, Esc y la condición de primer uso de la burbuja.
  - Ventanas reales: Burbuja, Panel (400 px a la derecha), Ventana (12–15), PrimerUso, Capa (overlays) y, con `--dev`, chat de prueba «Soporte UTN» y botón «Facilitador».
- Las 90 pantallas y 16 capas del prototipo quedaron en código (5 subagentes en paralelo):
  - Panel: Escribir 02*/03*, animación de inicio 00a–00d, Hablar 07*/08/09*, Estados 16–21b.
  - Ventanas: Historial 12*, Diccionario 13*, Práctica 14*, Ajustes 15a–d (oscuro, tamaño de texto y reducir movimiento funcionan de verdad).
  - Primer uso 22–26b, reposo 01*/04*/06, bandeja de Windows (ícono real), menú de la burbuja, historial rápido, avisos.
- `tests/test_desktop_pantallas.py`: recorre las 90 pantallas y 16 capas sin abrir ventanas y falla si hay errores de QML (102 pruebas, pasan).

## Lo que faltó por hacer
- [ ] El texto de las ventanas 12–15 está en px fijos: no crece con 125 % / 150 %.
- [ ] `panel/Inicio.qml` detiene `Nav.reloj` y cambia la opacidad del panel por su cuenta; pasar la secuencia a `Nav.tiempos` con las duraciones reales.
- [ ] Atajos globales de Windows (Ctrl+Alt+E/H/V, Shift+F10): hoy solo funcionan con una ventana de LESCOCam enfocada.
- [ ] Sombras suaves de las tarjetas del panel (Figma las tiene, en código no).
- [ ] Revisión visual lado a lado de las pantallas que los subagentes no compararon (12e, 12h, 13f/l/q, 14a/d/e/f, 15a/b/d, 19, 20, capas Enseñar 1/3 y avisos) y del 150 % en general.
- [ ] Los menús y avisos no siguen a la burbuja si se arrastra.

## Decisiones y notas
- Interfaz de escritorio en **PySide6 + QML** (el documento técnico dejaba PySide/Tkinter/Flutter): mismo proceso que el motor de `core/`, ventana siempre encima, bandeja de Windows y animaciones como las del prototipo.
- Python **3.12** (el documento técnico dice 3.14; MediaPipe suele tardar en soportar versiones nuevas). Conviene corregir el documento.
- El subagente `ui-escritorio` no tiene acceso a las herramientas de Figma (no se pudo agregar desde la sesión); se usaron subagentes generales con modelo sonnet y sus mismas reglas. Si se quiere, agregar a mano las herramientas `mcp__figma__*` en su `tools:`.
- Servidor MCP de Figma configurado a nivel de usuario (`claude mcp add --transport http -s user figma https://mcp.figma.com/mcp`).
- Las pantallas que en Figma no tienen acción (ej. «Terminar» en 03b/03y/03d, «Siguiente» en 14a/14c/14d/14f) quedaron igual, sin acción.
- No cambió `signs.json`.

## Siguiente paso
- Correr `.venv\Scripts\python -m desktop --dev`, recorrer el prototipo con la ventana de herramientas y anotar diferencias con Figma; después hacer que el texto de las ventanas 12–15 siga la escala de `Tema`.
