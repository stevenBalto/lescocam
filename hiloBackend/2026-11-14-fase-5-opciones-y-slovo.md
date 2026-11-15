# Sesión 2026-11-13/14 — Fase 5: opciones cuando duda y modelo con Slovo

**Área:** Backend (core / scripts / tests) + escritorio
**Quién:** Christian Paniagua Castro

## Objetivo de la sesión
- Reescribir el criterio de la fase 5 con el techo medido del banco, mostrar opciones cuando el motor duda y conseguir un modelo para el producto sin ASL Citizen.

## Lo que se hizo
- Criterio de la fase 5 reescrito y **aprobado por Christian**: top-3 ≥ 95 %, aceptación errónea ≤ 2 %, top-1 lo más alto posible, con un método que pueda ir en el producto.
- `ComparadorPalabras.decidir()`: si no acepta y la mejor tiene confianza ≥ `UMBRAL_OPCIONES` (0.4) devuelve 3 opciones. Escritorio: palabra «dudosa» con ola, alternativas, «Ninguna», «Deletrear»; Terminar y Reproducir piden corregirlas antes. `senas.db` con las constantes nuevas en `meta`.
- Licencias revisadas: Slovo sí (basada en CC BY-SA, uso comercial permitido, crédito + pesos con licencia compatible); WLASL y AUTSL no (no comercial); LSFB sin verificar.
- Slovo bajado (`slovo_full360.zip`, 13 GB, por pedazos en paralelo) y extraído con `scripts/extraer_slovo.py`: 20 400 videos, 194 personas, 0 errores, 97 % con seña.
- Bug en `scripts/entrenar_embedding.py`: la época se elegía con la partición `val`; Slovo no la tiene, así que se guardaba la época 1 (modelo 39 %). Arreglado con `--particion-val` (Slovo: `test`) y, sin evaluación A, se guarda la última época. 2 tests nuevos (suite 466).

## Resultados en el banco (680 tomas, plantillas CENAREC)

| Método | top-1 | top-3 | errónea (por persona) |
|---|---|---|---|
| DTW (motor de hoy) | 70.4 % | 88.2 % | 1.2 % |
| Modelo Slovo solo | 74.3 % | 90.6 % | 1.6 % |
| Slovo + DTW, peso 0.3 | 79.0 % | 92.2 % | 1.2 % |
| **Slovo + DTW, peso 0.5** | **78.5 %** | **92.5 %** | **1.0 %** |
| Slovo + DTW, peso 0.7 | 77.4 % | 92.2 % | 1.2 % |
| Slovo 40 épocas + DTW 0.5 | 74.9 % | 90.3 % | 1.3 % |

## Lo que faltó por hacer
- [ ] Llegar a top-3 ≥ 95 % (hoy 92.5 %).
- [ ] Avisar al equipo de la app móvil: 3 opciones cuando duda y constantes nuevas en `senas.db`.
- [ ] Pendientes anteriores: BUENO/TRABAJAR, `DURACION_MAX` 6, señas encadenadas.

## Siguiente paso
- Subir el top-3 de 92.5 a 95 %: ensamble de varias semillas del modelo Slovo, sumar las tomas del equipo al entrenamiento (afinar), plantillas del equipo en la galería, reajustar umbral y margen con el modelo elegido.
- Datos en `data/dictionary/slovo/` (ignorado por git); modelo `modelo/embedding_slovo.pt`.

## Madrugada 2026-11-15: ensamble + galería del equipo

| Configuración (85 palabras, plantillas CENAREC) | top-1 | top-3 | errónea por persona | dice bien |
|---|---|---|---|---|
| 1 modelo Slovo + DTW, peso 0.5 | 78.5 % | 92.5 % | 1.0 % | 45.1 % |
| 5 modelos (semillas 7, 1–4) + DTW, peso 0.7 | 79.7 % | 93.1 % | — | — |
| 5 modelos + galería del equipo (máx.) + DTW, peso 0.5 | 84.7 % | 93.7 % | 1.2 % | 54.7 % |
| **5 modelos + galería del equipo (máx.) + DTW, peso 0.7** | **83.5 %** | **95.1 %** | **1.2 %** | **54.4 %** |

- Galería del equipo = las tomas de las otras 3 personas como plantillas del MODELO (no del DTW); la persona medida nunca está en su galería.
- Errónea con las reglas de `evaluar_banco_modelo` (DTW y modelo coinciden; umbral y margen ajustados dejando a la persona afuera, tope 1 %).
- Experimento en el scratchpad (no en el repo todavía): cache por toma + análisis. Falta pasarlo a un script del repo cuando se mida con todo el vocabulario.
- Siguiente: CENAREC completo (1104 videos) y Hands-On (~2100) descargando; luego extraer, `construir_palabras --todas --handson` y medir el banco con todas las palabras como competencia.
