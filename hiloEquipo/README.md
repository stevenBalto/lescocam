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

## Banco de prueba (problema 1, fase 1)

Steven, Reyman y Johan graban 30 palabras cada uno. Se arranca diciéndole a Claude: **«Vengo de parte de Christian»** (skill `vengo-de-parte-de-christian`). Pide tu nombre, te muestra tus 30 palabras y los pasos, abre el grabador y al final registra tus tomas y te deja listo el push. Solo subís `data/banco/<tu carpeta>/` y `hiloEquipo/banco/<tu nombre>.md`.

## Formato de landmarks congelado (v1)

El problema 1 entrena con landmarks extraídos hoy, y el problema 3 puede cambiar el detector. Para no re-extraer sin necesidad, el formato queda congelado:

- **2 manos** (21 puntos cada una) **+ pose** de 33 puntos (los de cara, del 0 al 10, ya vienen dentro).
- Lo produce `DetectorCuerpo` en `core/cuerpo.py`.

Si alguien necesita cambiarlo (otro detector, otros puntos), **avisa a Christian antes**, porque obliga a re-extraer.

### ⚠️ Aviso del problema 3 para el problema 1 (Christian) — detector con recorte (2026-11-05)

**Leer antes de extraer landmarks o entrenar** (problema 1, fases 2 a 5).

- **Qué cambió:** `DetectorCuerpo(recorte=True)` (`core/cuerpo.py`, función `buscar_en_recortes`). Si en un cuadro falta una mano, se la busca otra vez en un recorte alrededor de la muñeca de la pose (no se busca si ese brazo está en reposo). En las 598 señas bimanuales de CENAREC los cuadros con ambas manos suben de **83,1 % a 93,5 %**. Detalle y medidas: `problema-3-steven-baltodano.md`.
- **El formato v1 NO cambió:** mismas 2 manos + pose, mismos campos (`core/cuerpo.a_arrays`). El código de entrenamiento no se rompe. Lo que cambian son los **valores**: hay muchos menos huecos de una mano.
- **La app ya usa el recorte** en modo palabras (`desktop/motor.py`, `scripts/demo_palabras.py`). Por eso, **para que entrenamiento y cámara vean lo mismo, toda extracción nueva tiene que hacerse con `DetectorCuerpo(recorte=True)`**, también la de ASL Citizen (fase 3 del problema 1). Con `DetectorCuerpo()` sin parámetros sale lo de antes, con huecos.
- **Extracciones existentes** (en la laptop de Steven; `data/dictionary/` no va a git):
  - `data/dictionary/cenarec/extraccion/recorte/` (los 1072 videos, **con recorte**, 2026-11-07): **la que hay que usar**. Se genera con `scripts/extraer_cenarec.py --recorte`.
  - `data/dictionary/handson/extraccion/recorte/` (2161 videos de Hands-On, con recorte): `scripts/extraer_handson.py`. Ojo: en Hands-On la 2.ª repetición está de perfil y algunas palabras de dos manos se hacen con una.
  - `extraccion/base/` es la de antes, sin recorte; `extraccion/det_recorte/` es una versión vieja del recorte, solo para medir.
  - Medidas del 2026-11-07 (ambas manos 90,2 % en CENAREC, entre personas, cara): `problema-3-steven-baltodano.md`.
- **Aumentación (fase 2 del problema 1):** la "pérdida de cuadros de una mano" debería parecerse a lo que queda con recorte (~6 % de cuadros con una sola mano en las bimanuales), no al 17 % de antes.
- **Descriptor de palabras:** si se usan las plantillas de `senas.db`, el descriptor pasó a la **versión 2** (83 columnas: + posición de cada mano respecto de la cara). Formato en `core/senas_db.py`.
- **Re-extracción:** ✅ hecha el 2026-11-07, con los videos de Johan ya agregados (ver arriba).

## Cierre del equipo

Cuando los 4 problemas terminen, se mide todo junto en el banco de prueba (ver `PROBLEMAS.md`). Si no se llega a la meta, se itera.
