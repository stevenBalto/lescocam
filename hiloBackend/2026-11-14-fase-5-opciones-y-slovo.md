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

## Madrugada 2026-11-15: medición con TODO el vocabulario de CENAREC

Competencia: 1036 palabras + 30 letras de CENAREC (2132 plantillas, `senas_cenarec_todas.db`). Banco: 680 tomas, 4 personas. Sin galería del equipo (solo existe para 85 palabras: con todo el vocabulario sería trampa).

| Configuración | top-1 | top-3 |
|---|---|---|
| DTW solo | 35.6 % | 55.7 % |
| 5 modelos Slovo + DTW, peso 0.7 | 45.4 % | 67.1 % |
| **5 modelos Slovo + DTW, peso 0.9** | **48.2 %** | **70.3 %** |
| 5 modelos solos (peso 1.0) | 45.6 % | 67.1 % |
| + modelo entrenado también con las 1036 palabras LESCO (repeticiones de CENAREC) | 48.2 % | 70.9 % |
| Corrección de "palabras imán" (CSLS, pool genérico de Slovo) | 48.8 % | 69.6 % |

Top-10: 86.8 %. Contar variantes (-2) como la misma palabra no cambia nada (981 textos distintos).

Curva según tamaño del vocabulario (85 del banco + palabras al azar de CENAREC, 3 sorteos, 5 modelos + DTW 0.9):

| Palabras | top-1 | top-3 |
|---|---|---|
| 85 | 79.6 % | 94.1 % |
| 150 | 75.0 % | 90.7 % |
| 200 | 71.3 % | 88.3 % |
| 300 | 66.6 % | 84.7 % |
| 500 | 59.3 % | 80.1 % |
| 750 | 52.5 % | 74.0 % |
| 1036 | 48.2 % | 70.3 % |

Lectura:
- Los errores están repartidos (no hay sinónimos ni pocas palabras culpables). Peores: BUENO, LECHE, CÓMO (0/8).
- Ajustes de puntaje (peso, ensamble, CSLS) y entrenar con las repeticiones LESCO ya no mueven el número. El límite es de datos: cada palabra tiene UN firmante (CENAREC).
- Lo que sí movió el número en 85 palabras fue la galería del equipo (tomas de otras 3 personas): 93.1 → 95.1 % top-3. Es decir, más personas por palabra.
- Siguiente: medir con CENAREC + Hands-On (segundo firmante para muchas palabras) cuando termine la descarga y extracción.

## Madrugada 2026-11-15 (5 a. m.): CENAREC + Hands-On juntos

Hands-On: 1989 de ~2100 videos (el resto: 401 de Vimeo aun con reintento). `senas_todas.db`: 2203 palabras + 30 letras, 6097 plantillas; 820 palabras de CENAREC ganaron un segundo firmante (Hands-On) y 1167 palabras son nuevas. De las 85 del banco, 58 tienen plantillas de Hands-On.

| Configuración (sin galería del equipo) | top-1 | top-3 | top-10 |
|---|---|---|---|
| DTW solo | 26.9 % | 40.4 % | — |
| 5 modelos Slovo + DTW, peso 0.7 | 33.1 % | 50.6 % | — |
| **5 modelos Slovo + DTW, peso 0.9** | **36.5 %** | **56.6 %** | — |
| 5 modelos Slovo + DTW, peso 0.8 | 35.0 % | 52.2 % | 72.2 % |
| Solo etiquetas de CENAREC, pero con las plantillas de Hands-On sumadas, peso 0.9 | 46.3 % | 69.1 % | — |

Curva (85 del banco + palabras al azar del vocabulario conjunto, 3 sorteos, peso 0.9):

| Palabras | top-1 | top-3 |
|---|---|---|
| 85 | 77.8 % | 92.1 % |
| 150 | 71.5 % | 88.3 % |
| 300 | 63.3 % | 83.0 % |
| 500 | 56.2 % | 77.8 % |
| 1000 | 46.2 % | 66.9 % |
| 1500 | 41.3 % | 61.5 % |
| 2203 | 36.3 % | 56.6 % |

Lectura:
- **La meta (top-3 ≥ 95 %) NO se alcanza con todo el vocabulario.** Hoy: 56.6 % con 2203 palabras; 70.3 % con las 1036 de CENAREC.
- El segundo firmante de Hands-On no subió el número (70.3 → 69.1 % en las palabras de CENAREC). Las tomas del equipo se parecen poco a los videos de diccionario en varias palabras (HERMANO, HIJA, LECHE, TÍO, PRIMO, CÓMO, SEÑA: 0/8), aun con dos firmantes.
- Lo único que movió el número fue tener tomas de personas reales firmando como firma el usuario (galería del equipo: +2 puntos en 85 palabras con solo 3 personas).
- Con los métodos y datos de hoy, el tamaño que cumple top-3 ≈ 95 % ronda las **~85–100 palabras**.

Aceptación errónea con 2203 palabras (5 modelos + DTW 0.9, por persona, tope 1 %): **1.0 %** (cumple), pero el motor solo acepta directo el **6.8 %** de las señas; el resto pasa a opciones (y el top-3 acierta 56.6 %).

Decisiones para Christian (opciones):
1. **Grabar más personas por palabra** (equipo, comunidad sorda, voluntarios): es lo que la evidencia dice que funciona. Va contra la idea de "sin depender de firmantes humanos" del problema 1, pero sería grabación una sola vez, no en vivo.
2. **Producto inicial con vocabulario reducido** (las palabras más usadas, ~100–150) con 3 opciones, más deletreo para el resto.
3. **Personalización**: el usuario graba sus propias señas de las palabras que más usa (galería personal).
4. Seguir investigando el modelo (más datos tipo Slovo, otro descriptor): sin garantía; los ajustes probados esta noche (peso, ensamble, CSLS, clases LESCO en el entrenamiento) ya no mueven el número.
