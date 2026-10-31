# LESCOCam · escritorio

Interfaz de escritorio en **PySide6 + QML**. Por ahora reproduce el prototipo de
Figma *Asistente de Reconocimiento Visual LESCO* (página **PC · Pantallas y
prototipo**) con datos de ejemplo; el motor de `core/` se conecta después.

## Cómo correrla

```bash
.venv\Scripts\python -m desktop                 # normal
.venv\Scripts\python -m desktop --dev           # recarga al guardar + herramientas
.venv\Scripts\python -m desktop --dev --pantalla 13s   # arrancar en una pantalla
.venv\Scripts\python -m desktop --pantalla 02 --captura carpeta/   # PNG de cada ventana y cierra
```

Con `--dev` se abre una ventana de herramientas para saltar a cualquier pantalla,
cambiar a modo oscuro y probar el texto al 125 % y 150 %.

## Cómo está armada

```
desktop/
├── app.py            arranque, fuentes, íconos, --dev, --captura
├── iconos.py         los 24 íconos de Figma («Ícono/…»), con color a pedido
├── assets/           fuente Atkinson Hyperlegible Next, ícono de la app, ilustraciones
└── qml/
    ├── Main.qml      crea las ventanas
    ├── Lesco/        Tema (tokens de Figma) y Nav (navegación del prototipo)
    ├── componentes/  piezas reutilizables: Texto, Icono, Boton, Camara, Ola…
    ├── ventanas/     las ventanas reales: Burbuja, Panel, Ventana, PrimerUso, Capa
    ├── panel/        contenido del panel: Escribir, Hablar, Estados, Inicio
    ├── ventana/      Historial, Diccionario, Practica, Ajustes
    ├── primeruso/    asistente de primer uso
    ├── capas/        lo que se abre encima: bandeja, menús, avisos…
    ├── escritorio/   avisos junto a la burbuja y, en --dev, el chat de prueba
    └── dev/          herramientas de desarrollo
```

### Pantallas y navegación

Cada pantalla se llama con el **código de su frame en Figma** (`01`, `02a`,
`13s`, …). `Nav.pantalla` es la pantalla de fondo y `Nav.capas` lo que está
abierto encima. Las acciones son las mismas de Figma:

| Figma | QML |
|---|---|
| Navigate to | `Nav.ir("02a")` |
| Open overlay | `Nav.abrir("13")` o `Nav.abrir("Capa · Bandeja")` |
| Close overlay | `Nav.cerrar()` |
| After delay | tabla `Nav.tiempos` |
| Tecla Esc | tabla `Nav.salidas` |

Cada ventana elige el archivo según el código (`ventanas/Panel.qml`,
`ventanas/Ventana.qml`…). Un archivo cubre un grupo de pantallas y resuelve sus
variantes leyendo `Nav.pantalla`. Si un archivo no existe se ve el marcador
«Pendiente de pasar desde Figma».

Las capas se buscan por nombre: `"Capa · Aviso del historial · copiado"` →
`capas/AvisoDelHistorialCopiado.qml`. La ventana de la capa cubre la pantalla
y es transparente; el archivo ubica su contenido y puede declarar
`property bool cerrarAlTocarFuera: true`.

### Reglas

- **Colores, tamaños y radios salen de `Tema`**, nunca escritos a mano. Si falta
  un token, se agrega en `Lesco/Tema.qml` con su nombre de Figma.
- **Texto siempre con `Texto`** (`tam` en px de Figma, `peso`, `alto` = interlineado).
- **Íconos con `Icono { nombre: "copiar" }`**; los nombres están en `iconos.py`.
- Las medidas son las de Figma en px lógicos; Qt escala solo en pantallas HiDPI.
- Modo oscuro y texto grande tienen que verse bien en cada pantalla.
- Los textos de la interfaz se copian tal cual de Figma.
