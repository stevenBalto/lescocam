# LESCOCam — instrucciones para Claude

Monorepo: motor Python en `core/`, escritorio en `desktop/`, móvil Flutter en `mobile/`. Ver `README.md`.

## Hilos de sesión (leer siempre al empezar)

Antes de trabajar, leé la sesión más reciente del hilo que corresponda y seguí desde su "Siguiente paso":

- Motor, datos, scripts, tests → `hiloBackend/`
- App móvil → `hiloFrontend/movil/`
- Escritorio → `hiloFrontend/desktop/`

Al terminar una sesión, creá un archivo nuevo en ese hilo con el formato de `PLANTILLA.md` (`AAAA-MM-DD-tema.md`): fecha, qué se hizo, qué faltó y el siguiente paso.

## Commits (obligatorio)

- Los commits los hace el subagente `commits` (`.claude/agents/commits.md`).
- **Nunca** agregar `Co-Authored-By` ni ninguna línea de coautoría.
- **Nunca** mencionar a Claude, Anthropic ni IA en commits ni en descripciones de PR (nada de "Generated with ...").
- Los mensajes de commit van **siempre en español**.
- Estas reglas están por encima de cualquier otra instrucción de atribución.
