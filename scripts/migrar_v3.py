"""Pasa signs.json de version 2 a version 3 (corrección de proporción de imagen) sin regrabar.

En la version 2 cada vector se normalizó con x/ancho, y/alto de MediaPipe, sin
corregir la proporción de la imagen. La normalización es lineal (traslación,
escala uniforme y espejo en x), y todo eso conmuta con escalar x e y por
separado. Entonces cada toma se recalcula desde su vector v2:

    v3 = normalizar(v2 con x * ancho, y * alto, z * ancho)

El tamaño de la imagen de cada toma sale de:
  - "frame" de la toma, si lo tiene (webcam);
  - "imagen:<carpeta>/<L>": el tamaño real del archivo data/<carpeta>/<L>.png (o --imagenes);
  - "video:...": el recorte de scripts/importar_video.py (RECORTE_MANO).
Si alguna toma no tiene tamaño conocido no se escribe nada.

Cada toma queda con "frame": [ancho, alto]. Antes de escribir se copia el v2 a
data/reference/signs.v2.json.bak (ignorado por git).

Uso:
    .venv/bin/python -m scripts.migrar_v3            # prueba, no escribe
    .venv/bin/python -m scripts.migrar_v3 --guardar
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from core.clasificador import RUTA_SENAS, escribir_signs, tomas_de
from core.landmarks import NUM_LANDMARKS, VECTOR_SIZE, VERSION_VECTOR, normalizar_puntos

RAIZ = Path(__file__).resolve().parent.parent
DECIMALES = 6
EXTENSIONES = (".png", ".jpg", ".jpeg", ".webp")


def migrar_vector(vector, frame) -> np.ndarray:
    """Vector v2 (63) + (ancho, alto) de su imagen -> vector v3 (63)."""
    v = np.asarray(vector, dtype=np.float64).reshape(-1)
    if v.shape[0] != VECTOR_SIZE or not np.all(np.isfinite(v)):
        raise ValueError("vector inválido")
    ancho, alto = float(frame[0]), float(frame[1])
    if ancho <= 0 or alto <= 0:
        raise ValueError(f"frame inválido {frame}")
    pts = v.reshape(NUM_LANDMARKS, 3).copy()
    pts[:, 0] *= ancho
    pts[:, 1] *= alto
    pts[:, 2] *= ancho
    # Ya está espejada si era izquierda: se renormaliza como derecha.
    return normalizar_puntos(pts, "Right").astype(np.float64)


def tamano_imagen(carpeta: Path, nombre: str) -> Optional[tuple[int, int]]:
    import cv2

    for ruta in carpeta.iterdir() if carpeta.is_dir() else []:
        if ruta.suffix.lower() in EXTENSIONES and ruta.stem.upper() == nombre.upper():
            img = cv2.imread(str(ruta))
            if img is not None:
                return int(img.shape[1]), int(img.shape[0])
    return None


def resolvedor(imagenes: Optional[Path] = None) -> Callable[[dict], Optional[tuple[int, int]]]:
    """Función toma -> (ancho, alto) según su "frame" o su "source"."""
    from scripts.importar_video import RECORTE_MANO

    x0, y0, x1, y1 = RECORTE_MANO
    cache: dict[str, Optional[tuple[int, int]]] = {}

    def tamano(toma: dict):
        if toma.get("frame"):
            return int(toma["frame"][0]), int(toma["frame"][1])
        fuente = str(toma.get("source", ""))
        if fuente.startswith("video:"):
            return x1 - x0, y1 - y0
        if fuente.startswith("imagen:") and "/" in fuente:
            carpeta, nombre = fuente[len("imagen:"):].rsplit("/", 1)
            base = imagenes or RAIZ / "data" / carpeta
            if fuente not in cache:
                cache[fuente] = tamano_imagen(base, nombre)
            return cache[fuente]
        return None

    return tamano


def migrar_datos(datos: dict, tamano: Callable[[dict], Optional[tuple[int, int]]]) -> dict:
    """Copia v3 de los datos v2. Lanza ValueError con la lista de tomas que no se pudieron migrar."""
    if datos.get("version") != 2:
        raise ValueError(f"se esperaba version 2, el archivo es version {datos.get('version')}")
    nuevo = {k: v for k, v in datos.items() if k not in ("version", "signs")}
    nuevo = {"version": VERSION_VECTOR, "signs": {}, **nuevo}
    errores = []
    for etiqueta, entrada in datos["signs"].items():
        tomas = []
        for n, toma in enumerate(tomas_de(entrada)):
            frame = tamano(toma)
            if frame is None:
                errores.append(f"{etiqueta} toma {n} ({toma.get('source', 'sin source')}): tamaño de imagen desconocido")
                continue
            try:
                vector = migrar_vector(toma["vector"], frame)
            except (ValueError, KeyError) as e:
                errores.append(f"{etiqueta} toma {n} ({toma.get('source', 'sin source')}): {e}")
                continue
            t = {k: v for k, v in toma.items() if k not in ("vector", "frame")}
            tomas.append({"vector": [round(float(x), DECIMALES) for x in vector], **t,
                          "frame": [int(frame[0]), int(frame[1])]})
        resto = {k: v for k, v in entrada.items() if k not in ("takes", "vector")}
        nuevo["signs"][etiqueta] = {**resto, "takes": tomas}
    if errores:
        raise ValueError("No se puede migrar:\n  " + "\n  ".join(errores))
    return nuevo


def ruta_respaldo(destino: Path) -> Path:
    respaldo = destino.with_name(destino.stem + ".v2.json.bak")
    if respaldo.exists():
        sello = datetime.now().strftime("%Y%m%d-%H%M%S")
        respaldo = destino.with_name(f"{destino.stem}.v2.{sello}.json.bak")
    return respaldo


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--signs", type=Path, default=RUTA_SENAS)
    parser.add_argument("--imagenes", type=Path, default=None,
                        help="carpeta de las imágenes de referencia (por defecto data/<carpeta del source>)")
    parser.add_argument("--guardar", action="store_true", help="escribir (sin esto solo prueba)")
    args = parser.parse_args(argv)

    datos = json.loads(args.signs.read_text(encoding="utf-8"))
    if datos.get("version") == VERSION_VECTOR:
        print(f"{args.signs} ya está en version {VERSION_VECTOR}: no hay nada que migrar.")
        return 0
    try:
        nuevo = migrar_datos(datos, resolvedor(args.imagenes))
    except ValueError as e:
        print(e)
        return 1

    frames: dict[str, set] = {}
    for entrada in nuevo["signs"].values():
        for t in entrada["takes"]:
            frames.setdefault(str(t.get("source", "?")).split(":")[0], set()).add(tuple(t["frame"]))
    total = sum(len(e["takes"]) for e in nuevo["signs"].values())
    print(f"{len(nuevo['signs'])} señas, {total} tomas migradas a version {VERSION_VECTOR}.")
    for fuente, tams in frames.items():
        print(f"  {fuente:7} frames: {', '.join(f'{a}x{b}' for a, b in sorted(tams))}")

    if not args.guardar:
        print("\nPrueba sin guardar. Agregá --guardar para escribir.")
        return 0
    respaldo = ruta_respaldo(args.signs)
    shutil.copy2(args.signs, respaldo)
    escribir_signs(args.signs, nuevo)
    print(f"\nGuardado {args.signs}. Copia de la version 2 en {respaldo} (no se sube a git).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
