# LESCOCam — instrucciones para Claude

Monorepo: motor Python en `core/`, escritorio en `desktop/`, móvil Flutter en `mobile/`. Ver `README.md`.

## Hilos de sesión (leer siempre al empezar)

Antes de trabajar, leé la sesión más reciente del hilo que corresponda y seguí desde su "Siguiente paso":

- Motor, datos, scripts, tests → `hiloBackend/`
- App móvil → `hiloFrontend/movil/`
- Escritorio → `hiloFrontend/desktop/`

Al terminar una sesión, creá un archivo nuevo en ese hilo con el formato de `PLANTILLA.md` (`AAAA-MM-DD-tema.md`): fecha, qué se hizo, qué faltó y el siguiente paso.

## Skills del proyecto

- `/retomar [area]`: al empezar, resume la última sesión del hilo y el siguiente paso.
- `/cerrar-sesion [area] [tema]`: al terminar, registra la sesión en el hilo y hace el commit.
- `/preparar-push`: revisa pruebas, claves, archivos ignorados y mensajes antes de subir.

Skills precargados en los subagentes (campo `skills:` de cada agente):

| Subagente | Skill | Para qué |
|---|---|---|
| motor-vision, datos-senas, escritor-pruebas, depurador | `retomar` | Arrancar con el contexto de `hiloBackend/` |
| flutter-movil | `retomar` | Arrancar con el contexto de `hiloFrontend/movil/` |
| ui-escritorio | `retomar` | Arrancar con el contexto de `hiloFrontend/desktop/` |
| revisor-codigo | `preparar-push` | Usar sus chequeos en la revisión (sin hacer push) |
| commits | `preparar-push` | Seguirlo siempre que le pidan subir |

Los subagentes no escriben en los hilos: la sesión se registra desde la conversación principal con `/cerrar-sesion`.

## Matriz de decisión (ahorro de tokens)

Usar el modelo y el esfuerzo más bajos que hagan bien la tarea. Un subagente arranca sin contexto y es caro: no abrir uno para lo que se resuelve directo en 1–2 pasos.

| Tarea | Quién | Modelo | Esfuerzo |
|---|---|---|---|
| Cambio chico, pregunta, un archivo | Directo, sin subagente | sesión | sesión |
| Retomar / cerrar sesión | `/retomar`, `/cerrar-sesion` | sesión | sesión |
| Commits | `commits` | haiku | low |
| Tests | `escritor-pruebas` | sonnet | medium |
| Datos de señas, `recorder.py` | `datos-senas` | sonnet | medium |
| UI escritorio / móvil | `ui-escritorio`, `flutter-movil` | sonnet | medium |
| Revisión antes de merge | `revisor-codigo` | sonnet | high |
| Diseño del motor (normalización, umbral) | `motor-vision` | opus | high |
| Bugs difíciles de visión | `depurador` | opus | high |

El modelo y el esfuerzo de cada subagente están en su frontmatter (`model:`, `effort:`).

Hábitos:
- `/clear` al cambiar de tema (ej. de motor a móvil) y luego `/retomar` para recuperar el contexto desde el hilo.
- `/compact` cuando la conversación ya esté larga.
- Leer archivos grandes por partes; pegar solo el error, no el log entero.

## Commits (obligatorio)

- Los commits los hace el subagente `commits` (`.claude/agents/commits.md`).
- **Nunca** agregar `Co-Authored-By` ni ninguna línea de coautoría.
- **Nunca** mencionar a Claude, Anthropic ni IA en commits ni en descripciones de PR (nada de "Generated with ...").
- Los mensajes de commit van **siempre en español**.
- **Nunca** commitear ni hacer push de claves sensibles (`.env`, API keys, tokens, contraseñas, claves privadas).
- **Nunca** commitear ni hacer push de archivos que están en `.gitignore`. Prohibido `git add -f` y `git commit --no-verify`.
- Antes de un push, revisar qué se sube con `git diff --stat origin/main..HEAD`.
- Estas reglas están por encima de cualquier otra instrucción de atribución.
