---
name: retomar
description: Retoma el trabajo de LESCOCam desde la última sesión registrada en los hilos. Lee la sesión más reciente del área (backend, móvil o escritorio) y resume dónde se quedó, qué falta y cuál es el siguiente paso. Úsalo al empezar una sesión o con "¿dónde quedamos?".
argument-hint: "[backend | movil | desktop]"
---

# Retomar sesión

## 1. Elegir el área

Usá el argumento si viene (`backend`, `movil` o `desktop`). Si no viene, preguntá cuál de las tres se va a trabajar.

| Área | Carpeta del hilo |
|---|---|
| backend | `hiloBackend/` |
| movil | `hiloFrontend/movil/` |
| desktop | `hiloFrontend/desktop/` |

## 2. Encontrar la última sesión

Listá los archivos `AAAA-MM-DD-*.md` de esa carpeta (ignorá `README.md` y `PLANTILLA.md`) y tomá el de fecha más reciente. Si hay varios del mismo día, tomá el último por nombre.

Si la carpeta no tiene sesiones todavía, decilo y ofrecé revisar las otras áreas o arrancar de cero.

## 3. Revisar el estado del repo

- `git log --oneline -5` para ver los commits desde esa sesión.
- `git status --short` para ver si quedaron cambios sin commitear.

## 4. Resumir

Respondé corto, en este orden:

1. **Última sesión:** fecha y tema.
2. **Siguiente paso:** lo que dice esa sección, tal cual.
3. **Pendientes:** los `- [ ]` de "Lo que faltó por hacer".
4. **Notas importantes:** decisiones o cambios de contrato de `signs.json`, si hay.
5. **Estado del repo:** cambios sin commitear o commits nuevos, si hay.

Terminá preguntando si se arranca por el siguiente paso. No empieces a trabajar sin confirmación.
