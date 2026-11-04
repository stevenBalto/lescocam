---
name: hilo-equipo
description: Arranque del equipo de LESCOCam. Se activa con "Hola chat, póngamonos al hilo del proyecto para avanzar" (o frases como "ponernos al hilo del proyecto"). Pide el nombre antes de todo, hace git pull, muestra el problema que le toca a esa persona, cómo se resuelve y en qué fase va, y obliga a hacer commit, pull y push al cerrar cada fase, tachándola.
---

# Hilo del equipo

Plan en `hiloEquipo/` (leer `README.md` y `PROBLEMAS.md` si hay dudas de reglas).

## 1. Pedir el nombre (antes de todo)

**No leas archivos, no corras comandos ni resumas nada hasta tener el nombre.** Preguntá solo: «¿Cómo te llamás?».

Con el nombre, buscá a la persona (sin distinguir mayúsculas ni tildes; alcanza con nombre y un apellido, o el nombre solo si es único):

| Persona | Problema | Archivo |
|---|---|---|
| Christian Paniagua | 1 — Reconocer sin humanos | `hiloEquipo/problema-1-christian-paniagua.md` |
| Johan Morales Chacón | 2 — Recursos y vocabulario | `hiloEquipo/problema-2-johan-morales.md` |
| Steven Baltodano | 3 — Detección de dos manos | `hiloEquipo/problema-3-steven-baltodano.md` |
| Reyman Barquero | 4 — Luz y contraste | `hiloEquipo/problema-4-reyman-barquero.md` |

Si el nombre no coincide con nadie, decilo y volvé a preguntar. No sigas hasta tener uno válido.

## 2. Ponerse al día

Corré `git pull`. Si falla, hay conflictos o hay cambios sin commitear que lo bloquean, **parate**: explicá qué pasa y resolvelo con la persona antes de seguir.

## 3. Mostrar el problema

Leé el archivo de esa persona y mostrá, corto y en este orden:

1. **Tu problema:** número y título.
2. **Meta.**
3. **Qué hay que resolver y cómo** (2–4 líneas).
4. **Fases:** la lista con su estado (las tachadas ya están hechas).
5. **Fase actual:** la primera sin tachar, con su "Hecho cuando".

Terminá preguntando si se arranca por la fase actual. No empieces a trabajar sin confirmación.

## 4. Trabajar

- Solo la fase actual, y en orden. No saltes fases.
- Editá solo el archivo del problema de esa persona.
- El formato de landmarks v1 está congelado. Si hace falta cambiarlo, avisá que hay que decírselo a Christian antes.

## 5. Cerrar una fase (obligatorio)

Una fase se cierra solo cuando se cumple su "Hecho cuando" **con evidencia** (el número medido o el resultado concreto). Sin evidencia no se tacha. Pedí confirmación a la persona.

Al cerrarla, en este orden:

1. **Tachar** la fase en el archivo del problema:
   `- [x] ~~**Fase N — título**~~ ✅ AAAA-MM-DD — evidencia: <qué se midió>`
2. **Commit** con el subagente `commits` (mensaje en español, sin coautores, sin mencionar a Claude, sin claves ni archivos ignorados), con el trabajo de la fase y el archivo tachado.
3. **`git pull`**. Si hay conflictos, resolverlos con la persona antes de seguir.
4. **Chequeos de `/preparar-push`** (claves, archivos ignorados, archivos de más de 5 MB) y **`git push`**.

**No empieces la fase siguiente hasta que el push haya salido bien.** Si el push falla, arreglalo primero. Esto no se puede omitir aunque la persona lo pida.

Después del push, mostrá la nueva fase actual y preguntá si se sigue.

## 6. Cerrar el problema

Al tachar la última fase: avisá que hay que decirle al equipo, y recordá el cierre global descrito en `hiloEquipo/PROBLEMAS.md` (medir todo junto en el banco de prueba).

Al terminar la sesión, `/cerrar-sesion` sigue registrando la bitácora en el hilo de backend o frontend, como siempre.
