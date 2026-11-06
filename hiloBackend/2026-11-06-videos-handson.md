# Sesión 2026-11-06 — videos del diccionario de Hands-On

**Área:** Backend (core / data / scripts / tests)
**Quién:** Johan Morales (problema 2, recursos y vocabulario)

## Objetivo de la sesión
- Sumar una segunda fuente de vocabulario, el diccionario de Hands-On LESCO (diccionario.handsonlesco.com), a la del CENAREC. Solo guardar los videos en el proyecto; extraer las manos y entrenar viene después.

## Lo que se hizo
- `scripts/descargar_handson.py` (nuevo): recorre las letras A–Z en orden, arma la lista de cada una (con su paginación), baja todos sus videos y guarda un catálogo. Va de a un video con pausa de 1 s y retoma donde quedó (salta los ya descargados). Un video que falla no frena a los demás.
- La página no tiene botón de descarga: los videos están en Vimeo, que solo los entrega a un navegador. Se usa `yt-dlp` con la suplantación de Chrome (`curl_cffi`) y la página de Hands-On como origen. Se baja solo la imagen, sin audio.
- `requirements-dev.txt`: se agregan `yt-dlp==2026.10.26` y `curl_cffi==0.17.0`. `pip-audit` no marca vulnerabilidades en ninguna de las dos (solo en `pip`).
- `tests/test_descargar_handson.py` (nuevo): 3 pruebas del armado de nombres y de la lectura de la lista.
- Resultado: **2279 de 2281 videos** descargados (unos 7,8 GB) en `data/dictionary/handson/videos/`, con el catálogo en `data/dictionary/handson/catalogo.json`. Son de 1920×1080 a 24 fps, de unos 7 segundos.

## Lo que faltó por hacer
- [ ] 2 videos que Vimeo no entrega (error 401): «aborto espontáneo» (letra A) y «náusea» (letra N). Pedírselos a Hands-On.
- [ ] Pasar los videos por la extracción de dos manos y cuerpo (`DetectorCuerpo`, formato de landmarks v1) y construir sus plantillas; hay que adaptar `extraer_cenarec.py` y `construir_palabras.py` a esta carpeta.
- [ ] Decidir cómo se tratan las palabras repetidas con el CENAREC: `palabras.etiqueta` es única en `senas.db`.
- [ ] Dejar el permiso de Hands-On por escrito (hoy es verbal) y pedir por escrito el del CENAREC.
- [ ] Problema 2, fase 1: las 32 palabras pendientes del CENAREC (`extra/`); ver si Hands-On cubre algunas.
- [ ] Problema 2, fase 3: medir la cobertura con las dos fuentes contra las ~2000 palabras más frecuentes del español.

## Decisiones y notas
- **Los videos no se suben a GitHub:** `data/dictionary/*` está en `.gitignore` y pesan 7,8 GB. Cada persona los obtiene corriendo `.venv\Scripts\python -m scripts.descargar_handson` (unas 2 horas) o con una copia de la carpeta `data/dictionary/handson/` por USB o Drive. Esto es solo para uso interno: confirmar con Hands-On antes de mostrarlos en la app.
- Instalar antes `pip install -r requirements-dev.txt`.
- Un video con el mismo texto en dos letras se baja una sola vez. Los archivos se llaman `palabra_IDVimeo.mp4`, así que las palabras repetidas (por ejemplo «aprovechar 1» y «aprovechar 2») no chocan.
- No cambió `signs.json` ni `senas.db`.
- Ninguna fase del problema 2 se tacha con este trabajo: aporta vocabulario para las fases 1 y 3, pero no cumple su «Hecho cuando».

## Siguiente paso
- Pedir a Steven la lista de las 32 palabras pendientes del CENAREC, compararla con el catálogo de Hands-On y, con eso, avanzar la fase 3 (cobertura).
