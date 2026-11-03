"""Tomas sintéticas: variantes de las tomas OFICIALES en el espacio de los 21 puntos 3D.

No se renderiza nada ni se usa azar: cada toma oficial se transforma con una
lista FIJA de variantes (VARIANTES) y se vuelve a normalizar como landmarks.py.
El resultado es siempre el mismo, así que se guarda en signs.json y la app
móvil no tiene que generarlas: las lee como cualquier otra toma.

Reglas:
  - Salen SOLO de tomas oficiales (imagen:/video:), nunca de webcam:, para no
    multiplicar una seña mal hecha. Cada categoría (letra / número) por separado.
  - Llevan source "sintetica:<variante>|<source de origen>#<n de toma>" y nunca
    cuentan como oficiales (core/referencia.py): el grabador no las usa.
  - Se descartan si dejan de parecerse a su seña: contra las oficiales de su
    categoría tienen que quedar primeras, con confianza >= UMBRAL y por lo menos
    MARGEN_FILTRO sobre la segunda seña (filtrar()).
  - Se regeneran con scripts/generar_sinteticas.py (los importadores lo hacen
    solos). Un test verifica que las de signs.json estén al día.

Tipos de variante (puntos en el marco de la mano normalizada: muñeca en el
origen, muñeca -> nudillo del medio = 1):
  - "flexion" (articulaciones, grados): dobla (+) o estira (-) esas articulaciones
    de los 4 dedos (no el pulgar). Solo toca articulaciones que ya están dobladas
    más de FLEXION_MINIMA (un dedo recto queda recto), nunca las estira más allá
    de rectas ni las dobla más de FLEXION_MAXIMA. Gira la parte del dedo que
    sigue a la articulación alrededor del eje a x b (a = hueso que llega, b =
    hueso que sale), con la fórmula de Rodrigues.
  - "dedos" f / "pulgar" f: largo de los 4 dedos / del pulgar x f.
  - "palma" f: ancho de la palma x f (nudillos 5, 13 y 17 respecto del 9).
  - "giro" (yaw, pitch, roll): giro 3D de toda la mano alrededor de la muñeca.

Medido con scripts/evaluar_motor.py (sesión 2026-11-02): solo quedó la flexión de
los nudillos (MCP) +10° y -5°. Largo de dedos/pulgar/palma bajaban la validación
cruzada imagen<->video; flexión de PIP/DIP subía las aceptadas MAL; los giros
solo mejoraban los giros simulados y bajaban las aceptadas en el video real
(con core/rasgos.py el giro solo mueve los 2 rasgos de orientación). MCP -10°
acercaba V a U. Esos tipos quedan implementados para volver a medirlos cuando
haya tomas de más personas. No hay variante de proporción de cámara: desde la
version 3 (landmarks.py) la misma mano da el mismo vector en 4:3, 16:9 o vertical.

Se guardan en signs.json (no se generan al cargar): son ~190 tomas (+~320 KB,
el archivo queda en ~0.6 MB) y la app móvil solo tiene que leerlas, sin
reimplementar esta geometría ni depender de que Dart redondee igual que numpy.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np

from core.landmarks import MIDDLE_FINGER_MCP, NUM_LANDMARKS, VECTOR_SIZE, WRIST
from core.rasgos import marco_palma, rasgos

PREFIJO = "sintetica:"
DECIMALES = 6

# Cadenas de los 4 dedos (nudillo, falange, falange, punta) y del pulgar.
DEDOS_LARGOS = ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))
PULGAR = (1, 2, 3, 4)
# Articulaciones: índice dentro de la cadena (wrist, nudillo, f1, f2, punta).
MCP, PIP, DIP = 1, 2, 3

TIPOS = ("flexion", "dedos", "pulgar", "palma", "giro")
FLEXION_MINIMA = 10.0   # grados: por debajo, la articulación se considera recta
FLEXION_MAXIMA = 170.0  # grados: una articulación nunca se dobla más que esto

# Lista fija de variantes, en este orden (una sintética por variante y toma oficial).
VARIANTES: tuple = (
    ("flexion", (MCP,), 10.0),
    ("flexion", (MCP,), -5.0),
)
# Margen exigido a cada sintética contra las oficiales. Más estricto que el del
# Aceptador (0.10): una sintética tiene que ser claramente su seña.
MARGEN_FILTRO = 0.25


# ---------------------------------------------------------------- geometría

def rotacion(yaw: float, pitch: float, roll: float) -> np.ndarray:
    """Matriz 3x3: primero yaw (eje y), después pitch (eje x), al final roll (eje z). Grados."""
    y, p, r = (math.radians(a) for a in (yaw, pitch, roll))
    ry = np.array([[math.cos(y), 0.0, math.sin(y)], [0.0, 1.0, 0.0], [-math.sin(y), 0.0, math.cos(y)]])
    rp = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(p), -math.sin(p)], [0.0, math.sin(p), math.cos(p)]])
    rr = np.array([[math.cos(r), -math.sin(r), 0.0], [math.sin(r), math.cos(r), 0.0], [0.0, 0.0, 1.0]])
    return rr @ rp @ ry


def _girar_eje(v: np.ndarray, eje: np.ndarray, grados: float) -> np.ndarray:
    """Rodrigues: gira las filas de v alrededor del eje unitario."""
    a = math.radians(grados)
    c, s = math.cos(a), math.sin(a)
    return v * c + np.cross(eje, v) * s + np.outer(v @ eje, eje) * (1.0 - c)


def renormalizar(pts: np.ndarray) -> Optional[np.ndarray]:
    """Muñeca al origen y muñeca -> nudillo del medio = 1 (como landmarks.normalizar_puntos, en float64)."""
    pts = pts - pts[WRIST]
    escala = float(np.linalg.norm(pts[MIDDLE_FINGER_MCP]))
    if escala < 1e-6:
        return None
    return pts / escala


def _alargar(pts: np.ndarray, cadena: Sequence[int], f: float) -> np.ndarray:
    """Multiplica por f cada hueso de la cadena desde su primer punto (que queda fijo)."""
    nuevo = pts.copy()
    for i in range(1, len(cadena)):
        nuevo[cadena[i]] = nuevo[cadena[i - 1]] + (pts[cadena[i]] - pts[cadena[i - 1]]) * f
    return nuevo


def _palma(pts: np.ndarray, f: float) -> Optional[np.ndarray]:
    base = marco_palma(pts)
    if base is None:
        return None
    lateral = base[0]
    nuevo = pts.copy()
    for cadena in DEDOS_LARGOS:
        if cadena[0] == MIDDLE_FINGER_MCP:
            continue
        corrimiento = lateral * (float((pts[cadena[0]] - pts[MIDDLE_FINGER_MCP]) @ lateral) * (f - 1.0))
        nuevo[list(cadena)] += corrimiento
    return nuevo


def _flexionar(pts: np.ndarray, articulaciones: Sequence[int], grados: float) -> np.ndarray:
    nuevo = pts.copy()
    for cadena in DEDOS_LARGOS:
        dedo = (WRIST,) + cadena
        for j in articulaciones:
            a = nuevo[dedo[j]] - nuevo[dedo[j - 1]]
            b = nuevo[dedo[j + 1]] - nuevo[dedo[j]]
            eje = np.cross(a, b)
            na, nb, ne = np.linalg.norm(a), np.linalg.norm(b), np.linalg.norm(eje)
            if na < 1e-9 or nb < 1e-9 or ne < 1e-9:
                continue
            angulo = math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b) / (na * nb)))))
            if angulo < FLEXION_MINIMA:
                continue
            giro = max(min(grados, FLEXION_MAXIMA - angulo), -angulo)   # ni más allá de recto ni de FLEXION_MAXIMA
            distales = list(dedo[j + 1:])
            centro = nuevo[dedo[j]]
            nuevo[distales] = centro + _girar_eje(nuevo[distales] - centro, eje / ne, giro)
    return nuevo


def aplicar(vector, variante) -> Optional[np.ndarray]:
    """Vector de 63 (float64) de la variante, o None si la mano queda degenerada."""
    tipo = variante[0]
    if tipo not in TIPOS:
        raise ValueError(f"variante desconocida: {variante!r}")
    v = np.asarray(vector, dtype=np.float64).reshape(-1)
    if v.shape[0] != VECTOR_SIZE or not np.all(np.isfinite(v)):
        return None
    pts = renormalizar(v.reshape(NUM_LANDMARKS, 3))
    if pts is None:
        return None
    if tipo == "dedos":
        for cadena in DEDOS_LARGOS:
            pts = _alargar(pts, cadena, variante[1])
    elif tipo == "pulgar":
        pts = _alargar(pts, PULGAR, variante[1])
    elif tipo == "palma":
        pts = _palma(pts, variante[1])
    elif tipo == "flexion":
        pts = _flexionar(pts, variante[1], variante[2])
    else:  # "giro"
        pts = pts @ rotacion(*variante[1]).T
    if pts is None:
        return None
    pts = renormalizar(pts)
    return None if pts is None else pts.reshape(-1)


def nombre(variante) -> str:
    """Texto corto de la variante, para el source: "dedos=0.9", "flexion=PIP+DIP:+10", "giro=20,0,0"."""
    tipo = variante[0]
    if tipo == "flexion":
        arts = "+".join({MCP: "MCP", PIP: "PIP", DIP: "DIP"}[j] for j in variante[1])
        return f"flexion={arts}:{variante[2]:+g}"
    if tipo == "giro":
        return "giro=" + ",".join(f"{a:g}" for a in variante[1])
    return f"{tipo}={variante[1]:g}"


# ---------------------------------------------------------------- generar y filtrar

def es_sintetica(toma: dict) -> bool:
    return str(toma.get("source", "")).startswith(PREFIJO)


def generar(etiquetas: Sequence[str], vectores, variantes=None, umbral: Optional[float] = None,
            margen: Optional[float] = None):
    """Sintéticas de las tomas dadas, que tienen que ser OFICIALES y de UNA categoría.

    Devuelve (etiquetas, vectores (n, 63), origen) solo de las que pasan filtrar():
    origen[i] = (índice de la toma de origen, variante).
    """
    from core.clasificador import UMBRAL

    variantes = VARIANTES if variantes is None else tuple(variantes)
    umbral = UMBRAL if umbral is None else umbral
    margen = MARGEN_FILTRO if margen is None else margen
    etiquetas = list(etiquetas)
    vectores = np.asarray(vectores, dtype=np.float64).reshape(-1, VECTOR_SIZE)

    cand_et, cand_vec, origen = [], [], []
    for n, (etiqueta, vec) in enumerate(zip(etiquetas, vectores)):
        for variante in variantes:
            nuevo = aplicar(vec, variante)
            if nuevo is not None:
                cand_et.append(etiqueta)
                cand_vec.append(nuevo)
                origen.append((n, variante))
    if not cand_vec:
        return [], np.empty((0, VECTOR_SIZE)), []
    cand_vec = np.vstack(cand_vec)
    ok = filtrar(etiquetas, vectores, cand_et, cand_vec, umbral, margen)
    return ([e for e, b in zip(cand_et, ok) if b], cand_vec[ok], [o for o, b in zip(origen, ok) if b])


def filtrar(etiquetas_of, vectores_of, etiquetas, vectores, umbral: float, margen: float) -> np.ndarray:
    """Máscara: la sintética se queda si, contra las oficiales, su etiqueta es la primera,
    con confianza >= umbral y por lo menos `margen` sobre la segunda etiqueta.

    Con una sola etiqueta oficial solo se pide el umbral.
    """
    from core.clasificador import confianza

    ref_et, ref = [], []
    for etiqueta, vec in zip(etiquetas_of, vectores_of):
        r = rasgos(vec)
        if r is not None:
            ref_et.append(etiqueta)
            ref.append(r)
    ok = np.zeros(len(etiquetas), dtype=bool)
    if not ref:
        return ok
    ref = np.vstack(ref)
    nombres = sorted(set(ref_et))
    columna = np.array([nombres.index(e) for e in ref_et])

    for n, (etiqueta, vec) in enumerate(zip(etiquetas, vectores)):
        r = rasgos(vec)
        if r is None or etiqueta not in nombres:
            continue
        mejor = np.zeros(len(nombres))
        np.maximum.at(mejor, columna, confianza(np.linalg.norm(ref - r, axis=1)))
        k = nombres.index(etiqueta)
        segunda = float(np.delete(mejor, k).max()) if len(nombres) > 1 else 0.0
        ok[n] = mejor[k] >= umbral and mejor[k] - segunda >= margen
    return ok


def regenerar(datos: dict, variantes=None) -> dict:
    """signs.json (dict) con las sintéticas recalculadas desde las oficiales actuales.

    Borra todas las tomas "sintetica:" y vuelve a crearlas, por categoría. No
    modifica `datos`. Es determinista: con las mismas oficiales da lo mismo.
    """
    import copy

    from core.clasificador import categoria_de, tomas_de
    from core.referencia import es_oficial

    nuevo = copy.deepcopy(datos)
    for entrada in nuevo["signs"].values():
        entrada["takes"] = [t for t in tomas_de(entrada) if not es_sintetica(t)]
        entrada.pop("vector", None)

    por_categoria: dict[str, list] = {}
    for etiqueta, entrada in nuevo["signs"].items():
        for n, toma in enumerate(entrada["takes"]):
            vec = np.asarray(toma.get("vector", []), dtype=np.float64).reshape(-1)
            if es_oficial(toma) and vec.shape[0] == VECTOR_SIZE and np.all(np.isfinite(vec)) and vec.any():
                por_categoria.setdefault(categoria_de(entrada), []).append((etiqueta, n, toma))

    for origenes in por_categoria.values():
        etiquetas = [o[0] for o in origenes]
        vectores = [o[2]["vector"] for o in origenes]
        sin_et, sin_vec, sin_origen = generar(etiquetas, vectores, variantes)
        for etiqueta, vec, (i, variante) in zip(sin_et, sin_vec, sin_origen):
            _, n, toma = origenes[i]
            sintetica = {
                "vector": [round(float(x), DECIMALES) for x in vec],
                "samples": toma.get("samples", 1),
                "recorded_at": toma.get("recorded_at"),
                "source": f"{PREFIJO}{nombre(variante)}|{toma.get('source', '?')}#{n}",
            }
            if "frame" in toma:
                sintetica["frame"] = list(toma["frame"])
            nuevo["signs"][etiqueta]["takes"].append(sintetica)
    return nuevo
