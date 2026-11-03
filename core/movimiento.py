"""Letras con movimiento (J, LL, Ñ, RR, Z): segmentar el gesto y compararlo con DTW.

Las letras quietas se comparan cuadro a cuadro (core/clasificador.py). Las que
tienen movimiento se reconocen como un GESTO entero (sin modelos entrenados):

  1. Por cada cuadro con mano se arma un `Cuadro`: el vector de 63 de
     landmarks.py (forma, ya espejada si es la izquierda), la muñeca en píxeles
     del frame y la escala de la mano en píxeles (|punto 9 - punto 0| en 3D), los
     dos con la corrección de proporción x*ancho, y*alto, z*ancho. Una mano con
     algún punto fuera de la imagen (x o y fuera de [0, 1]) no cuenta: MediaPipe
     inventa esos puntos.
  2. `Segmentador` mide la velocidad de la mano en "manos por segundo": cuánto se
     mueven los 21 puntos SUAVIZADOS (promedio de los últimos SUAVIZADO s, saca
     el temblor) entre ahora y hace DT_VELOCIDAD s, dividido por la escala. Así
     no depende de la distancia a la cámara ni de los fps. Un gesto arranca cuando
     la velocidad pasa V_INICIO, se confirma cuando la mano se alejó D_INICIO
     manos de donde estaba (si no, en T_CONFIRMAR s se descarta: temblor) y
     termina cuando la velocidad queda bajo V_FIN durante SEGUNDOS_QUIETO.
  3. `descriptor()` pasa el gesto a MUESTRAS puntos parejos en el tiempo
     (interpolación lineal: da igual 15 o 30 fps, o hacerlo lento o rápido) y en
     cada uno junta:
       - forma: los 31 rasgos de core/rasgos.py                     x PESO_FORMA
       - orientación: ejes "y" (muñeca -> nudillos) y "z" (normal de la
         palma) del marco de la palma (rasgos.marco_palma), 6 valores x PESO_ORIENTACION
       - trayectoria: centro de la palma (promedio de los puntos 0, 5, 9, 13,
         17 en píxeles) menos el del primer cuadro, dividido por la escala
         mediana del gesto; x negada si la mayoría de los cuadros es "Left" x PESO_TRAYECTORIA
     La trayectoria NO se normaliza por gesto: un temblor de 0.1 manos no se
     parece a un deslizamiento de 0.7 manos.
  4. `dtw()` (DTW clásico, banda de Sakoe-Chiba, pasos simétricos: diagonal x2,
     dividido por n + m) compara el gesto con cada plantilla de
     data/reference/movimientos.json. Antes, `movimiento_comparable()` exige que
     el gesto se mueva parecido a la plantilla (alcance y recorrido, ver
     ALCANCE_*). También se prueba el gesto sin su primer 15 % y 30 %
     (RECORTES_INICIO). confianza = 1 - distancia / DISTANCIA_MAX; se acepta la
     mejor letra si pasa UMBRAL y le saca MARGEN a la segunda. Si no, "nada":
     nunca inventa.

Todo es numpy simple (promedios, interpolación lineal, normas, DTW con dos
bucles) para poder reimplementarlo igual en Dart. Constantes medidas con
scripts/evaluar_movimiento.py. La convivencia con las letras quietas está en
core/reconocedor.py.

Formato de movimientos.json (CAMBIO DE CONTRATO: la app móvil lo tiene que leer):

    {"version": 1,                 # VERSION_MOVIMIENTOS (formato de este archivo)
     "version_vector": 3,          # VERSION_VECTOR de landmarks.py
     "signs": {"J": {"categoria": "letra", "tipo": "movimiento", "takes": [
        {"source": "video:abecedario-lesco.mp4",   # o "webcam:<persona>"
         "recorded_at": "2026-11-03T...", "fps": 29.97, "frame": [612, 720],
         "inicio": 41.61, "fin": 43.08,          # opcional: segundos en el video
         "cuadros": [{"t": 0.0,                  # segundos desde el primer cuadro
                      "lado": "Left",           # como lo da MediaPipe
                      "muneca": [x, y],          # píxeles del frame (x*ancho, y*alto)
                      "escala": 191.6,           # píxeles, |punto 9 - punto 0| en 3D
                      "vector": [63 valores]}, ...]}]}}}

Solo están los cuadros con mano (el tiempo "t" muestra los huecos). Los 21 puntos
en píxeles se recuperan como muneca + escala * vector[:, :2] (x negada si "Left").
"""
from __future__ import annotations

import json
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from core.landmarks import (MIDDLE_FINGER_MCP, NUM_LANDMARKS, VECTOR_SIZE, VERSION_VECTOR, WRIST, corregir_proporcion,
                            normalizar_puntos)
from core.rasgos import marco_palma, rasgos

RAIZ = Path(__file__).resolve().parent.parent
RUTA_MOVIMIENTOS = RAIZ / "data" / "reference" / "movimientos.json"
VERSION_MOVIMIENTOS = 1
TIPO = "movimiento"
DECIMALES = 5

PALMA = (0, 5, 9, 13, 17)

# --- Segmentación (velocidades en manos por segundo, tiempos en segundos) ---
SUAVIZADO = 0.2           # promedio de los puntos de los últimos 0.2 s (saca el temblor)
DT_VELOCIDAD = 0.1        # velocidad entre el promedio de ahora y el de hace >= 0.1 s
V_INICIO = 0.6            # quietas del video (suavizado): mediana 0.07, p99 0.47; gestos: picos 1.5-7
V_FIN = 0.35
SEGUNDOS_QUIETO = 0.25    # tanto tiempo bajo V_FIN = terminó el gesto (Ñ baja ~0.1 s en cada vaivén)
SEGUNDOS_PREVIOS = 0.05   # el gesto arranca un poco antes del primer cuadro rápido
D_INICIO = 0.15           # el gesto se confirma cuando la mano (suavizada) se alejó 0.15 manos de donde estaba
T_CONFIRMAR = 0.6         # si en ese tiempo no se alejó, era temblor: se descarta
DURACION_MIN = 0.25
DURACION_MAX = 4.0        # más largo = la mano anda dando vueltas: se descarta
HUECO_MAX = 0.3           # sin mano más tiempo que esto corta el gesto

# --- Descriptor y comparación ---
MUESTRAS = 20
PESO_FORMA = 1.0
PESO_ORIENTACION = 0.5
PESO_TRAYECTORIA = 2.0
BANDA = 0.3               # fracción del largo que el DTW puede correrse
DISTANCIA_MAX = 2.0
UMBRAL = 0.5
MARGEN = 0.1
# Cuánto se mueve el gesto comparado con la plantilla, en trayectoria y en giro
# de la palma por separado (ver cantidad_de_movimiento()):
#   - alcance (lo más lejos que llega de su primer punto) >= ALCANCE_MIN x el de la
#     plantilla, si la plantilla llega a MOVIMIENTO_PLANTILLA o más: una L con
#     temblor no es una LL;
#   - alcance <= max(ALCANCE_MAX x el de la plantilla, el de la plantilla + ALCANCE_MAS):
#     una mano que gira mucho no es una RR (que no gira);
#   - recorrido total (suma de los pasos) >= RECORRIDO_MIN x el de la plantilla:
#     un solo giro no es una Ñ (que va y viene ~4 veces).
ALCANCE_MIN = 0.5
ALCANCE_MAX = 3.0
ALCANCE_MAS = 0.5
RECORRIDO_MIN = 0.4
MOVIMIENTO_PLANTILLA = 0.3
# El gesto también se compara sin su comienzo (la mano todavía estaba armando la
# forma al empezar a moverse, como en la Z del video) y se queda la mejor.
RECORTES_INICIO = (0.0, 0.15, 0.3)
COLUMNAS_ORIENTACION = slice(31, 37)
COLUMNAS_TRAYECTORIA = slice(37, 39)


class VersionIncompatible(ValueError):
    """movimientos.json es de otro formato o de otra versión del vector."""


@dataclass
class Cuadro:
    t: float                 # segundos (reloj monótono o desde el inicio de la toma)
    vector: np.ndarray       # (63,) normalizado como landmarks.py (izquierda espejada)
    muneca: np.ndarray       # (2,) píxeles del frame
    escala: float            # píxeles
    lado: str                # "Left" | "Right"
    _forma: Optional[tuple] = field(default=None, repr=False, compare=False)

    def forma(self) -> tuple:
        """(31 rasgos, marco de la palma 3x3) o (None, None); se calcula una vez por cuadro."""
        if self._forma is None:
            pts = self.vector.reshape(NUM_LANDMARKS, 3)
            self._forma = (rasgos(self.vector), marco_palma(pts - pts[WRIST]))
        return self._forma

    def puntos_px(self) -> np.ndarray:
        """(21, 2) en píxeles del frame, reconstruidos desde muñeca + escala x vector."""
        v = self.vector.reshape(NUM_LANDMARKS, 3)[:, :2].copy()
        if self.lado.strip().lower() == "left":
            v[:, 0] = -v[:, 0]        # el vector está espejado: se deshace para volver a la imagen
        return self.muneca + self.escala * v


def cuadro_de_mano(mano, t: float) -> Optional[Cuadro]:
    """Cuadro desde un `core.camara.Mano` (None si la mano no sirve)."""
    if mano is None or mano.vector is None:
        return None
    return cuadro_de_puntos(mano.puntos, mano.lado, mano.frame, t, mano.vector)


def cuadro_de_puntos(puntos, lado: str, frame, t: float, vector=None) -> Optional[Cuadro]:
    """Cuadro desde los 21 landmarks de MediaPipe (x/ancho, y/alto, z) y el tamaño del frame."""
    try:
        crudos = np.array([[q.x, q.y] for q in puntos] if hasattr(puntos[0], "x")
                          else [q[:2] for q in puntos], dtype=np.float64)
        if crudos.min() < 0.0 or crudos.max() > 1.0:
            return None     # mano cortada por el borde: MediaPipe inventa los puntos de afuera
        pts = corregir_proporcion(puntos, frame)
        if vector is None:
            vector = normalizar_puntos(pts, lado)
    except ValueError:
        return None
    escala = float(np.linalg.norm(pts[MIDDLE_FINGER_MCP] - pts[WRIST]))
    if escala <= 1e-6:
        return None
    return Cuadro(float(t), np.asarray(vector, dtype=np.float64).reshape(-1), pts[WRIST, :2].copy(), escala, lado)


# ---------------------------------------------------------------- velocidad y segmentación

def velocidad(antes: Cuadro, ahora: Cuadro) -> float:
    """Cuánto se movieron los 21 puntos en la imagen entre dos cuadros, en manos por segundo."""
    dt = ahora.t - antes.t
    if dt <= 0:
        return 0.0
    desplazamiento = np.linalg.norm(ahora.puntos_px() - antes.puntos_px(), axis=1).mean()
    return float(desplazamiento / ((antes.escala + ahora.escala) / 2) / dt)


class Segmentador:
    """Corta el flujo de cuadros en gestos (inicio y fin del movimiento).

    actualizar(cuadro, t) en cada frame (cuadro None = sin mano). Devuelve la
    lista de cuadros del gesto cuando termina, o None. `moviendo` dice si ahora
    mismo hay un gesto en curso (para que las letras quietas esperen).

    La velocidad se mide sobre los puntos SUAVIZADOS (promedio de los cuadros de
    los últimos SUAVIZADO segundos): un temblor de 4-12 Hz casi desaparece y un
    gesto (1-3 Hz) queda. Es la velocidad entre el promedio de ahora y el de hace
    DT_VELOCIDAD segundos, dividida por la escala de la mano.
    """

    def __init__(self, v_inicio=V_INICIO, v_fin=V_FIN, quieto=SEGUNDOS_QUIETO, previos=SEGUNDOS_PREVIOS,
                 duracion_min=DURACION_MIN, duracion_max=DURACION_MAX, hueco_max=HUECO_MAX,
                 suavizado=SUAVIZADO):
        self.v_inicio, self.v_fin, self.quieto, self.previos = v_inicio, v_fin, quieto, previos
        self.duracion_min, self.duracion_max, self.hueco_max = duracion_min, duracion_max, hueco_max
        self.suavizado = suavizado
        self.reiniciar()

    def reiniciar(self) -> None:
        self._historia: deque = deque()   # (cuadro, puntos suavizados) recientes
        self._gesto: Optional[list] = None        # cuadros del gesto (candidato o confirmado)
        self._confirmado = False
        self._referencia = None                   # (puntos suavizados, escala) al arrancar el candidato
        self._lento_desde: Optional[float] = None
        self.velocidad = 0.0

    @property
    def moviendo(self) -> bool:
        """Hay un gesto confirmado en curso (la mano ya se alejó D_INICIO de donde estaba)."""
        return self._gesto is not None and self._confirmado

    @property
    def activo(self) -> bool:
        """Hay un candidato o un gesto en curso."""
        return self._gesto is not None

    def actualizar(self, cuadro: Optional[Cuadro], t: float) -> Optional[list]:
        if cuadro is None:
            if self._historia and t - self._historia[-1][0].t > self.hueco_max:
                return self._perdida()
            return None
        if self._historia and cuadro.t - self._historia[-1][0].t > self.hueco_max:
            gesto = self._perdida()            # se perdió la mano mucho rato: lo de antes no sigue
            self._agregar(cuadro)
            return gesto
        self._agregar(cuadro)
        suave = self._historia[-1][1]

        if self._gesto is None:
            if self.velocidad > self.v_inicio:
                # El promedio llega tarde: el gesto empieza un poco antes del cuadro rápido.
                desde = cuadro.t - (DT_VELOCIDAD + self.suavizado) / 2 - self.previos
                previos = [(c, s) for c, s in self._historia if c.t >= desde - 1e-9]
                self._gesto = [c for c, _ in previos]
                self._referencia = (previos[0][1], previos[0][0].escala)
                self._confirmado, self._lento_desde = False, None
            return None

        self._gesto.append(cuadro)
        cuadro.forma()                           # se calcula ahora y no todo junto al final
        if not self._confirmado:
            ref, escala = self._referencia
            if np.linalg.norm(suave - ref, axis=1).mean() / escala >= D_INICIO:
                self._confirmado = True
            elif cuadro.t - self._gesto[0].t > T_CONFIRMAR:
                self._gesto = None               # se sacude pero no va a ningún lado: temblor
                return None
        if self.velocidad >= self.v_fin:
            self._lento_desde = None
        elif self._lento_desde is None:
            self._lento_desde = cuadro.t
        if cuadro.t - self._gesto[0].t > self.duracion_max:
            self._gesto = None                   # demasiado largo: no es una letra
            return None
        if self._lento_desde is not None and cuadro.t - self._lento_desde >= self.quieto:
            if not self._confirmado:
                self._gesto, self._lento_desde = None, None
                return None
            return self._cerrar()
        return None

    def _agregar(self, cuadro: Cuadro) -> None:
        recientes = [c for c, _ in self._historia if cuadro.t - c.t < self.suavizado - 1e-9] + [cuadro]
        suave = np.mean([c.puntos_px() for c in recientes], axis=0)
        base = None
        for c, s in reversed(self._historia):
            if cuadro.t - c.t >= DT_VELOCIDAD - 1e-9:
                base = (c, s)
                break
        if base is None and self._historia:
            base = self._historia[0]
        if base is None:
            self.velocidad = 0.0
        else:
            dt = cuadro.t - base[0].t
            escala = (base[0].escala + cuadro.escala) / 2
            self.velocidad = float(np.linalg.norm(suave - base[1], axis=1).mean() / escala / dt) if dt > 0 else 0.0
        self._historia.append((cuadro, suave))
        guardar = DT_VELOCIDAD + self.suavizado + self.previos + 0.2
        while self._historia and cuadro.t - self._historia[0][0].t > guardar:
            self._historia.popleft()

    def _perdida(self) -> Optional[list]:
        gesto = self._cerrar() if self.moviendo else None
        self._gesto = None
        self._historia.clear()
        self.velocidad = 0.0
        return gesto

    def _cerrar(self) -> Optional[list]:
        gesto, self._gesto = self._gesto, None
        if not gesto:
            return None
        # Se corta en el primer cuadro lento después del último rápido.
        fin = self._lento_desde if self._lento_desde is not None else gesto[-1].t
        gesto = [c for c in gesto if c.t <= fin + 1e-9]
        self._lento_desde = None
        if len(gesto) < 3 or gesto[-1].t - gesto[0].t < self.duracion_min:
            return None
        return gesto


def segmentar(cuadros: Sequence[Optional[Cuadro]], tiempos: Sequence[float], **kw) -> list[list]:
    """Todos los gestos de una secuencia ya grabada (mismo Segmentador que en vivo)."""
    seg = Segmentador(**kw)
    gestos = []
    for c, t in zip(cuadros, tiempos):
        g = seg.actualizar(c, t)
        if g:
            gestos.append(g)
    if seg.moviendo:
        g = seg._cerrar()
        if g:
            gestos.append(g)
    return gestos


def recortar_gesto(cuadros: Sequence[Optional[Cuadro]], tiempos: Sequence[float]) -> Optional[list]:
    """El gesto más largo de una ventana (para sacar la plantilla de un video o de una grabación)."""
    gestos = segmentar(cuadros, tiempos)
    return max(gestos, key=lambda g: g[-1].t - g[0].t) if gestos else None


# ---------------------------------------------------------------- descriptor y DTW

def lado_mayoritario(cuadros: Sequence[Cuadro]) -> str:
    return Counter(c.lado.strip().lower() for c in cuadros).most_common(1)[0][0]


def descriptor(cuadros: Sequence[Cuadro], muestras: int = MUESTRAS, pesos=None) -> Optional[np.ndarray]:
    """(muestras, 31 + 6 + 2) del gesto, parejo en el tiempo. None si no alcanza."""
    pf, po, pt = pesos if pesos is not None else (PESO_FORMA, PESO_ORIENTACION, PESO_TRAYECTORIA)
    validos = []
    for c in cuadros:
        r, base = c.forma()
        if r is not None and base is not None:
            validos.append((c, r, base))
    if len(validos) < 2:
        return None
    espejo = -1.0 if lado_mayoritario([v[0] for v in validos]) == "left" else 1.0
    escala = float(np.median([v[0].escala for v in validos]))
    centros = np.array([v[0].puntos_px()[list(PALMA)].mean(axis=0) for v in validos])
    tray = (centros - centros[0]) / escala
    tray[:, 0] *= espejo
    filas = np.array([np.concatenate([r * pf, base[1] * po, base[2] * po, tr * pt])
                      for (c, r, base), tr in zip(validos, tray)])
    t = np.array([v[0].t for v in validos])
    if t[-1] - t[0] <= 0:
        return None
    grilla = np.linspace(t[0], t[-1], muestras)
    return np.stack([np.interp(grilla, t, filas[:, k]) for k in range(filas.shape[1])], axis=1)


def cantidad_de_movimiento(d: np.ndarray, pesos=None) -> np.ndarray:
    """[[alcance, recorrido] de la trayectoria, [alcance, recorrido] de la orientación], sin pesos.

    alcance = lo más lejos que llega del primer punto; recorrido = suma de los pasos.
    """
    _, po, pt = pesos if pesos is not None else (PESO_FORMA, PESO_ORIENTACION, PESO_TRAYECTORIA)
    salida = []
    for columnas, peso in ((COLUMNAS_TRAYECTORIA, pt), (COLUMNAS_ORIENTACION, po)):
        x = d[:, columnas] / peso
        salida.append([np.linalg.norm(x - x[0], axis=1).max(), np.linalg.norm(np.diff(x, axis=0), axis=1).sum()])
    return np.array(salida)


def movimiento_comparable(gesto: np.ndarray, plantilla: np.ndarray) -> bool:
    """El gesto se mueve parecido a la plantilla (ver ALCANCE_MIN, ALCANCE_MAX, RECORRIDO_MIN)."""
    for (alcance, recorrido), (alcance_p, recorrido_p) in zip(gesto, plantilla):
        if alcance > max(ALCANCE_MAX * alcance_p, alcance_p + ALCANCE_MAS):
            return False
        if alcance_p >= MOVIMIENTO_PLANTILLA and (alcance < ALCANCE_MIN * alcance_p
                                                  or recorrido < RECORRIDO_MIN * recorrido_p):
            return False
    return True


def dtw(a: np.ndarray, b: np.ndarray, banda: float = BANDA) -> float:
    """DTW con pasos simétricos (diagonal x2) dividido por n + m: costo medio por cuadro."""
    n, m = len(a), len(b)
    w = max(int(np.ceil(banda * max(n, m))), abs(n - m))
    costo = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(max(1, i - w), min(m, i + w) + 1):
            c = costo[i - 1, j - 1]
            D[i, j] = min(D[i - 1, j - 1] + 2 * c, D[i - 1, j] + c, D[i, j - 1] + c)
    return float(D[n, m] / (n + m))


def confianza(distancia):
    return np.clip(1.0 - np.asarray(distancia) / DISTANCIA_MAX, 0.0, 1.0)


# ---------------------------------------------------------------- archivo

def movimientos_vacio() -> dict:
    return {"version": VERSION_MOVIMIENTOS, "version_vector": VERSION_VECTOR, "signs": {}}


def leer_movimientos(ruta: Path | str = RUTA_MOVIMIENTOS) -> dict:
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Importá las letras con movimiento con scripts/importar_video.py")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict) or datos.get("version") != VERSION_MOVIMIENTOS:
        raise VersionIncompatible(f"{ruta}: se esperaba version {VERSION_MOVIMIENTOS}")
    if datos.get("version_vector") != VERSION_VECTOR:
        raise VersionIncompatible(f"{ruta}: vectores version {datos.get('version_vector')}, el motor usa {VERSION_VECTOR}")
    if not isinstance(datos.get("signs"), dict):
        raise ValueError(f"{ruta} no tiene la clave 'signs'")
    return datos


def escribir_movimientos(ruta: Path | str, datos: dict) -> None:
    ruta = Path(ruta)
    if datos.get("version") != VERSION_MOVIMIENTOS or datos.get("version_vector") != VERSION_VECTOR:
        raise VersionIncompatible("Solo se escribe el formato actual de movimientos.json")
    tmp = ruta.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(ruta)


def cuadro_a_json(c: Cuadro, t0: float = 0.0) -> dict:
    return {"t": round(c.t - t0, 4), "lado": c.lado, "muneca": [round(float(x), 2) for x in c.muneca],
            "escala": round(float(c.escala), 3), "vector": [round(float(x), DECIMALES) for x in c.vector]}


def cuadros_de_toma(toma: dict) -> list[Cuadro]:
    """Cuadros válidos de una toma de movimientos.json."""
    salida = []
    for c in toma.get("cuadros", []):
        if not c:
            continue
        v = np.asarray(c["vector"], dtype=np.float64).reshape(-1)
        if v.shape[0] != VECTOR_SIZE or not np.all(np.isfinite(v)) or float(c["escala"]) <= 0:
            continue
        salida.append(Cuadro(float(c["t"]), v, np.asarray(c["muneca"], dtype=np.float64), float(c["escala"]), c["lado"]))
    return salida


def toma_desde_cuadros(cuadros: Sequence[Cuadro], source: str, fps: float, frame, recorded_at: str, **extra) -> dict:
    t0 = cuadros[0].t
    toma = {"source": source, "recorded_at": recorded_at, "fps": round(float(fps), 3),
            "frame": [int(frame[0]), int(frame[1])]}
    toma.update(extra)
    toma["cuadros"] = [cuadro_a_json(c, t0) for c in cuadros]
    return toma


# ---------------------------------------------------------------- reconocedor

class ReconocedorMovimiento:
    """Compara un gesto con las plantillas de movimientos.json (precalculadas al cargar)."""

    def __init__(self, ruta: Path | str = RUTA_MOVIMIENTOS, umbral: float = UMBRAL, margen: float = MARGEN,
                 categoria: str = "letra"):
        datos = leer_movimientos(ruta)
        plantillas = []
        for etiqueta, entrada in datos["signs"].items():
            if entrada.get("categoria", "letra") != categoria:
                continue
            for toma in entrada.get("takes", []):
                plantillas.append((etiqueta, cuadros_de_toma(toma)))
        self._iniciar(plantillas, umbral, margen)

    @classmethod
    def desde_plantillas(cls, plantillas, umbral: float = UMBRAL, margen: float = MARGEN, pesos=None):
        """plantillas = [(etiqueta, [Cuadro, ...]), ...] en memoria (para evaluar)."""
        nuevo = cls.__new__(cls)
        nuevo._iniciar(plantillas, umbral, margen, pesos)
        return nuevo

    def _iniciar(self, plantillas, umbral, margen, pesos=None):
        self.umbral, self.margen, self.pesos = umbral, margen, pesos
        self._plantillas = []
        for etiqueta, cuadros in plantillas:
            d = descriptor(cuadros, pesos=pesos)
            if d is not None:
                self._plantillas.append((etiqueta, d, cantidad_de_movimiento(d, pesos)))
        if not self._plantillas:
            raise ValueError("No hay plantillas de movimiento válidas")
        self.etiquetas = sorted({e for e, _, _ in self._plantillas})

    def mejores(self, gesto: Sequence[Cuadro], k: int = 2) -> list[tuple[str, float]]:
        """[(letra, confianza), ...] de mayor a menor (la mejor plantilla y el mejor recorte de cada letra).

        Una plantilla cuyo movimiento no es comparable con el del gesto da 0.
        """
        mejor: dict[str, float] = {}
        n = len(gesto)
        for recorte in RECORTES_INICIO:
            d = descriptor(gesto[int(recorte * n):], pesos=self.pesos)
            if d is None:
                continue
            cantidad = cantidad_de_movimiento(d, self.pesos)
            for etiqueta, plantilla, cantidad_p in self._plantillas:
                conf = float(confianza(dtw(d, plantilla))) if movimiento_comparable(cantidad, cantidad_p) else 0.0
                mejor[etiqueta] = max(conf, mejor.get(etiqueta, 0.0))
        return sorted(mejor.items(), key=lambda p: p[1], reverse=True)[:k]

    def clasificar(self, gesto: Sequence[Cuadro]) -> tuple[Optional[str], float]:
        """(letra, confianza); letra None si no pasa umbral y margen: nunca inventa."""
        top = self.mejores(gesto, 2)
        if not top:
            return None, 0.0
        letra, conf = top[0]
        segunda = top[1][1] if len(top) > 1 else 0.0
        if conf < self.umbral or conf - segunda < self.margen:
            return None, conf
        return letra, conf
