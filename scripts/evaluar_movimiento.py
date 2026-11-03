"""Mide el reconocimiento de las letras con movimiento (J, LL, Ñ, RR, Z) y su convivencia con las quietas.

Usa los landmarks ya extraídos del video (data/dictionary/evaluacion_landmarks.json,
`scripts.evaluar_motor --extraer`) y las plantillas de data/reference/movimientos.json
(que guardan en qué segundos del video está cada gesto).

  1. Variantes de prueba: con UNA sola plantilla por letra no hay validación
     cruzada real. Cada gesto del video se rehace con cambios realistas (más lento
     y más rápido, 15 fps, giros de la mano y de la cámara, cámaras 4:3 y 16:9,
     la otra mano, más o menos recorrido, ruido, recortes del principio o del
     final) con la postura inicial quieta antes y la final quieta después, y se
     pasa por el Reconocedor combinado como en vivo. Se cuenta qué dice.
  2. Negativas: las letras quietas del video con temblor y con un deslizamiento
     corto, y los gestos con muy poco recorrido, no deben decir letras con movimiento.
  3. Flujo: el video ENTERO (25 quietas, 5 con movimiento y las transiciones) por
     el Aceptador solo (antes) y por el Reconocedor combinado (después).
  4. --barrido: prueba pesos de forma / orientación / trayectoria del descriptor.

Las variantes salen del mismo gesto de la plantilla: miden robustez a cámara,
velocidad y fps, no a otra persona (para eso hacen falta grabaciones propias).

Uso:
    .venv/bin/python -m scripts.evaluar_movimiento
    .venv/bin/python -m scripts.evaluar_movimiento --barrido
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from core.aceptador import Aceptador
from core.clasificador import RUTA_SENAS, Clasificador
from core.landmarks import normalize_landmarks
from core.movimiento import (RUTA_MOVIMIENTOS, ReconocedorMovimiento, cuadro_de_puntos, cuadros_de_toma,
                             leer_movimientos)
from core.reconocedor import Reconocedor
from scripts.evaluar_motor import RUTA_EXTRAIDO, cargar_signs, con_sinteticas, evaluar_flujo

SEGUNDOS_QUIETA = 0.7          # postura quieta antes y después de cada variante
RUIDO_QUIETA = 0.01            # temblor de la postura quieta (fracción de la escala de la mano)


# ---------------------------------------------------------------- material

def cargar_extraido(ruta: Path = RUTA_EXTRAIDO) -> dict:
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}: corré .venv/bin/python -m scripts.evaluar_motor --extraer")
    return json.loads(ruta.read_text(encoding="utf-8"))


def ventanas_de(ruta: Path = RUTA_MOVIMIENTOS, video: str | None = None) -> dict:
    """letra -> (inicio, fin) en segundos del video, de las tomas "video:" de movimientos.json."""
    datos = leer_movimientos(ruta)
    salida = {}
    for letra, entrada in datos["signs"].items():
        for toma in entrada["takes"]:
            if toma["source"].startswith("video:") and "inicio" in toma and (video is None or toma["source"] == f"video:{video}"):
                salida[letra] = (toma["inicio"], toma["fin"])
    return salida


def armar(mano: dict, t: float, camara=None):
    """(Cuadro o None, vector de 63 o None) de un cuadro crudo, como lo vería el Detector."""
    pts = np.asarray(mano["puntos"], dtype=np.float64)
    frame = (mano["ancho"], mano["alto"])
    if camara is not None:
        pts, frame = _otra_camara(pts, frame, camara)
    try:
        vector = normalize_landmarks(pts, mano["lado"], frame=frame).astype(np.float64)
    except ValueError:
        return None, None
    return cuadro_de_puntos(pts, mano["lado"], frame, t, vector), vector


def _otra_camara(pts, frame, camara):
    """La misma escena vista por una cámara más ancha (el recorte del video queda en el centro)."""
    ancho, alto = frame
    nuevo_ancho, nuevo_alto = camara
    f = nuevo_alto / alto                   # misma densidad de píxeles en vertical
    sobra = (nuevo_ancho - ancho * f) / 2
    q = pts.copy()
    q[:, 0] = (pts[:, 0] * ancho * f + sobra) / nuevo_ancho
    q[:, 2] = pts[:, 2] * ancho * f / nuevo_ancho
    return q, (nuevo_ancho, nuevo_alto)


# ---------------------------------------------------------------- variantes

def _a_px(mano):
    p = np.asarray(mano["puntos"], dtype=np.float64).copy()
    p[:, 0] *= mano["ancho"]
    p[:, 1] *= mano["alto"]
    p[:, 2] *= mano["ancho"]
    return p


def _de_px(mano, p):
    q = p.copy()
    q[:, 0] /= mano["ancho"]
    q[:, 1] /= mano["alto"]
    q[:, 2] /= mano["ancho"]
    return dict(mano, puntos=q.tolist())


def _rot(eje, grados):
    a = np.radians(grados)
    c, s = np.cos(a), np.sin(a)
    return {"yaw": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            "pitch": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
            "roll": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[eje]


def transformar(manos: list, *, giro=None, roll_camara=0.0, espejo=False, amplitud=1.0, ruido=0.0, semilla=0):
    """Aplica cambios a una secuencia de cuadros crudos (dicts del material extraído)."""
    rng = np.random.default_rng(semilla)
    validas = [m for m in manos if m is not None]
    if not validas:
        return manos
    p0 = _a_px(validas[0])[0]
    salida = []
    for m in manos:
        if m is None:
            salida.append(None)
            continue
        p = _a_px(m)
        escala = np.linalg.norm(p[9] - p[0])
        if amplitud != 1.0:                      # más o menos recorrido de la muñeca
            p = p + (amplitud - 1.0) * (p[0] - p0) * np.array([1, 1, 0])
        if giro is not None:                     # la mano girada sobre la muñeca
            p = (p - p[0]) @ _rot(*giro).T + p[0]
        if roll_camara:                          # la cámara inclinada: gira toda la imagen
            centro = np.array([m["ancho"] / 2, m["alto"] / 2, 0])
            p = (p - centro) @ _rot("roll", roll_camara).T + centro
        if ruido:
            p = p + rng.normal(0, ruido * escala, p.shape) * np.array([1, 1, 0.5])
        nueva = _de_px(m, p)
        if espejo:                               # la otra mano haciendo el gesto espejado
            q = np.asarray(nueva["puntos"])
            q[:, 0] = 1.0 - q[:, 0]
            q[:, 2] = q[:, 2]
            nueva = dict(nueva, puntos=q.tolist(), lado="Right" if m["lado"] == "Left" else "Left")
        salida.append(nueva)
    return salida


def con_quietas(manos: list, fps: float, segundos: float = SEGUNDOS_QUIETA, semilla: int = 1):
    """Postura inicial quieta antes y final quieta después (con un poco de temblor)."""
    validas = [m for m in manos if m is not None]
    n = int(round(segundos * fps))
    antes = transformar([validas[0]] * n, ruido=RUIDO_QUIETA, semilla=semilla)
    despues = transformar([validas[-1]] * n, ruido=RUIDO_QUIETA, semilla=semilla + 1)
    return antes + list(manos) + despues


def tiempos(n: int, fps: float, factor=1.0, inicio_gesto=0, fin_gesto=None, no_uniforme=False):
    """Tiempo de cada cuadro: el gesto (entre inicio_gesto y fin_gesto) va `factor` veces más lento."""
    fin_gesto = n if fin_gesto is None else fin_gesto
    t, ahora = [], 0.0
    for i in range(n):
        t.append(ahora)
        dt = 1.0 / fps
        if inicio_gesto <= i < fin_gesto:
            if no_uniforme:
                medio = (inicio_gesto + fin_gesto) / 2
                dt *= 1.4 if i < medio else 0.7
            else:
                dt *= factor
        ahora += dt
    return t


VARIANTES = {
    "original": {},
    "lenta x1.3": {"factor": 1.3},
    "rápida x0.7": {"factor": 0.7},
    "no uniforme": {"no_uniforme": True},
    "15 fps": {"paso": 2},
    "15 fps rápida": {"paso": 2, "factor": 0.7},
    "yaw +15°": {"giro": ("yaw", 15)},
    "yaw -15°": {"giro": ("yaw", -15)},
    "pitch +15°": {"giro": ("pitch", 15)},
    "pitch -15°": {"giro": ("pitch", -15)},
    "cámara girada +10°": {"roll_camara": 10},
    "cámara girada -10°": {"roll_camara": -10},
    "webcam 4:3": {"camara": (640, 480)},
    "webcam 16:9": {"camara": (1280, 720)},
    "otra mano": {"espejo": True},
    "recorrido x0.7": {"amplitud": 0.7},
    "recorrido x1.3": {"amplitud": 1.3},
    "ruido 2%": {"ruido": 0.02},
    "sin el 15% inicial": {"recorte": (0.15, 0.0)},
    "sin el 15% final": {"recorte": (0.0, 0.15)},
}
NEGATIVAS = {"recorrido x0.3": {"amplitud": 0.3}}


def secuencia_variante(manos: list, fps: float, v: dict):
    """(manos, tiempos, camara) de una variante del gesto `manos`."""
    a, b = v.get("recorte", (0.0, 0.0))
    n = len(manos)
    manos = manos[int(round(a * n)):n - int(round(b * n))]
    manos = transformar(manos, giro=v.get("giro"), roll_camara=v.get("roll_camara", 0.0),
                        espejo=v.get("espejo", False), amplitud=v.get("amplitud", 1.0), ruido=v.get("ruido", 0.0))
    q = int(round(SEGUNDOS_QUIETA * fps))
    completas = con_quietas(manos, fps)
    t = tiempos(len(completas), fps, v.get("factor", 1.0), q, q + len(manos), v.get("no_uniforme", False))
    paso = v.get("paso", 1)
    return completas[::paso], t[::paso], v.get("camara")


def pasar(reconocedor: Reconocedor, manos: list, t: list, camara=None) -> list:
    """Pasa una secuencia por el Reconocedor combinado: [(tiempo, letra), ...]."""
    salida = []
    for mano, ti in zip(manos, t):
        cuadro, vector = (None, None) if mano is None else armar(mano, ti, camara)
        for letra in reconocedor.actualizar_cuadro(cuadro, vector, ti):
            salida.append((ti, letra))
    return salida


# ---------------------------------------------------------------- armado del motor

def plantillas_de(ruta: Path = RUTA_MOVIMIENTOS) -> list:
    datos = leer_movimientos(ruta)
    return [(e, cuadros_de_toma(t)) for e, entrada in datos["signs"].items() for t in entrada["takes"]]


def clasificadores_quietas(ruta_signs: Path = RUTA_SENAS) -> dict:
    """"imagen+sint": otra persona (honesto) · "app": todo signs.json, como la app."""
    etiquetas, vectores, fuentes = cargar_signs(ruta_signs)
    im = fuentes == "imagen"
    return {"imagen+sint": con_sinteticas(etiquetas[im], vectores[im], fuentes[im]),
            "app (signs.json)": Clasificador(ruta_signs)}


def nuevo_reconocedor(clasificador, plantillas, **kw) -> Reconocedor:
    mov = ReconocedorMovimiento.desde_plantillas(plantillas, **kw)
    return Reconocedor(clasificador, Aceptador(), mov, plantillas)


# ---------------------------------------------------------------- 1 y 2: variantes y negativas

def gesto_crudo(datos: dict, ventana) -> list:
    fps = datos["fps"]
    a, b = int(round(ventana[0] * fps)), int(round(ventana[1] * fps))
    return datos["cuadros"][a:b + 1]


def evaluar_variantes(datos, ventanas, clasificador, plantillas, kw=None, detalle=True):
    kw = kw or {}
    fps = datos["fps"]
    letras = sorted(ventanas)
    tabla, confusiones, total, bien = {}, Counter(), 0, 0
    for nombre, v in VARIANTES.items():
        fila = {}
        for letra in letras:
            manos, t, cam = secuencia_variante(gesto_crudo(datos, ventanas[letra]), fps, v)
            dichas = [l for _, l in pasar(nuevo_reconocedor(clasificador, plantillas, **kw), manos, t, cam)]
            ok = dichas == [letra]
            fila[letra] = "ok" if ok else ("-" if not dichas else "+".join(dichas))
            total += 1
            bien += ok
            for l in dichas:
                if l != letra:
                    confusiones[(letra, l)] += 1
        tabla[nombre] = fila
    negativas = {}
    for nombre, v in NEGATIVAS.items():
        fila = {}
        for letra in letras:
            manos, t, cam = secuencia_variante(gesto_crudo(datos, ventanas[letra]), fps, v)
            dichas = [l for _, l in pasar(nuevo_reconocedor(clasificador, plantillas, **kw), manos, t, cam)]
            fila[letra] = "+".join(dichas) or "-"
        negativas[nombre] = fila
    if detalle:
        print(f"  {'variante':20} " + " ".join(f"{l:>6}" for l in letras))
        for nombre, fila in tabla.items():
            print(f"  {nombre:20} " + " ".join(f"{fila[l]:>6}" for l in letras))
        for nombre, fila in negativas.items():
            print(f"  {nombre + ' (neg.)':20} " + " ".join(f"{fila[l]:>6}" for l in letras)
                  + "   <- lo que dice; para LL/RR no debería ser la letra con movimiento")
        print(f"  acierto exacto (dice solo la letra correcta): {bien}/{total} = {bien / total:.1%}; "
              f"confusiones: {dict(confusiones) or '-'}")
    return bien / total, tabla, negativas


def evaluar_quietas_con_temblor(datos, clasificador, plantillas, kw=None):
    """Letras quietas del video (parte central) con temblor o con un deslizamiento corto."""
    kw = kw or {}
    fps = datos["fps"]
    movimiento = set(ventanas_de())
    casos = {"tal cual": {}, "temblor 4 Hz 0.05 manos": {"temblor": 0.05},
             "temblor 4 Hz 0.10 manos": {"temblor": 0.10},
             "se corre 0.25 manos en 0.5 s": {"corrimiento": 0.25}}
    print(f"  {'caso':30} quietas dichas bien | letras con movimiento inventadas")
    resultado = {}
    for nombre, caso in casos.items():
        bien, inventadas = 0, Counter()
        tramos = [t for t in datos["tramos"] if not t["movimiento"]]
        for tramo in tramos:
            a, b = tramo["centro"]
            manos = [m for m in datos["cuadros"][a:b + 1]]
            manos = _sacudir(manos, fps, **caso)
            t = [i / fps for i in range(len(manos))]
            dichas = [l for _, l in pasar(nuevo_reconocedor(clasificador, plantillas, **kw), manos, t)]
            bien += tramo["letra"] in dichas
            for l in dichas:
                if l in movimiento:
                    inventadas[(tramo["letra"], l)] += 1
        resultado[nombre] = (bien, sum(inventadas.values()))
        print(f"  {nombre:30} {bien:2}/{len(tramos)}               | {sum(inventadas.values())} "
              f"{dict(inventadas) if inventadas else ''}")
    return resultado


def _sacudir(manos, fps, temblor=0.0, corrimiento=0.0):
    salida = []
    for i, m in enumerate(manos):
        if m is None:
            salida.append(None)
            continue
        p = _a_px(m)
        escala = np.linalg.norm(p[9] - p[0])
        t = i / fps
        dx = temblor * escala * np.sin(2 * np.pi * 4 * t)
        if corrimiento:
            dx += corrimiento * escala * float(np.clip((t - 0.6) / 0.5, 0, 1))
        p = p + np.array([dx, 0, 0])
        salida.append(_de_px(m, p))
    return salida


# ---------------------------------------------------------------- 3: flujo del video entero

def evaluar_flujo_combinado(datos, ventanas, clasificador, plantillas, kw=None, camara=None, paso=1):
    """El video entero por el Reconocedor combinado. paso=2 simula una cámara a 15 fps."""
    kw = kw or {}
    fps, tramos = datos["fps"], datos["tramos"]
    inicio = {t["letra"]: t["inicio"] / fps for t in tramos}
    demoras = {}
    rec = nuevo_reconocedor(clasificador, plantillas, **kw)
    letra_de, mov = {}, set()
    vecinas = {}
    for n, t in enumerate(tramos):
        vecinas[t["letra"]] = {tramos[m]["letra"] for m in (n - 1, n + 1) if 0 <= m < len(tramos)}
        for i in range(t["inicio"], t["fin"] + 1):
            letra_de[i] = t["letra"]
            if t["movimiento"]:
                mov.add(i)
    zonas = {l: (a - 0.5, b + 0.5) for l, (a, b) in ventanas.items()}
    vistas, mov_bien, mov_mal, inventadas, en_mov, en_borde = set(), set(), Counter(), Counter(), Counter(), 0
    dichas = []
    for i, mano in enumerate(datos["cuadros"]):
        if i % paso:
            continue
        ti = i / fps
        cuadro, vector = (None, None) if mano is None else armar(mano, ti, camara)
        for letra in rec.actualizar_cuadro(cuadro, vector, ti):
            dichas.append((ti, letra))
            real = letra_de.get(i)
            if letra == real and letra not in demoras:
                demoras[letra] = ti - inicio[letra]
            if letra in zonas:
                a, b = zonas[letra]
                if a <= ti <= b:
                    mov_bien.add(letra)
                else:
                    mov_mal[(real or "-", letra)] += 1
            elif letra == real:
                vistas.add(real)
            elif i in mov:
                en_mov[(real, letra)] += 1
            elif letra in vecinas.get(real, ()):
                en_borde += 1
            else:
                inventadas[(real or "-", letra)] += 1
    return {"quietas": len(vistas), "inventadas": sum(inventadas.values()), "vecinas": en_borde,
            "en_movimiento": sum(en_mov.values()), "mov_bien": sorted(mov_bien),
            "mov_mal": sum(mov_mal.values()),
            "detalle": {"inventadas": dict(inventadas), "en_movimiento": dict(en_mov), "mov_mal": dict(mov_mal)},
            "dichas": dichas, "demoras": demoras, "bases": rec._todas_bases}


def evaluar_flujos(datos, ventanas, clasificadores, plantillas, kw=None):
    print(f"  {'quietas':18} {'motor':13} quietas inventadas vecina quieta-en-tramo-mov | movimiento bien / inventadas"
          " | demora mediana (bases)")
    for nombre, clf in clasificadores.items():
        p = {"umbral": Aceptador().umbral, "margen": Aceptador().margen,
             "segundos": Aceptador().segundos, "frames_minimos": Aceptador().frames_minimos}
        antes = evaluar_flujo(clf, datos["cuadros"], datos["tramos"], datos["fps"], None, p)
        print(f"  {nombre:18} {'antes':13} {antes['bien']:4}/25 {antes['inventadas']:6} {antes['vecinas']:6} "
              f"{antes['en_movimiento']:10}          | (no reconocía movimiento) | {antes['demora']:.2f}s")
        for etiqueta, cam, paso in (("después", None, 1), ("después 4:3", (640, 480), 1), ("después 15fps", None, 2)):
            r = evaluar_flujo_combinado(datos, ventanas, clf, plantillas, kw, cam, paso)
            dem = r["demoras"]
            bases = [v for l, v in dem.items() if l in r["bases"]]
            print(f"  {nombre:18} {etiqueta:13} {r['quietas']:4}/25 {r['inventadas']:6} {r['vecinas']:6} "
                  f"{r['en_movimiento']:10}          | {len(r['mov_bien'])}/5 {','.join(r['mov_bien']):14} / {r['mov_mal']}"
                  f"         | {np.median(list(dem.values())):.2f}s ({np.median(bases) if bases else float('nan'):.2f}s)")
            if paso == 1 and cam is None:
                det = {k: v for k, v in r["detalle"].items() if v}
                if det:
                    print(f"      detalle: {det}")
                if nombre.startswith("app"):
                    print("      lo que dice: " + " ".join(l for _, l in r["dichas"]))


def evaluar_transiciones(datos, ventanas, plantillas, kw=None):
    """Los gestos del video que NO son letras con movimiento (la mano que se acomoda entre letras)."""
    kw = kw or {}
    mov = ReconocedorMovimiento.desde_plantillas(plantillas, **kw)
    zonas = list(ventanas.values())
    gestos = gestos_del_video(datos)
    ajenos = [g for g in gestos if not any(g[0].t <= b + 0.5 and g[-1].t >= a - 0.5 for a, b in zonas)]
    tops = [(g, mov.mejores(g, 1)) for g in ajenos]
    aceptados = [g for g in ajenos if mov.clasificar(g)[0] is not None]
    peor = max(tops, key=lambda p: p[1][0][1] if p[1] else 0)
    print(f"  {len(gestos)} gestos en el video: {len(gestos) - len(ajenos)} son las letras con movimiento, "
          f"{len(ajenos)} son transiciones entre letras quietas.")
    print(f"  transiciones aceptadas como letra con movimiento: {len(aceptados)}; la más parecida: "
          f"{peor[1][0][0]} {peor[1][0][1]:.3f} en {peor[0][0].t:.1f}s (umbral {mov.umbral})")
    durs = [g[-1].t - g[0].t for g in ajenos]
    print(f"  duración de las transiciones: mediana {np.median(durs):.2f}s, máx {max(durs):.2f}s")


# ---------------------------------------------------------------- 4: barrido de pesos

def gestos_del_video(datos):
    """Todos los gestos que el Segmentador encuentra en el video entero (como en vivo)."""
    from core.movimiento import segmentar
    fps = datos["fps"]
    cuadros = [None if m is None else armar(m, i / fps)[0] for i, m in enumerate(datos["cuadros"])]
    return segmentar(cuadros, [i / fps for i in range(len(cuadros))])


def barrido(datos, ventanas, plantillas):
    fps = datos["fps"]
    zonas = {l: (a - 0.5, b + 0.5) for l, (a, b) in ventanas.items()}
    gestos = gestos_del_video(datos)
    ajenos = [g for g in gestos if not any(g[0].t <= b and g[-1].t >= a for a, b in zonas.values())]
    variantes = []
    for letra in sorted(ventanas):
        for v in VARIANTES.values():
            manos, t, cam = secuencia_variante(gesto_crudo(datos, ventanas[letra]), fps, v)
            cuadros = [None if m is None else armar(m, ti, cam)[0] for m, ti in zip(manos, t)]
            from core.movimiento import segmentar
            gs = segmentar(cuadros, t)
            if gs:
                variantes.append((letra, max(gs, key=lambda g: g[-1].t - g[0].t)))
    print(f"  {len(variantes)} variantes, {len(ajenos)} gestos del video que no son letras con movimiento")
    print(f"  {'forma':>5} {'orient':>6} {'tray':>5} | peor conf. propia | mejor ajena (2.ª letra) | mejor gesto ajeno | separación")
    filas = []
    for pf, po, pt in itertools.product((0.5, 1.0), (0.25, 0.5, 1.0), (1.0, 2.0, 3.0)):
        mov = ReconocedorMovimiento.desde_plantillas(plantillas, pesos=(pf, po, pt))
        propia, otra = [], []
        for letra, g in variantes:
            top = dict(mov.mejores(g, 5))
            propia.append(top.get(letra, 0.0))
            otra.append(max(c for l, c in top.items() if l != letra))
        ajena = [mov.mejores(g, 1)[0][1] for g in ajenos if mov.mejores(g, 1)]
        sep = min(np.percentile(propia, 5) - max(ajena), min(np.array(propia) - np.array(otra)))
        filas.append((sep, pf, po, pt, min(propia), np.percentile(propia, 5), max(otra), max(ajena)))
    for sep, pf, po, pt, pmin, p5, o, a in sorted(filas, reverse=True)[:10]:
        print(f"  {pf:5} {po:6} {pt:5} | {pmin:.3f} (p5 {p5:.3f})  | {o:.3f}                  | {a:.3f}             | {sep:+.3f}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--signs", type=Path, default=RUTA_SENAS)
    parser.add_argument("--movimientos", type=Path, default=RUTA_MOVIMIENTOS)
    parser.add_argument("--barrido", action="store_true", help="probar pesos del descriptor")
    args = parser.parse_args(argv)

    datos = cargar_extraido()
    ventanas = ventanas_de(args.movimientos, datos["video"])
    plantillas = plantillas_de(args.movimientos)
    print(f"Plantillas: " + ", ".join(f"{l} {a:.2f}-{b:.2f}s" for l, (a, b) in sorted(ventanas.items())) + "\n")
    if args.barrido:
        barrido(datos, ventanas, plantillas)
        return 0
    clasificadores = clasificadores_quietas(args.signs)
    rec = nuevo_reconocedor(clasificadores["app (signs.json)"], plantillas)
    print("Bases (postura inicial leída como letra quieta): "
          + ", ".join(f"{l}<-{'/'.join(sorted(b))}" for l, b in sorted(rec.bases.items())) + "\n")
    print("== 1. variantes de cada gesto (quietas: signs.json como la app)")
    evaluar_variantes(datos, ventanas, clasificadores["app (signs.json)"], plantillas)
    print("\n== 2. letras quietas con temblor o corrimiento (quietas: signs.json)")
    evaluar_quietas_con_temblor(datos, clasificadores["app (signs.json)"], plantillas)
    print("\n== 3. transiciones normales entre letras")
    evaluar_transiciones(datos, ventanas, plantillas)
    print("\n== 4. flujo del video entero (antes = solo Aceptador; después = Reconocedor combinado)")
    evaluar_flujos(datos, ventanas, clasificadores, plantillas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
