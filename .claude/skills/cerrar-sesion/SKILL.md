---
name: cerrar-sesion
description: Cierra una sesión de trabajo de LESCOCam. Registra en el hilo correspondiente (backend, móvil o escritorio) la fecha, lo que se hizo, lo que faltó y el siguiente paso, y luego hace el commit con el subagente commits. Úsalo al terminar de trabajar o con "cerremos la sesión".
argument-hint: "[backend | movil | desktop] [tema]"
---

# Cerrar sesión

## 1. Elegir el área

Usá el argumento si viene. Si no, deducilo de los archivos que cambiaron en la sesión y confirmalo:

| Archivos tocados | Área | Carpeta del hilo |
|---|---|---|
| `core/`, `data/`, `scripts/`, `tests/` | backend | `hiloBackend/` |
| `mobile/` | movil | `hiloFrontend/movil/` |
| `desktop/` | desktop | `hiloFrontend/desktop/` |

Si se tocaron varias áreas, escribí una sesión en cada hilo afectado.

## 2. Juntar la información

- Revisá la conversación, `git status` y `git log` desde la última sesión registrada para saber qué se hizo.
- Leé la última sesión del hilo para arrastrar los pendientes que sigan abiertos.
- Si no está claro qué faltó o cuál es el siguiente paso, preguntá antes de escribir.

## 3. Escribir la sesión

- Fecha de hoy en formato `AAAA-MM-DD` (usá `date +%F`).
- Nombre del archivo: `AAAA-MM-DD-tema.md`, con el tema en minúsculas y con guiones (ej. `2026-11-03-normalizacion.md`). Si ya existe, agregá `-2`.
- Usá exactamente la estructura de `PLANTILLA.md` de esa carpeta:
  - Objetivo de la sesión
  - Lo que se hizo (concreto: archivos, funciones, decisiones)
  - Lo que faltó por hacer (`- [ ]`, incluidos los pendientes que vienen de sesiones anteriores y siguen abiertos)
  - Decisiones y notas (si cambió el formato de `signs.json`, escribí "Cambio de contrato: afecta a la app móvil")
  - Siguiente paso (una acción clara para arrancar la próxima vez)
- Escribilo en español.

## 4. Mostrar y confirmar

Mostrá el contenido de la sesión y pedí confirmación o correcciones.

## 5. Commit

Con la confirmación, usá el subagente `commits` para commitear la sesión junto con los cambios de trabajo que queden pendientes. Se aplican sus reglas: mensaje en español, sin coautores, sin mencionar a Claude, sin claves ni archivos ignorados.

No hagas push. Para subir, se usa `/preparar-push`.
