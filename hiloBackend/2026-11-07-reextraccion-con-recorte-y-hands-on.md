# Sesión 2026-11-07 — Re-extracción con recorte y videos de Hands-On

**Área:** Backend (core / data / scripts / tests)
**Quién:** Steven Baltodano

## Objetivo de la sesión
- Con los videos de Johan ya agregados, hacer una sola vez lo pendiente del problema 3: bajar Hands-On, re-extraer todo con el recorte de la muñeca, regenerar las bases y medir (dos manos, cara, entre personas).

## Lo que se hizo
- **Descarga de Hands-On:** `descargar_handson.py --alto 540` (opción nueva: con internet lento baja ~4 veces menos y alcanza para los landmarks). 2161 de 2281 videos; 120 dan 401 en Vimeo aun reintentando → `hiloEquipo/medidas/handson-videos-no-descargados.md`.
- **Extracción con recorte:**
  - `extraer_cenarec.py --recorte` → `cenarec/extraccion/recorte/` (1072 videos).
  - `scripts/extraer_handson.py` (nuevo, con recorte por defecto) → `handson/extraccion/recorte/` (2161).
  - Muestra de 300 bimanuales de Hands-On sin recorte → `handson/extraccion/base/`.
- **Bases:**
  - `construir_palabras.py`: `--extraccion` (por defecto `recorte`), `--handson` (suma Hands-On juntando por `clave_palabra`).
  - `data/reference/senas.db` regenerada: 85 palabras, recorte, solo CENAREC.
  - Base completa afuera de git: `data/dictionary/senas_todas_fuentes.db` (2306 palabras).
- **Mediciones:**
  - `medir_dos_manos.py`: `--fuente cenarec|handson|todas` y `--brazos-arriba` (solo cuadros con los dos brazos levantados según la pose: mide el detector y no la seña), con tests en `tests/test_medir_dos_manos.py`.
  - `scripts/evaluar_fuentes.py` (nuevo): plantillas de una persona y prueba con la otra.
- **Resultados** (detalle en `hiloEquipo/problema-3-steven-baltodano.md`, archivos en `hiloEquipo/medidas/problema3-*.json`):
  - CENAREC: ambas manos 90,2 %; con los dos brazos arriba 93,7 % (sin recorte 85,9 %).
  - Hands-On: con los dos brazos arriba 83,9 %; sin recorte 80,5 % → con recorte 83,6 % en la muestra. La 2.ª repetición es de perfil (78,4 %).
  - Banco (120 tomas): senas.db con recorte top-1 31,7 %, errónea 0 %. Con Hands-On top-1 29,2 % y errónea 3,3 % → no se usa.
  - Cara (peso 0/1/2) entre personas: igual. Top-1 entre personas ~21 % (CENAREC→Hands-On) y ~26 % (al revés).
  - Bajar el umbral de reposo para la actividad (0,7/0,6/0,5) no mejora; queda 0,85.

## Lo que faltó por hacer
- [ ] Banco de prueba de Steven (30 palabras): se abrió el grabador y se cortó sin tomas.
- [ ] Pedir a Hands-On los 120 videos que no se pueden bajar.
- [ ] Coordinar con Christian el uso de la extracción con recorte para entrenar.
- [ ] Medir la cara con el banco de las 4 personas cuando esté completo.

## Decisiones y notas
- Hands-On **no** entra a `senas.db` (sube las aceptaciones erróneas). Sirve para medir y como datos de otra persona para el problema 1. Si se quiere usar, probar antes sacando la 2.ª repetición (de perfil) y las palabras que hacen con una mano.
- El reconocimiento entre personas es bajo (~21–26 % top-1): es el tema del problema 1 (Christian).
- `medir_dos_manos.py` en bruto subestima en Hands-On porque `manos = 2` viene de CENAREC; para el detector usar `--brazos-arriba`.

## Siguiente paso
- Grabar el banco de Steven («Vengo de parte de Christian»).
