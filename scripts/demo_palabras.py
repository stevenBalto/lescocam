"""Demo en vivo del modo "palabra": cámara + la palabra reconocida.

Usa el mismo motor que la evaluación (core/cuerpo.DetectorCuerpo y
core/reconocedor_palabras.ReconocedorPalabras con data/reference/senas.db).
No toca la app de escritorio. Cerrala antes: comparten la cámara.

Cómo hacer una seña: brazos abajo (reposo) → seña → brazos abajo de nuevo.
La palabra aparece al volver al reposo.

Uso:
    .venv/bin/python -m scripts.demo_palabras
    .venv/bin/python -m scripts.demo_palabras --camara 1 --sin BEBÉ
Teclas: Q / ESC salir · B borrar historial.
"""
from __future__ import annotations

import argparse
import sys
import time

import cv2
import numpy as np

from core import senas_db
from core.camara import abrir_camara, leer_espejado
from core.cuerpo import DetectorCuerpo
from core.reconocedor_palabras import ReconocedorPalabras

CONEXIONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
              (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]
CUERPO = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]  # hombros y brazos


def _texto(img, txt, y, esc=0.7, color=(255, 255, 255), x=12, grosor=2):
    cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, esc, (0, 0, 0), grosor + 3, cv2.LINE_AA)
    cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, esc, color, grosor, cv2.LINE_AA)


def _dibujar(img, cuadro):
    alto, ancho = img.shape[:2]
    if cuadro.pose is not None:
        p = cuadro.pose
        for a, b in CUERPO:
            if p[a, 3] > 0.5 and p[b, 3] > 0.5:
                cv2.line(img, (int(p[a, 0] * ancho), int(p[a, 1] * alto)),
                         (int(p[b, 0] * ancho), int(p[b, 1] * alto)), (200, 200, 200), 2, cv2.LINE_AA)
    for puntos, lado, _ in cuadro.manos:
        color = (60, 200, 60) if lado == "Right" else (230, 140, 40)
        pts = [(int(x * ancho), int(y * alto)) for x, y, _ in puntos]
        for a, b in CONEXIONES:
            cv2.line(img, pts[a], pts[b], color, 2, cv2.LINE_AA)
        for q in pts:
            cv2.circle(img, q, 3, (255, 255, 255), -1, cv2.LINE_AA)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--camara", type=int, default=0)
    ap.add_argument("--sin", nargs="*", default=["BEBÉ"], help="palabras a dejar fuera (por defecto BEBÉ, que falla)")
    a = ap.parse_args(argv)

    todas = {e for e, _ in senas_db.leer()["plantillas"]}
    etiquetas = todas - set(a.sin or [])
    reconocedor = ReconocedorPalabras(senas_db.comparador(etiquetas=etiquetas))
    print(f"{len(etiquetas)} palabras cargadas. Q para salir.")

    try:
        cap = abrir_camara(a.camara)
    except RuntimeError:
        print("No se pudo abrir la cámara: cerrá la app de escritorio, que la está usando.")
        return 1
    detector = DetectorCuerpo()
    historial: list[str] = []
    inicio = time.monotonic()
    ultima_vista = None
    try:
        while True:
            frame = leer_espejado(cap)
            if frame is None:
                continue
            ahora = time.monotonic() - inicio
            cuadro = detector.procesar(frame, ahora)
            palabra = reconocedor.actualizar(cuadro, ahora)
            if palabra:
                historial = (historial + [palabra])[-6:]
                print(f"  → {palabra}", flush=True)
            if reconocedor.ultima is not None and reconocedor.ultima is not ultima_vista:
                ultima_vista = reconocedor.ultima
                p, conf, top = ultima_vista
                print("     top:", ", ".join(f"{e}={s:.2f}" for e, s in (top or [])[:3]),
                      "" if p else "(no alcanzó: no se dijo nada)", flush=True)

            _dibujar(frame, cuadro)
            alto, ancho = frame.shape[:2]
            if cuadro.pose is None:
                estado, color = "No veo el cuerpo: alejate un poco de la cámara", (0, 0, 255)
            elif reconocedor.activo:
                estado, color = "SEÑA EN CURSO... bajá los brazos al terminar", (0, 220, 255)
            else:
                estado, color = "En reposo: hacé una seña", (180, 255, 180)
            _texto(frame, estado, 30, 0.65, color)
            if ultima_vista is not None:
                p, conf, top = ultima_vista
                if p:
                    _texto(frame, p, alto - 70, 1.4, (60, 255, 60), grosor=3)
                else:
                    _texto(frame, "No la reconocí", alto - 70, 1.0, (0, 165, 255))
                _texto(frame, "  ".join(f"{e} {s:.0%}" for e, s in (top or [])[:3]), alto - 40, 0.55)
            _texto(frame, " · ".join(historial), alto - 12, 0.55, (220, 220, 220))
            cv2.imshow("LESCOCam · demo de palabras", frame)
            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), 27):
                break
            if tecla == ord("b"):
                historial, ultima_vista = [], None
                reconocedor.ultima = None
    finally:
        detector.cerrar()
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
