# Los 4 problemas

Meta global: **más de 95 % de precisión** reconociendo LESCO y traduciéndolo al español. Los 4 problemas se resuelven **al mismo tiempo**; el único punto de coordinación es el formato de landmarks (ver [`README.md`](README.md)).

Este archivo no lleva casillas: el avance de cada fase se tacha en el archivo de cada problema, para que nadie pise el trabajo de otro.

| # | Problema | Responsable | Meta | Archivo |
|---|---|---|---|---|
| 1 | Reconocer sin depender de firmantes humanos | Christian Paniagua | ≥ 95 % top-1 con ≤ 2 % de aceptaciones erróneas en el banco de prueba | [`problema-1-christian-paniagua.md`](problema-1-christian-paniagua.md) |
| 2 | Recursos y vocabulario limitado | Johan Morales Chacón | Brechas medidas y priorizadas, fuentes pedidas, respaldo por deletreo funcionando | [`problema-2-johan-morales.md`](problema-2-johan-morales.md) |
| 3 | La cámara detecta solo una mano | Steven Baltodano | Ambas manos en ≥ 90 % de los cuadros de las 598 señas bimanuales | [`problema-3-steven-baltodano.md`](problema-3-steven-baltodano.md) |
| 4 | Luz y contraste distintos | Reyman Barquero | ≥ 90 % de la detección que hay con buena luz, en poca luz y contraluz | [`problema-4-reyman-barquero.md`](problema-4-reyman-barquero.md) |

Las metas de 90 % son propuestas: si el equipo prefiere otra cifra, se cambia en el archivo del problema.

## Cómo sabemos que funciona

Cuando los 4 terminen, se mide todo junto en el **banco de prueba**: personas que no están en las plantillas, imitando los videos del CENAREC, con distinta luz y distancia. Criterio: ≥ 95 % top-1 con ≤ 2 % de aceptaciones erróneas. Si no se llega, se itera sobre el problema que más pese.

## Dependencias entre problemas

- **1 y 3:** comparten el formato de landmarks v1 (congelado). Cambiarlo obliga a re-extraer. **Desde 2026-11-05 el problema 3 usa `DetectorCuerpo(recorte=True)`** (mismo formato, menos huecos de una mano): toda extracción nueva para entrenar tiene que hacerse con recorte. Ver el aviso en [`README.md`](README.md#️-aviso-del-problema-3-para-el-problema-1-christian--detector-con-recorte-2026-11-05).
- **2 y 1:** las palabras nuevas que consiga Johan se agregan después como plantillas; no bloquea a nadie.
- **4:** es independiente. Afecta la cámara en vivo, no el entrenamiento.
- **2 y 3:** el respaldo por deletreo se conecta al modo palabras que Steven deja en la app.
