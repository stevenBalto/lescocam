# Sesión 2026-10-29 — Esqueleto del repo

**Área:** Backend (core / data / scripts / tests)
**Quién:** stevenBalto

## Objetivo de la sesión
- Inicializar el monorepo LESCOCam desde cero.

## Lo que se hizo
- Clonado el repo (estaba vacío) y creada la estructura: `core/`, `desktop/`, `mobile/`, `data/` (models, reference, dictionary), `scripts/`, `tests/`.
- `README.md`, `requirements.txt` (opencv-python, mediapipe, pyttsx3, numpy), `.gitignore`, `.env.example`.
- `data/reference/signs.json` inicializado como `{}` (sí se versiona).
- 8 subagentes en `.claude/agents/`: revisor-codigo, depurador, escritor-pruebas, motor-vision, datos-senas, flutter-movil, ui-escritorio, commits.
- Carpetas de hilos: `hiloBackend/` y `hiloFrontend/` (movil y desktop), y `CLAUDE.md` con las reglas del proyecto.
- Reglas de commits: en español, sin coautores, sin mencionar a Claude, sin claves ni archivos ignorados.
- Hook `.githooks/pre-commit` que bloquea claves, `.env`, archivos ignorados y archivos de más de 5 MB.
- Skills: `/retomar`, `/cerrar-sesion`, `/preparar-push`.
- Entorno Python en `.venv` (Python 3.12) con versiones fijas: mediapipe 1.2.0, opencv-contrib-python 5.0.0.93, numpy 2.5.4, pyttsx3 2.99; dev: pytest 9.2.0, pip-audit 2.10.1. `pip-audit`: sin vulnerabilidades.
- Quitado `opencv-python` (choca con `opencv-contrib-python`, que trae mediapipe).
- pnpm 12.16.1 instalado con Corepack (sin npm), sin avisos de seguridad. Regla: npm prohibido.

## Lo que faltó por hacer
- [ ] Subir a GitHub (con `/preparar-push`).
- [ ] Instalar Flutter para la app móvil.
- [ ] Cada compañero: activar el hook con `git config core.hooksPath .githooks`.
- [ ] Completar "Curso" y "Equipo" en el README.
- [ ] Definir el formato de `signs.json` (contrato de datos).
- [ ] Escribir la lógica del motor en `core/` (cámara, MediaPipe, normalización, comparación).
- [ ] Escribir `scripts/recorder.py`.

## Decisiones y notas
- Aún no hay lógica del motor ni interfaces: solo esqueleto.

## Siguiente paso
- Definir el formato de `signs.json` y la normalización (subagentes `motor-vision` y `datos-senas`).
