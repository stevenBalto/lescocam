"""Importa a signs.json las señas de una carpeta de imágenes (una imagen por seña).

El nombre del archivo es la etiqueta: A.png -> "A", CH.png -> "CH".
Cada imagen pasa por el mismo camino que la cámara (espejo, MediaPipe,
normalización con la proporción de la imagen) y queda como una toma de esa
seña, con "frame": [ancho, alto] de la imagen (signs.json version 3).

Uso:
    .venv/bin/python -m scripts.importar_imagenes data/dictionary            # prueba, no guarda
    .venv/bin/python -m scripts.importar_imagenes data/dictionary --guardar
    .venv/bin/python -m scripts.importar_imagenes data/dictionary --guardar --reemplazar

Por defecto se saltan las imágenes con nombre numérico (1.png, 2.png...):
los números comparten forma con letras y se separan después. --numeros las incluye.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from core.camara import Detector
from core.clasificador import RUTA_SENAS, confianza, escribir_signs, leer_signs, signs_vacio
from core.rasgos import rasgos

EXTENSIONES = {".png", ".jpg", ".jpeg", ".webp"}
DECIMALES = 6


def leer_imagenes(carpeta: Path, numeros: bool) -> list[Path]:
    rutas = [p for p in sorted(carpeta.iterdir())
             if p.is_file() and p.suffix.lower() in EXTENSIONES]
    if not numeros:
        rutas = [p for p in rutas if not p.stem.isdigit()]
    return rutas


def vector_de_imagen(detector: Detector, ruta: Path):
    imagen = cv2.imread(str(ruta))
    if imagen is None:
        return None, None, "no se pudo abrir"
    # La app espeja cada frame de la cámara (vista selfie) antes de detectar:
    # se hace lo mismo para que la toma salga por el mismo camino.
    mano = detector.procesar(cv2.flip(imagen, 1))
    if mano is None:
        return None, None, "no se detectó la mano"
    if mano.vector is None:
        return None, None, "mano degenerada"
    return mano.vector, mano.frame, None


def pares_parecidos(vectores: dict[str, np.ndarray], cuantos: int = 8):
    """Pares con mayor confianza entre sí según el clasificador (rasgos de forma)."""
    etiquetas = [e for e, v in vectores.items() if rasgos(v) is not None]
    if len(etiquetas) < 2:
        return []
    m = np.array([rasgos(vectores[e]) for e in etiquetas])
    sims = confianza(np.linalg.norm(m[:, None] - m[None], axis=2))
    pares = [(float(sims[i, j]), etiquetas[i], etiquetas[j])
             for i in range(len(etiquetas)) for j in range(i + 1, len(etiquetas))]
    return sorted(pares, reverse=True)[:cuantos]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("carpeta", type=Path)
    parser.add_argument("--guardar", action="store_true", help="escribir en signs.json (sin esto solo prueba)")
    parser.add_argument("--reemplazar", action="store_true",
                        help="borrar todas las señas actuales y dejar solo las importadas")
    parser.add_argument("--numeros", action="store_true", help="incluir imágenes con nombre numérico")
    parser.add_argument("--destino", type=Path, default=RUTA_SENAS)
    args = parser.parse_args(argv)

    rutas = leer_imagenes(args.carpeta, args.numeros)
    if not rutas:
        print(f"No hay imágenes en {args.carpeta}")
        return 1

    detector = Detector(confianza_deteccion=0.3)
    vectores, frames, fallidas = {}, {}, []
    try:
        for ruta in rutas:
            etiqueta = ruta.stem.upper()
            vector, frame, error = vector_de_imagen(detector, ruta)
            if error:
                fallidas.append((ruta.name, error))
                print(f"  ❌ {etiqueta:4} {error}")
            else:
                vectores[etiqueta], frames[etiqueta] = vector, frame
                print(f"  ✅ {etiqueta}")
    finally:
        detector.cerrar()

    print(f"\n{len(vectores)} importables, {len(fallidas)} fallidas.")
    print("Pares más parecidos (riesgo de confusión):")
    for sim, a, b in pares_parecidos(vectores):
        print(f"  {a:3} ~ {b:3}  {sim:.3f}")

    if not args.guardar:
        print("\nPrueba sin guardar. Agregá --guardar para escribir en signs.json.")
        return 0
    if not vectores:
        return 1

    destino: Path = args.destino
    datos = signs_vacio()
    if destino.exists() and not args.reemplazar:
        datos = leer_signs(destino)   # exige version 3: no se mezclan vectores de versiones distintas
    ahora = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for etiqueta, vector in vectores.items():
        toma = {
            "vector": [round(float(x), DECIMALES) for x in vector],
            "samples": 1,
            "recorded_at": ahora,
            "source": f"imagen:{args.carpeta.name}/{etiqueta}",
            "frame": [int(frames[etiqueta][0]), int(frames[etiqueta][1])],
        }
        datos["signs"].setdefault(etiqueta, {"takes": []})["takes"].append(toma)

    escribir_signs(destino, datos)
    print(f"\nGuardado en {destino} ({len(datos['signs'])} señas).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
