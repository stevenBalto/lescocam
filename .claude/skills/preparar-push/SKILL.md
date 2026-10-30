---
name: preparar-push
description: Revisa todo antes de subir los cambios de LESCOCam a GitHub — pruebas, qué se va a subir, claves sensibles, archivos ignorados, mensajes de commit y hilos al día — y recién entonces hace git push. Úsalo con "subamos esto", "hacé push", "preparar push".
---

# Preparar push

Corré cada chequeo en orden. Si uno falla, **no hagas push**: reportá qué falló y cómo arreglarlo.

## 1. Estado limpio

- `git status --short`: no debe haber cambios sin commitear. Si hay, preguntá si se commitean (con el subagente `commits`) o se dejan fuera.
- `git fetch origin` y revisá si la rama remota tiene commits nuevos (`git log --oneline HEAD..origin/main`). Si tiene, avisá que hay que integrarlos primero.

## 2. Qué se va a subir

- `git log --oneline origin/main..HEAD` (si la rama remota no existe aún, `git log --oneline`).
- `git diff --stat origin/main..HEAD`.

Mostrá la lista de commits y archivos.

## 3. Claves y archivos prohibidos

Sobre los archivos que se van a subir, verificá que:

- No hay `.env` (sí se permite `.env.example`, sin valores).
- Ningún archivo está en `.gitignore`: para cada uno, `git check-ignore --no-index <archivo>` no debe devolver nada (salvo `.gitkeep`).
- No hay modelos (`data/models/`), imágenes de `data/dictionary/`, `venv/`, `.venv/`, `__pycache__/`, `mobile/build/`, `mobile/.dart_tool/`.
- Ningún archivo pesa más de 5 MB.
- El diff (`git diff origin/main..HEAD`) no contiene claves: `API_KEY=`, `TOKEN=`, `SECRET=`, `PASSWORD=` con valor, `AIza...`, `ghp_...`, `-----BEGIN ... PRIVATE KEY-----`.

## 4. Mensajes de commit

En cada commit que se va a subir (`git log --format=%B origin/main..HEAD`):

- Está en español.
- No tiene `Co-Authored-By`.
- No menciona a Claude, Anthropic ni IA.

Si alguno falla, avisá y no hagas push.

## 5. Pruebas

Si existe `tests/` con archivos de prueba, corré `pytest`. Si falla, no hagas push. Si todavía no hay pruebas, decilo y seguí.

## 6. Hilos al día

Revisá que el hilo del área tocada tenga una sesión de hoy (`date +%F`). Si no la tiene, sugerí correr `/cerrar-sesion` antes de subir.

## 7. Push

Mostrá un resumen corto (commits, archivos, resultado de cada chequeo) y pedí confirmación. Con el sí:

- Si la rama no tiene upstream: `git push -u origin main`.
- Si ya lo tiene: `git push`.

Nunca uses `--force` ni `--no-verify`. Si el push falla por credenciales, explicá que hay que hacerlo desde la terminal propia.
