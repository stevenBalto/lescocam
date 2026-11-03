"""Graba tomas con la webcam para sumar variedad (otras manos, cámaras, luz, ángulos).

Cada toma se compara contra la referencia OFICIAL (imagen:/video:) de su
categoría (letras o números; nunca contra webcam: ni sintetica:) y solo se puede
guardar si queda aceptada. Así no entran señas mal hechas.

Uso:
    .venv/bin/python -m scripts.recorder A B C --persona steven [--camara 0] [--tomas 5]

Teclas: ESPACIO graba (cuenta 3 s y captura ~1 s) · G guarda (solo si ✅) ·
R repite · N siguiente letra · Q/ESC salir.

Letras con movimiento (J, LL, Ñ, RR, Z, las de data/reference/movimientos.json):
la captura dura CAPTURA_MOVIMIENTO_S; hay que empezar con la postura inicial
quieta, hacer el gesto y quedarse quieto al final. El gesto se recorta con el
mismo Segmentador del motor y se compara SOLO contra las plantillas oficiales
(video:/imagen:) con el mismo DTW; se guarda solo si queda aceptado.

Contrato (signs.json version 3): agrega a takes de la letra {"vector", "samples",
"recorded_at", "source": "webcam:<persona>", "frame": [ancho, alto]}. El vector ya
viene corregido por la proporción del frame (core/landmarks.py); "frame" queda
como registro del tamaño de la cámara. Las letras con movimiento agregan una toma
a movimientos.json (formato en core/movimiento.py) con source "webcam:<persona>".
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

from core.aceptador import MARGEN
from core.clasificador import CATEGORIAS, RUTA_SENAS, Clasificador, escribir_signs, leer_signs, tomas_de
from core.movimiento import (RUTA_MOVIMIENTOS, TIPO, ReconocedorMovimiento, cuadros_de_toma, escribir_movimientos,
                             leer_movimientos, recortar_gesto, toma_desde_cuadros)
from core.rasgos import rasgos
from core.referencia import cargar_oficiales, es_oficial

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_IMAGENES = RAIZ / "data" / "dictionary"
DECIMALES = 6
CUENTA_S = 3.0
CAPTURA_S = 1.0
CAPTURA_MOVIMIENTO_S = 3.0
MIN_VALIDOS = 0.6      # fracción mínima de frames con mano
MAX_DISPERSION = 0.35  # distancia media de los rasgos de cada frame al promedio (ver limitaciones)

ACEPTADA, DUDOSA, RECHAZADA = "aceptada", "dudosa", "rechazada"
ICONO = {ACEPTADA: "OK", DUDOSA: "DUDOSA", RECHAZADA: "RECHAZADA"}


def evaluar_toma(vector, etiqueta: str, clasificador_oficial: Clasificador, k: int = 3):
    """Control de calidad puro. Devuelve (estado, mensaje, top) con top = [(letra, confianza)]."""
    top = clasificador_oficial.mejores(vector, k)
    if not top:
        return RECHAZADA, "no se pudo leer la mano; probá de nuevo", []
    primera, conf = top[0]
    if primera != etiqueta:
        return (RECHAZADA, f"esto se parece más a {primera} que a {etiqueta}; "
                           "revisá la forma con la imagen de referencia", top)
    margen = conf - top[1][1] if len(top) > 1 else 1.0
    if conf >= clasificador_oficial.umbral and margen >= MARGEN:
        return ACEPTADA, f"{etiqueta} clara ({conf:.0%}); apretá G para guardar", top
    return DUDOSA, f"se parece a {etiqueta} pero no es clara; comparala con la referencia", top


def clasificadores_oficiales(ruta: Path) -> dict:
    """seña -> Clasificador con SOLO las tomas oficiales de su categoría.

    Las tomas de webcam y las sintéticas no cuentan. Un número se controla contra
    los números y una letra contra las letras (2 y V tienen la misma forma).
    """
    por_categoria = {}
    for categoria in CATEGORIAS:
        etiquetas, vectores = cargar_oficiales(ruta, categoria)
        if etiquetas:
            clasificador = Clasificador.desde_tomas(etiquetas, vectores)
            por_categoria.update((e, clasificador) for e in etiquetas)
    return por_categoria


def movimiento_oficial(ruta: Path = RUTA_MOVIMIENTOS) -> Optional[ReconocedorMovimiento]:
    """Reconocedor con SOLO las plantillas oficiales de movimientos.json (None si no hay)."""
    try:
        datos = leer_movimientos(ruta)
    except (OSError, ValueError):
        return None
    plantillas = [(e, cuadros_de_toma(t)) for e, entrada in datos["signs"].items()
                  for t in entrada.get("takes", []) if es_oficial(t)]
    try:
        return ReconocedorMovimiento.desde_plantillas(plantillas)
    except ValueError:
        return None


def evaluar_gesto(cuadros: list, tiempos: list, etiqueta: str, oficial: ReconocedorMovimiento):
    """Control de calidad de una letra con movimiento. (estado, mensaje, top, gesto recortado)."""
    gesto = recortar_gesto(cuadros, tiempos)
    if not gesto:
        return RECHAZADA, "no se vio movimiento: empezá quieto, hacé el gesto y quedate quieto", [], None
    top = oficial.mejores(gesto, 3)
    if not top or top[0][1] <= 0:
        return RECHAZADA, f"el movimiento no se parece a {etiqueta}; miralo de nuevo en el video", top, gesto
    primera, conf = top[0]
    if primera != etiqueta:
        return RECHAZADA, f"esto se parece más a {primera} que a {etiqueta}", top, gesto
    segunda = top[1][1] if len(top) > 1 else 0.0
    if conf >= oficial.umbral and conf - segunda >= oficial.margen:
        return ACEPTADA, f"{etiqueta} clara ({conf:.0%}); apretá G para guardar", top, gesto
    return DUDOSA, f"se parece a {etiqueta} pero no es clara; repetí el gesto", top, gesto


def guardar_gesto(ruta: Path, etiqueta: str, gesto: list, persona: str, frame: tuple, fps: float) -> dict:
    """Agrega el gesto como toma "webcam:<persona>" de la letra en movimientos.json."""
    ruta = Path(ruta)
    datos = leer_movimientos(ruta)
    toma = toma_desde_cuadros(gesto, f"webcam:{persona}", fps, frame,
                              datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    datos["signs"].setdefault(etiqueta, {"categoria": "letra", "tipo": TIPO, "takes": []})["takes"].append(toma)
    escribir_movimientos(ruta, datos)
    return toma


def promediar_frames(vectores: list, total: int):
    """Une los frames de una captura. Devuelve (vector, n_validos, error).

    vectores: vector 63 de cada frame con mano (None o ausentes no cuentan);
    total: frames leídos. error es None si la toma sirve.
    """
    validos = [np.asarray(v, dtype=np.float64) for v in vectores if v is not None and rasgos(v) is not None]
    if total <= 0 or len(validos) < MIN_VALIDOS * total:
        return None, len(validos), "se perdió la mano en muchos frames; ponela bien visible"
    r = np.array([rasgos(v) for v in validos])
    if np.linalg.norm(r - r.mean(axis=0), axis=1).mean() > MAX_DISPERSION:
        return None, len(validos), "mantené la mano quieta"
    return np.mean(validos, axis=0), len(validos), None


def guardar_toma(ruta: Path, etiqueta: str, vector, muestras: int, persona: str, frame: tuple) -> dict:
    """Agrega la toma a takes de la etiqueta. Relee el JSON justo antes y escribe atómico."""
    ruta = Path(ruta)
    datos = leer_signs(ruta)
    toma = {
        "vector": [round(float(x), DECIMALES) for x in vector],
        "samples": int(muestras),
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": f"webcam:{persona}",
        "frame": [int(frame[0]), int(frame[1])],
    }
    entrada = datos["signs"][etiqueta]
    if "takes" not in entrada:
        entrada["takes"] = tomas_de(entrada)
        entrada.pop("vector", None)
    entrada["takes"].append(toma)
    escribir_signs(ruta, datos)
    return toma


def resumen(stats: dict, motivos: Counter) -> str:
    lineas = ["", "Resumen:"]
    for letra, c in stats.items():
        lineas.append(f"  {letra:3} aceptadas {c[ACEPTADA]} · dudosas {c[DUDOSA]} · rechazadas {c[RECHAZADA]}")
    if motivos:
        lineas.append("Motivos de rechazo más comunes:")
        lineas += [f"  {n}x {m}" for m, n in motivos.most_common(3)]
    return "\n".join(lineas)


# ---------------------------------------------------------------- ventana

def _texto(cv2, img, txt, y, color=(255, 255, 255), esc=0.6):
    cv2.putText(img, txt, (10, y), cv2.FONT_HERSHEY_SIMPLEX, esc, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, txt, (10, y), cv2.FONT_HERSHEY_SIMPLEX, esc, color, 1, cv2.LINE_AA)


def _referencia(cv2, letra, alto):
    lado = alto
    img = cv2.imread(str(CARPETA_IMAGENES / f"{letra}.png")) if (CARPETA_IMAGENES / f"{letra}.png").exists() else None
    panel = np.full((alto, lado, 3), 40, np.uint8)
    if img is None:
        cv2.putText(panel, "sin referencia", (20, alto // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
        return panel
    h, w = img.shape[:2]
    f = min(lado / w, alto / h)
    img = cv2.resize(img, (max(1, int(w * f)), max(1, int(h * f))))
    y0, x0 = (alto - img.shape[0]) // 2, (lado - img.shape[1]) // 2
    panel[y0:y0 + img.shape[0], x0:x0 + img.shape[1]] = img
    cv2.putText(panel, "referencia oficial", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
    return panel


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("letras", nargs="+")
    ap.add_argument("--persona", required=True)
    ap.add_argument("--camara", type=int, default=0)
    ap.add_argument("--tomas", type=int, default=5)
    ap.add_argument("--destino", type=Path, default=RUTA_SENAS)
    ap.add_argument("--movimientos", type=Path, default=RUTA_MOVIMIENTOS)
    a = ap.parse_args(argv)

    import cv2
    from core.camara import Detector, abrir_camara, dibujar_mano, leer_espejado

    from core.movimiento import cuadro_de_mano
    persona = "".join(c for c in a.persona.strip().lower() if c.isalnum() or c in "-_") or "anonimo"
    oficial = clasificadores_oficiales(a.destino)
    oficial_mov = movimiento_oficial(a.movimientos)
    con_movimiento = set(oficial_mov.etiquetas) if oficial_mov else set()
    letras = []
    for l in (x.upper() for x in a.letras):
        if l in oficial or l in con_movimiento:
            letras.append(l)
        else:
            print(f"{l}: no tiene tomas oficiales, se salta (no se definen señas nuevas).")
    if not letras:
        return 1

    try:
        cap = abrir_camara(a.camara)
    except RuntimeError:
        print(f"No se pudo abrir la cámara {a.camara}: cerrá la app de escritorio, que está usando la cámara.")
        return 1
    detector = Detector()
    stats = {l: Counter() for l in letras}
    motivos: Counter = Counter()
    ventana = "LESCOCam recorder"
    salir = False
    try:
        for letra in letras:
            if salir:
                break
            mov = letra in con_movimiento
            hechas = (sum(1 for t in leer_movimientos(a.movimientos)["signs"][letra]["takes"]
                          if t.get("source") == f"webcam:{persona}") if mov
                      else sum(1 for t in _tomas_webcam(a.destino, letra, persona)))
            cuadros, tiempos_captura = [], []
            aceptadas = 0
            resultado = None  # (estado, msg, top, vector, n, frame) tras evaluar
            aviso = ""
            fase, t0, vals, total = "espera", 0.0, [], 0
            while aceptadas < a.tomas and not salir:
                frame = leer_espejado(cap)
                if frame is None:
                    print("La cámara dejó de responder.")
                    salir = True
                    break
                alto, ancho = frame.shape[:2]
                mano = detector.procesar(frame)
                limpio = frame.copy()
                if mano:
                    dibujar_mano(frame, mano)
                ahora = time.monotonic()
                if fase == "cuenta":
                    resto = CUENTA_S - (ahora - t0)
                    if resto <= 0:
                        fase, t0, vals, total = "captura", ahora, [], 0
                        cuadros, tiempos_captura = [], []
                    else:
                        cv2.putText(frame, str(int(resto) + 1), (ancho // 2 - 30, alto // 2 + 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 255), 6)
                if fase == "captura" and mov:
                    cuadros.append(cuadro_de_mano(mano, ahora))
                    tiempos_captura.append(ahora)
                    cv2.circle(frame, (ancho - 25, 25), 10, (0, 0, 255), -1)
                    if ahora - t0 >= CAPTURA_MOVIMIENTO_S:
                        fase = "espera"
                        est, msg, top, gesto = evaluar_gesto(cuadros, tiempos_captura, letra, oficial_mov)
                        stats[letra][est] += 1
                        print(f"  {letra}: {est} | " + ", ".join(f"{e}={s:.2f}" for e, s in top), flush=True)
                        if est == RECHAZADA:
                            motivos[msg.split(";")[0]] += 1
                        fps = (len(tiempos_captura) - 1) / max(tiempos_captura[-1] - tiempos_captura[0], 1e-6)
                        resultado, aviso = (est, msg, top, gesto, fps, (ancho, alto)), ""
                elif fase == "captura":
                    total += 1
                    vals.append(mano.vector if mano else None)
                    cv2.circle(frame, (ancho - 25, 25), 10, (0, 0, 255), -1)
                    if ahora - t0 >= CAPTURA_S:
                        vec, n, err = promediar_frames(vals, total)
                        fase = "espera"
                        if err:
                            aviso, resultado = err, None
                        else:
                            est, msg, top = evaluar_toma(vec, letra, oficial[letra])
                            stats[letra][est] += 1
                            print(f"  {letra}: {est} | " + ", ".join(f"{e}={s:.2f}" for e, s in top), flush=True)
                            if est == RECHAZADA:
                                motivos[msg.split(";")[0]] += 1
                            resultado, aviso = (est, msg, top, vec, n, (ancho, alto)), ""
                _texto(cv2, frame, f"Letra {letra}  aceptadas {aceptadas}/{a.tomas}  (ya tenias {hechas} de {persona})", 25)
                _texto(cv2, frame, "ESPACIO grabar | G guardar | R repetir | N siguiente | Q salir", alto - 12, esc=0.5)
                if mov and not resultado:
                    _texto(cv2, frame, f"con movimiento ({CAPTURA_MOVIMIENTO_S:.0f} s): quieto, gesto, quieto",
                           alto - 40, (0, 255, 255), 0.5)
                if aviso:
                    _texto(cv2, frame, aviso, 55, (0, 200, 255))
                if resultado:
                    est, msg, top = resultado[:3]
                    color = {ACEPTADA: (0, 220, 0), DUDOSA: (0, 200, 255), RECHAZADA: (0, 0, 255)}[est]
                    _texto(cv2, frame, f"{ICONO[est]}: {msg}", 55, color, 0.55)
                    _texto(cv2, frame, "top: " + "  ".join(f"{l} {c:.0%}" for l, c in top), 85)
                cv2.imshow(ventana, np.hstack([frame, _referencia(cv2, letra, alto)]))
                k = cv2.waitKey(1) & 0xFF
                if k in (ord("q"), 27):
                    salir = True
                elif k == ord("n"):
                    break
                elif k == ord(" ") and fase == "espera":
                    fase, t0, resultado, aviso = "cuenta", ahora, None, ""
                elif k == ord("r"):
                    fase, resultado, aviso = "espera", None, ""
                elif k == ord("g"):
                    if resultado and resultado[0] == ACEPTADA:
                        _, _, _, vec, n, fr = resultado
                        if mov:
                            guardar_gesto(a.movimientos, letra, vec, persona, fr, n)
                        else:
                            guardar_toma(a.destino, letra, vec, n, persona, fr)
                        aceptadas += 1
                        resultado = None
                        aviso = "guardada"
                    else:
                        aviso = "solo se guardan tomas aceptadas"
    finally:
        cap.release()
        detector.cerrar()
        cv2.destroyAllWindows()
    print(resumen(stats, motivos))
    return 0


def _tomas_webcam(ruta, letra, persona):
    datos = leer_signs(ruta)
    return [t for t in tomas_de(datos["signs"].get(letra, {})) if t.get("source") == f"webcam:{persona}"]


if __name__ == "__main__":
    sys.exit(main())
