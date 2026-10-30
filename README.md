# LESCOCam

Asistente de reconocimiento visual de **LESCO** (Lengua de Señas Costarricense).
Usa la cámara para leer señas y las traduce a texto y voz, **de forma local y sin internet**.

## Cómo funciona

```
Cámara (OpenCV) → mano (MediaPipe, 21 puntos) → normalización → comparación con signs.json → palabra + voz
```

No usa un modelo entrenado pesado: compara la mano con señas de referencia por similitud,
así que corre sin GPU. Si ninguna seña supera el umbral, no inventa traducción.

## Estructura (monorepo)

| Carpeta | Contenido |
|---|---|
| `core/` | El motor en Python, compartido: cámara, MediaPipe, normalización, comparación |
| `desktop/` | Interfaz de escritorio (usa `core/`) |
| `mobile/` | App móvil en Flutter (reimplementa la lógica en Dart, usa el mismo `signs.json`) |
| `data/reference/signs.json` | Señas de referencia. **Se versiona**: es el contrato de datos entre escritorio y móvil |
| `data/models/` | Modelo `hand_landmarker.task` de MediaPipe. No se versiona, se descarga |
| `data/dictionary/` | Imágenes del diccionario. No se versionan |
| `scripts/` | `recorder.py` para grabar señas nuevas y otras utilidades |
| `tests/` | Pruebas con pytest |
| `.claude/agents/` | Subagentes de Claude Code para el equipo |
| `hiloBackend/` | Bitácora de sesiones del motor, datos, scripts y tests |
| `hiloFrontend/movil/` · `hiloFrontend/desktop/` | Bitácora de sesiones de cada interfaz |

## Curso y equipo

- **Curso:** _(completar)_
- **Equipo:** _(completar)_

## Cómo arrancar

```bash
git clone https://github.com/stevenBalto/lescocam.git
cd lescocam
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # opcional, solo si se usa Gemini
pytest                           # correr pruebas
```

## Privacidad

La imagen de la cámara nunca sale del equipo. Si se usa Gemini, solo recibe el texto ya reconocido.
