# Hilo — Equipo (precisión de LESCO)

Plan de trabajo del equipo para llegar a **más de 95 % de precisión** en el reconocimiento de LESCO. Son 4 problemas, uno por persona, resueltos **en paralelo**. Cada problema tiene fases; cada fase se tacha cuando se cumple su criterio.

Índice de problemas y responsables: [`PROBLEMAS.md`](PROBLEMAS.md).

## Cómo se arranca

Decile a Claude: **«Hola chat, póngamonos al hilo del proyecto para avanzar»**. Se activa la skill `hilo-equipo`, que:

1. Pide tu nombre (antes de cualquier otra cosa).
2. Hace `git pull`.
3. Te muestra tu problema, cómo se resuelve y en qué fase vas.

## Reglas (obligatorias)

- **Cada persona edita solo su archivo** `problema-N-*.md`. Así no hay conflictos entre ustedes.
- **Una fase se cierra solo con evidencia**: el número medido o el resultado que pide su "Hecho cuando". Sin eso no se tacha.
- **Al cerrar cada fase**: se tacha, se hace commit, `git pull` y `git push`. No se empieza la fase siguiente hasta que el push haya salido bien.
- Las fases van en orden. No se salta ninguna.
- Los commits siguen las reglas de `CLAUDE.md` (los hace el subagente `commits`, en español, sin claves ni archivos ignorados).

## Cómo se tacha una fase

Antes:

```
- [ ] **Fase 2 — Nombre de la fase**
```

Después:

```
- [x] ~~**Fase 2 — Nombre de la fase**~~ ✅ 2026-11-05 — evidencia: top-1 = 91 % en el banco de prueba
```

## Formato de landmarks congelado (v1)

El problema 1 entrena con landmarks extraídos hoy, y el problema 3 puede cambiar el detector. Para no re-extraer sin necesidad, el formato queda congelado:

- **2 manos** (21 puntos cada una) **+ pose** de 33 puntos (los de cara, del 0 al 10, ya vienen dentro).
- Lo produce `DetectorCuerpo` en `core/cuerpo.py`.

Si alguien necesita cambiarlo (otro detector, otros puntos), **avisa a Christian antes**, porque obliga a re-extraer.

## Cierre del equipo

Cuando los 4 problemas terminen, se mide todo junto en el banco de prueba (ver `PROBLEMAS.md`). Si no se llega a la meta, se itera.
