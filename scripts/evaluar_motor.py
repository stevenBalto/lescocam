"""Mide qué tan bien reconoce el motor, para comparar cambios con números.

Compara el método anterior ("coseno": similitud de coseno del vector de 63), el
de rasgos solo con tomas reales ("rasgos": core/clasificador.py) y rasgos más
tomas sintéticas ("rasgos+sint": core/sinteticas.py, generadas en cada prueba
SOLO desde las tomas oficiales de su referencia, para no hacer trampa) en:

  1. Validación cruzada por fuente (solo signs.json): las tomas de video se
     clasifican usando como referencia solo las de imagen, y al revés. Son dos
     personas distintas: es lo más parecido a "otra mano" que tenemos.
  2. Giro: las mismas consultas giradas en 3D alrededor de la muñeca
     (yaw = mano de costado, pitch = inclinada hacia adelante/atrás, roll = en el
     plano de la imagen) a ±15°, ±30° y ±45°.
  3. Con el material de data/dictionary/ (opcional, --extraer una vez):
     - cuadro a cuadro: cada frame del video contra las tomas de imagen;
     - proporción de cámara: la misma mano vista con una webcam 4:3 o 16:9
       (con la corrección de la version 3 los tres resultados deben ser iguales);
     - flujo: el video entero (con transiciones y letras con movimiento) pasado
       por el Aceptador, como en vivo. Cuenta letras aceptadas e inventadas.
  4. "Persona nueva": tomas de webcam (webcam:<persona>) contra (a) solo las
     oficiales y (b) oficiales + sintéticas, derechas y giradas ±15/30/45°.
     Ojo: el grabador solo guarda tomas que ya acepta contra las oficiales, así
     que (a) sale ~100% por construcción; sirve para ver que (b) no empeore.
  5. Números (categoria "numero"): pares de números parecidos y qué letra se
     leería en modo deletreo (no deben aparecer como letras).

Las sintéticas guardadas en signs.json no se usan como referencia acá: cada
método arma la suya para que la comparación sea justa.

Uso:
    .venv/bin/python -m scripts.evaluar_motor                 # solo signs.json
    .venv/bin/python -m scripts.evaluar_motor --extraer       # una vez: lee imágenes y video
    .venv/bin/python -m scripts.evaluar_motor --cuadros       # además usa lo extraído

Nada de esto escribe en signs.json. Lo extraído queda en data/dictionary/
(ignorado por git): son landmarks de material que no se redistribuye.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from core.aceptador import Aceptador
from core.clasificador import (RUTA_SENAS, Clasificador, categoria_de, confianza, leer_signs,
                               mejor_por_etiqueta, tomas_de)
from core.landmarks import normalizar_puntos, normalize_landmarks
from core.rasgos import rasgos
from core.sinteticas import generar

RUTA_EXTRAIDO = Path("data/dictionary/evaluacion_landmarks.json")
RUTA_VIDEO = Path("data/dictionary/videos/abecedario-lesco.mp4")
CARPETA_IMAGENES = Path("data/dictionary")
ANGULOS = (15, 30, 45)
EJES = ("yaw", "pitch", "roll")
CAMARAS = {"video (612x720)": None, "webcam 4:3 (640x480)": (640, 480), "webcam 16:9 (1280x720)": (1280, 720)}

# Método anterior, para la tabla "antes": coseno del vector crudo, umbral/margen viejos y
# 10 frames seguidos (~0.3 s a 30 fps).
COSENO = {"umbral": 0.92, "margen": 0.02, "segundos": 0.3, "frames_minimos": 10}


# ---------------------------------------------------------------- métodos

class Coseno:
    """El clasificador anterior (similitud de coseno), solo para comparar."""

    def __init__(self, etiquetas, vectores):
        m = np.asarray(vectores, dtype=np.float64)
        self._etiquetas = list(etiquetas)
        self._matriz = m / np.linalg.norm(m, axis=1, keepdims=True)

    def mejores(self, vector, k=2):
        v = np.asarray(vector, dtype=np.float64).reshape(-1)
        n = np.linalg.norm(v)
        if n == 0:
            return []
        return mejor_por_etiqueta(self._etiquetas, self._matriz @ (v / n))[:k]


FUENTES_OFICIALES = ("imagen", "video")


def con_sinteticas(etiquetas, vectores, fuentes=None):
    """Clasificador con las tomas dadas + sintéticas generadas SOLO desde las oficiales entre ellas."""
    etiquetas, vectores = list(etiquetas), np.asarray(vectores, dtype=np.float64)
    of = (np.ones(len(etiquetas), bool) if fuentes is None
          else np.isin(np.asarray(fuentes), FUENTES_OFICIALES))
    s_et, s_vec, _ = generar([e for e, o in zip(etiquetas, of) if o], vectores[of])
    if not s_et:
        return Clasificador.desde_tomas(etiquetas, vectores)
    return Clasificador.desde_tomas(etiquetas + list(s_et), np.vstack([vectores, s_vec]))


def metodos():
    """nombre -> (constructor(etiquetas, vectores, fuentes), parámetros del aceptador)."""
    return {"coseno": (lambda e, v, f=None: Coseno(e, v), COSENO),
            "rasgos": (lambda e, v, f=None: Clasificador.desde_tomas(e, v), parametros()),
            "rasgos+sint": (con_sinteticas, parametros())}


def parametros(aceptador: Aceptador | None = None) -> dict:
    a = aceptador or Aceptador()
    return {"umbral": a.umbral, "margen": a.margen, "segundos": a.segundos, "frames_minimos": a.frames_minimos}


def titulo(p: dict) -> str:
    return (f"umbral {p['umbral']}, margen {p['margen']}, "
            f"{p['segundos']} s y {p['frames_minimos']} frames mínimo")


# ---------------------------------------------------------------- utilidades

def cargar_signs(ruta: Path, categoria: str = "letra"):
    """(etiquetas, vectores, fuentes) de una categoría. fuente = lo de antes de ":" en source
    ("imagen", "video", "webcam", "sintetica")."""
    datos = leer_signs(ruta)
    etiquetas, vectores, fuentes = [], [], []
    for etiqueta, entrada in datos["signs"].items():
        if categoria_de(entrada) != categoria:
            continue
        for toma in tomas_de(entrada):
            etiquetas.append(etiqueta)
            vectores.append(np.asarray(toma["vector"], dtype=np.float64))
            fuentes.append(toma.get("source", "?").split(":")[0])
    return np.array(etiquetas), np.array(vectores), np.array(fuentes)


def rotacion(eje: str, grados: float) -> np.ndarray:
    a = np.radians(grados)
    c, s = np.cos(a), np.sin(a)
    if eje == "yaw":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    if eje == "pitch":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def girar(vector, matriz) -> np.ndarray:
    """Gira la mano alrededor de la muñeca y la vuelve a normalizar como landmarks.py."""
    pts = np.asarray(vector, dtype=np.float64).reshape(21, 3) @ matriz.T
    return normalizar_puntos(pts, "Right").astype(np.float64)


def evaluar(clasificador, etiquetas, consultas, umbral, margen):
    """Resultados por consulta: (real, top1, conf1, conf2)."""
    salida = []
    for real, vec in zip(etiquetas, consultas):
        top = clasificador.mejores(vec, 2)
        if not top:
            salida.append((real, None, 0.0, 0.0))
            continue
        segunda = top[1][1] if len(top) > 1 else 0.0
        salida.append((real, top[0][0], top[0][1], segunda))
    return resumir(salida, umbral, margen)


def resumir(res, umbral, margen):
    n = len(res)
    pasa = [r for r in res if r[1] is not None and r[2] >= umbral and r[2] - r[3] >= margen]
    return {
        "n": n,
        "exactitud": sum(r[0] == r[1] for r in res) / n,
        "acepta_bien": sum(r[0] == r[1] for r in pasa) / n,
        "acepta_mal": sum(r[0] != r[1] for r in pasa) / n,
        "margen": float(np.mean([r[2] - r[3] for r in res])),
        "confusiones": Counter((r[0], r[1]) for r in res if r[0] != r[1]),
    }


def fmt_pct(x):
    return f"{x * 100:5.1f}%"


def pares(confusiones, cuantos=8):
    return ", ".join(f"{a}→{b}×{n}" for (a, b), n in confusiones.most_common(cuantos)) or "-"


# ---------------------------------------------------------------- 1 y 2: signs.json

def evaluar_signs(ruta: Path):
    etiquetas, vectores, fuentes = cargar_signs(ruta)
    print(f"signs.json: {len(set(etiquetas))} letras, {len(etiquetas)} tomas "
          f"({', '.join(f'{f}={n}' for f, n in Counter(fuentes).items())})\n")
    direcciones = [("imagen", "video"), ("video", "imagen")]
    for nombre, (crear, p) in metodos().items():
        print(f"== {nombre}  ({titulo(p)})")
        for ref, con in direcciones:
            r, c = fuentes == ref, fuentes == con
            res = evaluar(crear(etiquetas[r], vectores[r], fuentes[r]), etiquetas[c], vectores[c],
                          p["umbral"], p["margen"])
            print(f"  ref {ref:6} → {con:6}: exactitud {fmt_pct(res['exactitud'])}  "
                  f"aceptadas bien {fmt_pct(res['acepta_bien'])}  mal {fmt_pct(res['acepta_mal'])}  "
                  f"margen medio {res['margen']:.3f}")
            print(f"      confusiones: {pares(res['confusiones'])}")
        print("  giro (promedio de ambas direcciones y ± del ángulo):")
        clasificadores = {ref: crear(etiquetas[fuentes == ref], vectores[fuentes == ref], fuentes[fuentes == ref])
                          for ref, _ in direcciones}
        for angulo in (0,) + ANGULOS:
            fila = []
            for eje in EJES:
                accs = []
                for signo in ((1,) if angulo == 0 else (1, -1)):
                    m = rotacion(eje, signo * angulo)
                    for ref, con in direcciones:
                        c = fuentes == con
                        consultas = [girar(v, m) for v in vectores[c]]
                        accs.append(evaluar(clasificadores[ref], etiquetas[c], consultas,
                                            p["umbral"], p["margen"])["exactitud"])
                fila.append(np.mean(accs))
            print(f"    ±{angulo:2}°  " + "  ".join(f"{e} {fmt_pct(a)}" for e, a in zip(EJES, fila))
                  + f"  | media {fmt_pct(np.mean(fila))}")
        print()


# ---------------------------------------------------------------- 4: tomas de webcam

def evaluar_webcam(ruta: Path, detalle: bool = False) -> None:
    """"Persona nueva": cada toma de webcam contra (a) solo oficiales y (b) oficiales + sintéticas.

    Nunca se usa ninguna toma de webcam como referencia.
    """
    etiquetas, vectores, fuentes = cargar_signs(ruta)
    w = fuentes == "webcam"
    if not w.any():
        return
    of = np.isin(fuentes, FUENTES_OFICIALES)
    a = Aceptador()
    refs = {"(a) oficiales": Clasificador.desde_tomas(etiquetas[of], vectores[of]),
            "(b) oficiales+sint": con_sinteticas(etiquetas[of], vectores[of])}
    print(f"== persona nueva: {w.sum()} tomas de webcam ({titulo(parametros(a))})")
    print("   (las tomas ya pasaron el control del grabador contra las oficiales: (a) ~100% por construcción)")
    for nombre, clasificador in refs.items():
        for angulo in (0,) + ANGULOS:
            filas = []
            for eje in (EJES if angulo else EJES[:1]):
                for signo in ((1, -1) if angulo else (1,)):
                    consultas = [girar(v, rotacion(eje, signo * angulo)) for v in vectores[w]]
                    filas.append(evaluar(clasificador, etiquetas[w], consultas, a.umbral, a.margen))
            r = {k: float(np.mean([f[k] for f in filas])) for k in ("exactitud", "acepta_bien", "acepta_mal", "margen")}
            print(f"  {nombre:19} giro ±{angulo:2}°: top-1 {fmt_pct(r['exactitud'])}  "
                  f"aceptadas bien {fmt_pct(r['acepta_bien'])}  mal {fmt_pct(r['acepta_mal'])}  "
                  f"margen medio {r['margen']:.3f}")
    if detalle:
        for etiqueta, vec in zip(etiquetas[w], vectores[w]):
            tops = [c.mejores(vec, 2) for c in refs.values()]
            print(f"  {etiqueta:3} " + " | ".join(
                f"{t[0][0]} {t[0][1]:.3f} margen {t[0][1] - t[1][1]:.3f} "
                f"({'acepta' if a._valida(t) is not None else 'no pasa'})" for t in tops))
    print()


# ---------------------------------------------------------------- 5: números

def evaluar_numeros(ruta: Path) -> None:
    """Números: pares parecidos entre sí y qué letra se leería con la mano de cada número."""
    etiquetas, vectores, fuentes = cargar_signs(ruta, "numero")
    of = np.isin(fuentes, FUENTES_OFICIALES)
    if not of.any():
        return
    nums = sorted(set(etiquetas[of]), key=lambda e: (len(e), e))
    print(f"== números: {len(nums)} señas, {of.sum()} tomas oficiales, {(fuentes == 'sintetica').sum()} sintéticas")
    r = {e: rasgos(vectores[of][list(etiquetas[of]).index(e)]) for e in nums}
    pares = sorted(((float(confianza(np.linalg.norm(r[x] - r[y]))), x, y)
                    for i, x in enumerate(nums) for y in nums[i + 1:]), reverse=True)
    print("  pares más parecidos (confianza; el umbral es "
          f"{Aceptador().umbral}): " + ", ".join(f"{x}~{y} {c:.3f}" for c, x, y in pares[:5]))
    num_clf = Clasificador.desde_tomas(etiquetas[of], vectores[of])
    let_et, let_vec, let_f = cargar_signs(ruta, "letra")
    let_of = np.isin(let_f, FUENTES_OFICIALES)
    letras = Clasificador.desde_tomas(let_et[let_of], let_vec[let_of])
    a = Aceptador()
    for e in nums:
        v = vectores[of][list(etiquetas[of]).index(e)]
        tn, tl = num_clf.mejores(v, 2), letras.mejores(v, 2)
        print(f"  {e}: modo números → {tn[0][0]} (2.º {tn[1][0]} {tn[1][1]:.3f}) | "
              f"modo letras → {tl[0][0]} {tl[0][1]:.3f} ({'acepta' if a._valida(tl) is not None else 'no pasa'})")
    print()


# ---------------------------------------------------------------- 3: material extraído

def extraer(ruta_video: Path, carpeta: Path, destino: Path) -> None:
    """Landmarks crudos (con tamaño de imagen) de cada imagen y de cada frame del video."""
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    from core.camara import asegurar_modelo
    from scripts.importar_video import CENTRO, CON_MOVIMIENTO, ORDEN, RECORTE_MANO, buscar_tramos

    opciones = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(asegurar_modelo())),
        running_mode=vision.RunningMode.IMAGE, num_hands=1,
        min_hand_detection_confidence=0.3, min_hand_presence_confidence=0.3)
    detector = vision.HandLandmarker.create_from_options(opciones)

    def detectar(bgr):
        # Igual que la app: el frame se espeja (vista selfie) antes de detectar.
        bgr = cv2.flip(bgr, 1)
        r = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
        if not r.hand_landmarks:
            return None
        alto, ancho = bgr.shape[:2]
        return {"puntos": [[round(p.x, 6), round(p.y, 6), round(p.z, 6)] for p in r.hand_landmarks[0]],
                "lado": r.handedness[0][0].category_name, "ancho": ancho, "alto": alto}

    try:
        imagenes = []
        for ruta in sorted(carpeta.glob("*.png")):
            if ruta.stem.isdigit():
                continue
            mano = detectar(cv2.imread(str(ruta)))
            if mano:
                imagenes.append(dict(mano, etiqueta=ruta.stem.upper()))
        fps, tramos = buscar_tramos(ruta_video)
        if len(tramos) != len(ORDEN):
            raise RuntimeError(f"Se esperaban {len(ORDEN)} tramos y salieron {len(tramos)}")
        x0, y0, x1, y1 = RECORTE_MANO
        cap = cv2.VideoCapture(str(ruta_video))
        cuadros = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            cuadros.append(detectar(frame[y0:y1, x0:x1]))
        cap.release()
    finally:
        detector.close()

    info_tramos = []
    for letra, (a, b) in zip(ORDEN, tramos):
        borde = int((b - a + 1) * (1 - CENTRO) / 2)
        info_tramos.append({"letra": letra, "inicio": a, "fin": b, "movimiento": letra in CON_MOVIMIENTO,
                            "centro": [a + borde, b - borde]})
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"video": ruta_video.name, "fps": fps, "imagenes": imagenes,
                                   "tramos": info_tramos, "cuadros": cuadros}) + "\n", encoding="utf-8")
    print(f"Extraído: {len(imagenes)} imágenes, {sum(c is not None for c in cuadros)}/{len(cuadros)} "
          f"cuadros con mano → {destino}")


def vector_con_camara(mano: dict, camara) -> np.ndarray:
    """Vector normalizado de la mano tal como la vería una cámara de ancho x alto.

    MediaPipe da x dividido por el ancho e y por el alto de la imagen (z en la
    escala de x). Se pasa a píxeles, se vuelve a dividir con el tamaño de la otra
    cámara y se normaliza con ese tamaño, como haría el Detector con esa cámara.
    """
    pts = np.array(mano["puntos"], dtype=np.float64)
    ancho, alto = camara if camara is not None else (mano["ancho"], mano["alto"])
    pts[:, 0] *= mano["ancho"] / ancho
    pts[:, 2] *= mano["ancho"] / ancho
    pts[:, 1] *= mano["alto"] / alto
    return normalize_landmarks(pts, mano["lado"], frame=(ancho, alto)).astype(np.float64)


def evaluar_cuadros(ruta_signs: Path, ruta: Path):
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    etiquetas, vectores, fuentes = cargar_signs(ruta_signs)
    fps, cuadros, tramos = datos["fps"], datos["cuadros"], datos["tramos"]
    quietos = [t for t in tramos if not t["movimiento"]]
    centrales = [(t["letra"], cuadros[i]) for t in quietos
                 for i in range(t["centro"][0], t["centro"][1] + 1) if cuadros[i] is not None]
    referencias = {"imagen": fuentes == "imagen", "todas": fuentes != "sintetica"}
    print(f"Material extraído: {len(centrales)} cuadros centrales de {len(quietos)} letras quietas, "
          f"{len(cuadros)} cuadros en total.\n")
    print("Referencias 'imagen' = otra persona (honesto). 'todas' = incluye tomas del mismo video "
          "(optimista: mide sobre todo la proporción de cámara).\n")

    for nombre, (crear, p) in metodos().items():
        print(f"== {nombre}  ({titulo(p)})")
        for ref, mascara in referencias.items():
            clasificador = crear(etiquetas[mascara], vectores[mascara], fuentes[mascara])
            for camara, tam in CAMARAS.items():
                res = evaluar(clasificador, [c[0] for c in centrales],
                              [vector_con_camara(c[1], tam) for c in centrales], p["umbral"], p["margen"])
                flujo = evaluar_flujo(clasificador, cuadros, tramos, fps, tam, p)
                print(f"  ref {ref:6} {camara:22}: cuadro a cuadro {fmt_pct(res['exactitud'])} "
                      f"(acepta bien {fmt_pct(res['acepta_bien'])}, mal {fmt_pct(res['acepta_mal'])})"
                      f" | flujo: {flujo['bien']}/{len(quietos)} letras, inventadas {flujo['inventadas']}"
                      f" (+{flujo['vecinas']} letra vecina, +{flujo['en_movimiento']} en letras con movimiento), "
                      f"demora mediana {flujo['demora']:.2f}s")
                if camara.startswith("webcam 4:3"):
                    print(f"      confusiones: {pares(res['confusiones'])}")
                    if flujo["detalle"]:
                        print(f"      inventadas en flujo: {flujo['detalle']}")
        print()


def evaluar_flujo(clasificador, cuadros, tramos, fps, camara, p):
    """Pasa el video entero por el Aceptador, frame a frame, como la app en vivo."""
    letra_de, mov, vecinas = {}, set(), {}
    for n, t in enumerate(tramos):
        # El rótulo cambia antes o después que la mano: decir la letra anterior o
        # la siguiente en un tramo no es inventar, se cuenta aparte.
        vecinas[t["letra"]] = {tramos[m]["letra"] for m in (n - 1, n + 1) if 0 <= m < len(tramos)}
        for i in range(t["inicio"], t["fin"] + 1):
            letra_de[i] = t["letra"]
            if t["movimiento"]:
                mov.add(i)
    aceptador = Aceptador(**p)
    vistas, demoras, inventadas, en_mov, en_borde = set(), [], Counter(), 0, 0
    inicio = {t["letra"]: t["inicio"] for t in tramos}
    for i, mano in enumerate(cuadros):
        if mano is None:
            aceptador.mano_perdida()
            continue
        letra = aceptador.actualizar(clasificador.mejores(vector_con_camara(mano, camara), 2), i / fps)
        if letra is None:
            continue
        real = letra_de.get(i)
        if letra == real:
            if real not in vistas:
                demoras.append((i - inicio[real]) / fps)
            vistas.add(real)
        elif i in mov:
            en_mov += 1
        elif letra in vecinas.get(real, ()):
            en_borde += 1
        else:
            inventadas[(real or "-", letra)] += 1
    return {"bien": len(vistas), "inventadas": sum(inventadas.values()), "en_movimiento": en_mov,
            "vecinas": en_borde,
            "demora": float(np.median(demoras)) if demoras else float("nan"),
            "detalle": ", ".join(f"en {a} dijo {b}×{n}" for (a, b), n in inventadas.most_common())}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--signs", type=Path, default=RUTA_SENAS)
    parser.add_argument("--extraer", action="store_true", help="leer imágenes y video de data/dictionary/")
    parser.add_argument("--cuadros", action="store_true", help="evaluar también con lo extraído")
    parser.add_argument("--detalle", action="store_true", help="listar cada toma de webcam")
    args = parser.parse_args(argv)

    if args.extraer:
        extraer(RUTA_VIDEO, CARPETA_IMAGENES, RUTA_EXTRAIDO)
        return 0
    evaluar_signs(args.signs)
    evaluar_webcam(args.signs, args.detalle)
    evaluar_numeros(args.signs)
    if args.cuadros:
        if not RUTA_EXTRAIDO.exists():
            print(f"No existe {RUTA_EXTRAIDO}: corré primero con --extraer")
            return 1
        evaluar_cuadros(args.signs, RUTA_EXTRAIDO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
