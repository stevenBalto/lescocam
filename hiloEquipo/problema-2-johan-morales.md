# Problema 2 — Recursos y vocabulario limitado

**Responsable:** Johan Morales Chacón
**Meta:** brechas de vocabulario medidas y priorizadas, fuentes nuevas pedidas y respaldo por deletreo funcionando.

## Qué hay que resolver

El diccionario del CENAREC tiene unas ~1100 entradas y ya procesamos 1039. No se encontró ningún corpus público de LESCO, así que la falta de vocabulario es el tamaño del léxico documentado, no un error de búsqueda. Hay que cerrar lo que falta, buscar más fuentes y asegurar que ninguna palabra quede sin traducir.

## Cómo lo vamos a resolver

1. **Cubrir lo que falta**: completar las 32 palabras pendientes y pedir el permiso del CENAREC por escrito (hoy es solo verbal, de una reunión por Meet).
2. **Buscar fuentes**: preguntar a la UNA (SISLESCO) y al TEC (traductor LESCO) si comparten videos o datos y bajo qué permiso. No está verificado que tengan videos descargables, hay que preguntar.
3. **Medir la cobertura**: comparar las 1039 palabras contra las ~2000 palabras más frecuentes del español, para saber con datos cuántas faltan y cuáles pedir primero.
4. **Respaldo por deletreo**: si una palabra no está en el léxico, el sistema la deletrea con el alfabeto, que ya tenemos.

## Fases

- [ ] **Fase 1 — Pendientes y permiso**
  Completar las 32 palabras que faltan (carpeta `data/dictionary/cenarec/extra/`; CARRO solo aparece dentro de una oración) y pedir el permiso del CENAREC por escrito.
  **Hecho cuando:** las palabras que se pudieron conseguir están procesadas, y el permiso escrito está pedido (o recibido). Anotar quién lo pidió y cuándo.

- [ ] **Fase 2 — Contactar UNA y TEC**
  Escribir a la UNA (SISLESCO) y al TEC.
  **Hecho cuando:** las respuestas (o la falta de ellas) están anotadas en este archivo, con fecha y a quién se escribió.

- [ ] **Fase 3 — Medir la cobertura**
  Comparar el léxico contra las ~2000 palabras más frecuentes del español.
  **Hecho cuando:** hay una lista de brechas priorizada (guardada en el repo) y el porcentaje de cobertura medido.

- [ ] **Fase 4 — Respaldo por deletreo**
  Definir y probar el comportamiento cuando la palabra no está en el léxico. Se coordina con Steven, que conecta el modo palabras en la app.
  **Hecho cuando:** una palabra fuera del léxico se deletrea con el alfabeto, probado con al menos una palabra real.

## Notas

- Los videos y las imágenes del CENAREC no se versionan ni se redistribuyen.
- Las palabras nuevas se agregan después como plantillas; no bloquea a los demás problemas.
