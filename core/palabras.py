"""Palabras de LESCO: seña de una o dos manos ubicada respecto del cuerpo, comparada con DTW.

Modo aparte del deletreo (core/reconocedor.py): no cambia nada de las letras.
Sin modelos entrenados: cada palabra tiene plantillas (las dos repeticiones del
video de CENAREC) y una seña nueva se compara con todas por DTW.

  1. Por frame, core/cuerpo.DetectorCuerpo da hasta 2 manos y la pose.
     `cuadro_palabra()` arma un `CuadroPalabra`:
       - (v3) si la imagen llega GIRADA 180° (celular o cámara al revés: la nariz
         visible queda DEBAJO de la línea de los hombros, `cabeza_abajo`: nariz.y menos
         el promedio de y de los dos hombros > MARGEN_CABEZA_ABAJO, con la nariz
         visible (>= VISIBILIDAD_MIN); se evalúa en cada cuadro, ANTES de mirar si se
         ven los hombros), pose y
         manos se giran antes de todo: (x, y) -> (1 - x, 1 - y) en coordenadas
         normalizadas (z igual). Un giro no es un espejo: la mano no cambia de lado.
         Así venían 55 de las 60 tomas del iPhone del banco de prueba;
       - referencia del cuerpo: centro de los hombros (pose 11, 12) y ancho de
         hombros W, en píxeles con la corrección de proporción (x*ancho, y*alto);
       - dos BRAZOS por posición en la imagen: 0 = el del hombro de la izquierda
         de la imagen, 1 = el de la derecha. No se usan las etiquetas Left/Right
         de MediaPipe (cambian de un frame a otro con las manos juntas). Cada mano
         detectada va al brazo cuya muñeca de pose (15, 16) le queda más cerca;
       - por brazo: muñeca en píxeles (de la mano si se detectó, si no la muñeca
         de la pose si está dentro de la imagen) y forma de la mano: los 31
         rasgos de core/rasgos.py + ejes "y" y "z" del marco de la palma (6), con
         el vector de landmarks.py espejado si es el brazo 0 (como una "Left").
  2. `Segmentador` corta la seña usando el REPOSO: un brazo descansa si no se ve
     su muñeca o si está más abajo que su UMBRAL de reposo (en anchos de hombro
     debajo de los hombros). La seña arranca cuando algún brazo sale del reposo
     T_ARRANQUE s seguidos y termina cuando los dos vuelven T_FIN s seguidos. Lo
     mismo corta las dos repeticiones de cada video y la cámara en vivo.
     Reposo RELATIVO (v3; antes el umbral era Y_REPOSO fijo para todos): por
     brazo, el Segmentador guarda la altura de la muñeca de los últimos
     VENTANA_REPOSO s (sin muñeca = ABAJO) y en cada cuadro calcula
         nivel  = alturas ordenadas[(n - 1) * PERCENTIL_REPOSO // 100]
         umbral = min(max(nivel - DELTA_REPOSO, Y_REPOSO_MIN), Y_REPOSO)
     y lo deja en `cuadro.reposo` (lo usan también actividad() y el descriptor).
     Detalles para reimplementarlo igual: la ventana incluye el cuadro actual y solo
     la alimentan los cuadros que dieron CuadroPalabra (sin cuerpo no aporta); se
     descartan los cuadros con t - t_más_viejo > VENTANA_REPOSO (estricto: uno a
     exactamente 10.0 s se queda); no se vacía al cortar por hueco, solo en
     reiniciar(); el umbral se calcula ya con el valor del cuadro actual dentro; una
     muñeca fuera de [0, 1] o con visibilidad < VISIBILIDAD_MIN cuenta como ausente
     (ABAJO = 9).
     Con las manos fuera de cuadro o bien abajo (CENAREC, casi todas las cámaras)
     queda Y_REPOSO; con las manos apoyadas a la vista más arriba (escritorio,
     cámara baja) el umbral sube con ellas y la seña se corta igual.
  3. `descriptor()` lleva la seña a forma canónica y a MUESTRAS puntos parejos en
     el tiempo:
       - mano DOMINANTE (`espejos_posibles`): en una seña de UNA mano, la que
         sale del reposo. En una de DOS manos no se puede saber (las dos suben y
         bajan; medir cuál "recorre más" falla): se prueba como diestra y como
         zurda y se queda la mejor (o se fija con mano="derecha"/"izquierda").
         Si la dominante es el brazo 0 se espeja todo: x de las posiciones
         negada y los brazos intercambiados. Las formas ya están espejadas por
         brazo, así que una zurda queda igual que una diestra;
       - posición de cada muñeca = (muñeca - centro de hombros) / W (mediana de la
         seña): no depende de la distancia, del encuadre ni de la proporción;
       - la mano NO dominante cuenta solo si sale del reposo al menos
         FRACCION_ACTIVA de la seña (si no, es una seña de una mano y su bloque
         queda en 0 con la marca "activa" = 0);
       - huecos de la mano: interpolación lineal en el tiempo.
       - posición respecto de la CARA (problema 3, fase 3): c = (muñeca - nariz) / W
         cuadro a cuadro (nariz interpolada; si no se ve nunca, NARIZ_TIPICA
         respecto de los hombros), multiplicada por max(0, 1 - |c| / CARA_RADIO):
         solo cuenta con la mano CERCA de la cara (frente, boca, mejilla) y lejos
         queda en 0. Restarla siempre ("resta") empeoraba con otras personas: la
         distancia nariz-hombros cambia de persona a persona y con la cámara.
     Por muestra (83 valores):
       dominante: posición (2) x PESO_POSICION, rasgos (31) x PESO_FORMA, ejes (6) x PESO_EJES,
                  cara (2) x PESO_CARA
       no dominante: lo mismo x PESO_NO_DOMINANTE, y la marca activa x PESO_ACTIVA
  4. `dtw_lote()`: el mismo DTW de core/movimiento.dtw (banda de Sakoe-Chiba,
     pasos simétricos, dividido por n + m) contra todas las plantillas a la vez.
     confianza = 1 - distancia / DISTANCIA_MAX; se acepta la mejor palabra (d1) si
       - pasa UMBRAL (d1 <= (1 - UMBRAL) * DISTANCIA_MAX),
       - (v3) margen RELATIVO: la 2.ª palabra está a d2 >= MARGEN * d1 (antes una
         resta de confianzas fija),
       - (v3) la seña dura al menos DURACION_RELATIVA_MIN x la plantilla más corta
         de esa palabra (duración de la plantilla = fin - inicio en senas.db): un
         pedazo de seña no se dice como palabra,
       - y no es una plantilla NEGATIVA (categoría "letra": letras deletreadas).
     Si no, "nada": nunca inventa. Con d1 = d2 = 0 (dos palabras idénticas) tampoco
     se dice nada.

Versión 3 del descriptor (VERSION_DESCRIPTOR): giro de 180°, reposo relativo,
PESO_FORMA 0.5 -> 1.0, PESO_NO_DOMINANTE 0.7 -> 1.0, margen relativo y control de
duración, DISTANCIA_MAX 3 -> 5 (cambia la confianza mostrada: 1 - d / 5). Las
columnas de senas.db no cambian (83), pero la app tiene que
implementar todo lo marcado "v3" para dar los mismos números; por eso senas.db
de la v2 no se carga con este motor ni al revés. Medido con scripts/evaluar_banco.py
(ajustado con dos personas y validado con las otras dos).

Todo es aritmética simple (medianas, interpolación lineal, normas, DTW con dos
bucles) para poder reimplementarlo igual en Dart. Constantes medidas con
scripts/evaluar_palabras.py. El almacenamiento está en core/senas_db.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from core.cuerpo import HOMBRO_DER, HOMBRO_IZQ, MUNECA_DER, MUNECA_IZQ, NARIZ, CuadroCuerpo
from core.landmarks import NUM_LANDMARKS, WRIST, corregir_proporcion, normalizar_puntos
from core.rasgos import NUM_RASGOS, marco_palma, rasgos

VERSION_DESCRIPTOR = 3   # 2: + posición respecto de la cara; 3: giro 180°, reposo relativo, pesos, margen relativo

# --- Cuerpo ---
VISIBILIDAD_MIN = 0.5      # hombros con menos visibilidad = no hay cuerpo en el frame
W_MIN = 20.0               # ancho de hombros mínimo en píxeles
GIRAR_CABEZA_ABAJO = True  # imagen girada 180° (nariz debajo de los hombros) -> se gira antes de describir
MARGEN_CABEZA_ABAJO = 0.05  # la nariz tiene que estar más de esto (fracción del alto) bajo la línea de los hombros

# --- Segmentación (posiciones en anchos de hombro, tiempos en segundos) ---
Y_REPOSO = 0.85            # muñeca más abajo que esto (desde los hombros) = descansa (CENAREC: reposo 0.93-1.33, señas suben a <= 0.67)
T_ARRANQUE = 0.10          # tanto tiempo fuera del reposo = empieza la seña
T_FIN = 0.25               # tanto tiempo los dos brazos en reposo = terminó
PREVIOS = 0.15             # la seña arranca un poco antes (la mano ya venía subiendo)
DURACION_MIN = 0.35
DURACION_MAX = 6.0         # más largo = no es una palabra (deletreo, la mano quieta arriba). 4 -> 6 (2026-11-12):
                           # en el banco 8 de las 10 tomas "sin seña" tenían las manos arriba entre 4 y 6 s;
                           # con 6 (solo DTW): top-1 64.2 -> 67.1 %, sin seña 4.2 -> 0.4 %, aceptación errónea igual
                           # (0.4 %). Pendiente: medirlo con deletreo real (una letra sostenida 4-6 s ahora llega al
                           # comparador; la frenan el umbral y el margen, no hay control de duración máxima)
HUECO_MAX = 0.5            # sin cuerpo más tiempo que esto corta la seña
# Reposo RELATIVO (v3): cada brazo descansa donde descansa esa persona con esa cámara. Nivel de reposo =
# percentil PERCENTIL_REPOSO de la altura de la muñeca en los últimos VENTANA_REPOSO s (sin muñeca = ABAJO);
# umbral = nivel - DELTA_REPOSO, entre Y_REPOSO_MIN y Y_REPOSO (nunca más exigente que el umbral fijo).
VENTANA_REPOSO = 10.0
PERCENTIL_REPOSO = 90
DELTA_REPOSO = 0.15
Y_REPOSO_MIN = 0.5
ABAJO = 9.0                # altura que cuenta un brazo sin muñeca (fuera de cuadro = abajo del todo)

# --- Descriptor ---
MUESTRAS = 24
FRACCION_ACTIVA = 0.25     # la no dominante tiene que estar fuera del reposo este tanto de la seña
PESO_POSICION = 2.0
PESO_FORMA = 1.0           # v3: 0.5 -> 1.0 (la posición pesaba demasiado frente a la forma con otras personas)
PESO_EJES = 0.5
PESO_NO_DOMINANTE = 1.0    # v3: 0.7 -> 1.0
PESO_ACTIVA = 1.0
PESO_CARA = 1.0
CARA_MODO = "cerca"           # "resta" (muñeca - nariz), "cerca" (solo cerca de la cara), "cerca_y"
CARA_RADIO = 0.6              # anchos de hombro: más lejos de la nariz que esto, la cara no cuenta
NARIZ_TIPICA = (0.0, -0.63)   # (nariz - centro de hombros) / W, mediana de CENAREC: respaldo si no se ve la cara
FORMA = NUM_RASGOS + 6
BLOQUE = 2 + FORMA + 2
COLUMNAS = 2 * BLOQUE + 1

# --- Comparación ---
BANDA = 0.25
PREFILTRO = 150            # con más plantillas, el DTW se hace solo con las 150 más cercanas en línea recta
DISTANCIA_MAX = 5.0        # v3: 3.0 -> 5.0 (con PESO_FORMA 1.0 las distancias son más grandes)
UMBRAL = 0.5               # confianza mínima: distancia <= (1 - UMBRAL) * DISTANCIA_MAX = 2.5
MARGEN = 1.18              # v3: margen RELATIVO: la 2.ª palabra tiene que estar >= MARGEN x la distancia de la 1.ª
DURACION_RELATIVA_MIN = 0.5  # la seña dura al menos esto x la plantilla más corta de la palabra (si se conoce):
                             # un pedazo de seña (el comienzo o el final) no se dice como otra palabra


@dataclass
class CuadroPalabra:
    t: float
    centro: np.ndarray                  # (2,) píxeles: medio de los hombros
    ancho: float                        # píxeles: ancho de hombros
    muneca: list                        # [ (2,) píxeles o None ] por brazo 0, 1
    forma: list                         # [ (37,) o None ] por brazo 0, 1
    nariz: Optional[np.ndarray] = None  # (2,) píxeles
    reposo: Optional[tuple] = None      # (umbral brazo 0, brazo 1) en anchos de hombro; lo pone el Segmentador
                                        # (reposo relativo). None = Y_REPOSO fijo
    puntos: Optional[list] = None       # [ (63,) o None ] por brazo: los 21 puntos normalizados (puntos_mano).
                                        # Solo para el modelo de la fase 4 del problema 1; el descriptor no los usa.


def _px(p, frame) -> np.ndarray:
    return np.array([p[0] * frame[0], p[1] * frame[1]], dtype=np.float64)


def forma_mano(puntos, brazo: int, frame) -> Optional[np.ndarray]:
    """31 rasgos + ejes y, z de la palma (37,) de una mano; el brazo 0 se espeja como una "Left"."""
    try:
        v = normalizar_puntos(corregir_proporcion(puntos, frame), "Left" if brazo == 0 else "Right")
    except ValueError:
        return None
    r = rasgos(v)
    pts = v.reshape(NUM_LANDMARKS, 3).astype(np.float64)
    base = marco_palma(pts - pts[WRIST])
    if r is None or base is None:
        return None
    return np.concatenate([r, base[1], base[2]])


def puntos_mano(puntos, brazo: int, frame) -> Optional[np.ndarray]:
    """Los 21 puntos de la mano normalizados (63,) como en forma_mano (el brazo 0 espejado como "Left")."""
    try:
        return np.asarray(normalizar_puntos(corregir_proporcion(puntos, frame), "Left" if brazo == 0 else "Right"),
                          dtype=np.float64).reshape(-1)
    except ValueError:
        return None


def cabeza_abajo(pose: np.ndarray) -> bool:
    """La imagen está girada 180° (celular o cámara al revés): la nariz se ve DEBAJO de los hombros.

    Con un MARGEN (MARGEN_CABEZA_ABAJO, en fracción del alto de la imagen): así una persona
    agachada o una pose ruidosa no hacen saltar el giro entre cuadros de la misma seña.
    Medido en las 240 tomas del banco: de pie la nariz queda >= 0.145 POR ENCIMA de la línea
    de los hombros (y_nariz - y_hombros <= -0.145) y con la imagen girada >= 0.27 por debajo."""
    if pose[NARIZ, 3] < VISIBILIDAD_MIN:
        return False
    return pose[NARIZ, 1] - (pose[HOMBRO_IZQ, 1] + pose[HOMBRO_DER, 1]) / 2 > MARGEN_CABEZA_ABAJO


def _girar_180(puntos: np.ndarray) -> np.ndarray:
    """(x, y) normalizados -> (1 - x, 1 - y): la imagen girada 180° (z y visibilidad no cambian)."""
    p = np.array(puntos, dtype=np.float64)
    p[:, 0] = 1.0 - p[:, 0]
    p[:, 1] = 1.0 - p[:, 1]
    return p


def cuadro_palabra(c: CuadroCuerpo) -> Optional[CuadroPalabra]:
    """CuadroPalabra de un frame, o None si no se ve el cuerpo (hombros).

    Si la imagen llega girada 180° (cabeza_abajo), pose y manos se giran antes de
    todo (un giro no cambia la mano de lado: no es un espejo)."""
    if c.pose is None:
        return None
    pose, frame, manos_crudas = c.pose, c.frame, c.manos[:2]
    if GIRAR_CABEZA_ABAJO and cabeza_abajo(pose):
        pose = _girar_180(pose)
        manos_crudas = [(_girar_180(pts), lado, score) for pts, lado, score in manos_crudas]
    if pose[HOMBRO_IZQ, 3] < VISIBILIDAD_MIN or pose[HOMBRO_DER, 3] < VISIBILIDAD_MIN:
        return None
    hi, hd = _px(pose[HOMBRO_IZQ], frame), _px(pose[HOMBRO_DER], frame)
    ancho = float(np.linalg.norm(hi - hd))
    if ancho < W_MIN:
        return None
    # Brazo 0 = el del hombro que queda a la izquierda de la imagen.
    indices = (MUNECA_IZQ, MUNECA_DER) if hi[0] < hd[0] else (MUNECA_DER, MUNECA_IZQ)
    munecas_pose = []
    for k in indices:
        p = pose[k]
        dentro = 0.0 <= p[0] <= 1.0 and 0.0 <= p[1] <= 1.0
        munecas_pose.append(_px(p, frame) if dentro and p[3] >= VISIBILIDAD_MIN else None)
    ref = [m if m is not None else _px(pose[k], frame) for m, k in zip(munecas_pose, indices)]

    muneca, forma, pts_mano = list(munecas_pose), [None, None], [None, None]
    manos = [(np.asarray(pts, dtype=np.float64), _px(pts[WRIST], frame)) for pts, _, _ in manos_crudas]
    if len(manos) == 2:
        directo = np.linalg.norm(manos[0][1] - ref[0]) + np.linalg.norm(manos[1][1] - ref[1])
        cruzado = np.linalg.norm(manos[0][1] - ref[1]) + np.linalg.norm(manos[1][1] - ref[0])
        asignacion = [(0, manos[0]), (1, manos[1])] if directo <= cruzado else [(1, manos[0]), (0, manos[1])]
    elif len(manos) == 1:
        brazo = int(np.argmin([np.linalg.norm(manos[0][1] - r) for r in ref]))
        asignacion = [(brazo, manos[0])]
    else:
        asignacion = []
    for brazo, (pts, w) in asignacion:
        muneca[brazo] = w
        forma[brazo] = forma_mano(pts, brazo, frame)
        if forma[brazo] is not None:
            pts_mano[brazo] = puntos_mano(pts, brazo, frame)
    nariz = _px(pose[NARIZ], frame) if pose[NARIZ, 3] >= VISIBILIDAD_MIN else None
    return CuadroPalabra(c.t, (hi + hd) / 2, ancho, muneca, forma, nariz, puntos=pts_mano)


# ---------------------------------------------------------------- reposo y segmentación

def altura(c: CuadroPalabra, brazo: int) -> float:
    """Altura de la muñeca debajo de los hombros en anchos de hombro (ABAJO si no se ve)."""
    m = c.muneca[brazo]
    return ABAJO if m is None else float((m[1] - c.centro[1]) / c.ancho)


def umbral_reposo(alturas: Sequence[float]) -> float:
    """Umbral de reposo de un brazo a partir de sus alturas recientes (reposo relativo).

    nivel = alturas ordenadas[(n - 1) * PERCENTIL_REPOSO // 100] (sin interpolar, igual en Dart);
    umbral = nivel - DELTA_REPOSO, recortado a [Y_REPOSO_MIN, Y_REPOSO]. Si el brazo casi siempre
    está fuera de cuadro o bien abajo (CENAREC, la mayoría de las cámaras), queda Y_REPOSO."""
    if not alturas:
        return Y_REPOSO
    orden = sorted(alturas)
    nivel = orden[(len(orden) - 1) * PERCENTIL_REPOSO // 100]
    return float(min(max(nivel - DELTA_REPOSO, Y_REPOSO_MIN), Y_REPOSO))


def brazo_en_reposo(c: CuadroPalabra, brazo: int, centro=None, ancho=None) -> bool:
    m = c.muneca[brazo]
    if m is None:
        return True
    centro = c.centro if centro is None else centro
    ancho = c.ancho if ancho is None else ancho
    umbral = Y_REPOSO if c.reposo is None else c.reposo[brazo]
    return (m[1] - centro[1]) / ancho > umbral


def en_reposo(c: Optional[CuadroPalabra]) -> bool:
    return c is None or (brazo_en_reposo(c, 0) and brazo_en_reposo(c, 1))


class Segmentador:
    """Corta el flujo de CuadroPalabra en señas (de reposo a reposo).

    actualizar(cuadro, t) en cada frame (cuadro None = sin cuerpo). Devuelve la
    lista de cuadros de la seña cuando termina, o None. `activo` = hay una seña en curso.

    relativo=True (reposo relativo): a cada cuadro le pone `reposo` = el umbral de
    cada brazo según dónde descansó ese brazo en los últimos VENTANA_REPOSO s
    (umbral_reposo). relativo=False: Y_REPOSO fijo (como antes de la v3).
    """

    def __init__(self, arranque=T_ARRANQUE, fin=T_FIN, previos=PREVIOS, duracion_min=DURACION_MIN,
                 duracion_max=DURACION_MAX, hueco_max=HUECO_MAX, relativo=True):
        self.arranque, self.fin, self.previos = arranque, fin, previos
        self.duracion_min, self.duracion_max, self.hueco_max = duracion_min, duracion_max, hueco_max
        self.relativo = relativo
        self.reiniciar()

    def reiniciar(self) -> None:
        self._alturas: tuple = ([], [])    # (t, altura) recientes por brazo (reposo relativo)
        self._historia: list = []          # cuadros recientes en reposo (para PREVIOS)
        self._sena: Optional[list] = None
        self._fuera_desde: Optional[float] = None
        self._reposo_desde: Optional[float] = None
        self._ultimo_t: Optional[float] = None
        self.largo = False                  # la seña en curso ya pasó DURACION_MAX (se descarta al terminar)

    @property
    def activo(self) -> bool:
        return self._sena is not None

    def actualizar(self, cuadro: Optional[CuadroPalabra], t: float) -> Optional[list]:
        if cuadro is None:
            if self._ultimo_t is not None and t - self._ultimo_t > self.hueco_max:
                return self._cerrar_por_hueco()
            return None
        if self._ultimo_t is not None and cuadro.t - self._ultimo_t > self.hueco_max:
            sena = self._cerrar_por_hueco()
            self._ultimo_t = cuadro.t
            self._paso(cuadro)
            return sena
        self._ultimo_t = cuadro.t
        return self._paso(cuadro)

    def _marcar_reposo(self, c: CuadroPalabra) -> None:
        """Pone en el cuadro el umbral de reposo de cada brazo (ventana de VENTANA_REPOSO s hasta este cuadro)."""
        if not self.relativo:
            c.reposo = None
            return
        umbrales = []
        for b in (0, 1):
            ventana = self._alturas[b]
            ventana.append((c.t, altura(c, b)))
            while ventana and c.t - ventana[0][0] > VENTANA_REPOSO:
                ventana.pop(0)
            umbrales.append(umbral_reposo([y for _, y in ventana]))
        c.reposo = tuple(umbrales)

    def _paso(self, c: CuadroPalabra) -> Optional[list]:
        self._marcar_reposo(c)
        reposo = en_reposo(c)
        if self._sena is None:
            if reposo:
                self._fuera_desde = None
                self._historia.append(c)
                while self._historia and c.t - self._historia[0].t > self.previos + self.arranque + 0.5:
                    self._historia.pop(0)
                return None
            if self._fuera_desde is None:
                self._fuera_desde = c.t
            self._historia.append(c)
            if c.t - self._fuera_desde >= self.arranque - 1e-9:
                desde = self._fuera_desde - self.previos
                self._sena = [x for x in self._historia if x.t >= desde - 1e-9]
                self._historia, self._reposo_desde, self.largo = [], None, False
            return None
        self._sena.append(c)
        if not reposo:
            self._reposo_desde = None
        elif self._reposo_desde is None:
            self._reposo_desde = c.t
        if c.t - self._sena[0].t > self.duracion_max:
            self.largo = True
        if self._reposo_desde is not None and c.t - self._reposo_desde >= self.fin - 1e-9:
            return self._cerrar()
        return None

    def _cerrar(self) -> Optional[list]:
        sena, self._sena = self._sena, None
        fin = self._reposo_desde if self._reposo_desde is not None else sena[-1].t
        self._reposo_desde, self._fuera_desde, self._historia = None, None, []
        largo, self.largo = self.largo, False
        # Se queda hasta el primer cuadro en reposo (la mano ya bajó).
        sena = [x for x in sena if x.t <= fin + 1e-9]
        if largo or len(sena) < 4 or sena[-1].t - sena[0].t < self.duracion_min:
            return None
        return sena

    def _cerrar_por_hueco(self) -> Optional[list]:
        sena = self._cerrar() if self._sena is not None else None
        self._historia, self._ultimo_t, self._fuera_desde = [], None, None
        return sena

    def terminar(self) -> Optional[list]:
        """Fin del video: cierra la seña en curso si la hay."""
        return self._cerrar() if self._sena is not None else None


def segmentar(cuadros: Sequence[Optional[CuadroPalabra]], tiempos: Sequence[float], **kw) -> list[list]:
    """Todas las señas de una secuencia grabada (mismo Segmentador que en vivo)."""
    seg = Segmentador(**kw)
    salida = []
    for c, t in zip(cuadros, tiempos):
        s = seg.actualizar(c, t)
        if s:
            salida.append(s)
    s = seg.terminar()
    if s:
        salida.append(s)
    return salida


def duracion(cuadros: Sequence[Optional[CuadroPalabra]]) -> float:
    """Segundos entre el primer y el último cuadro de una seña (0 si no hay dos)."""
    ts = [c.t for c in cuadros if c is not None]
    return float(ts[-1] - ts[0]) if len(ts) > 1 else 0.0


# ---------------------------------------------------------------- descriptor

def _interpolar(t: np.ndarray, filas: list, grilla: np.ndarray, columnas: int) -> Optional[np.ndarray]:
    """filas: valores (columnas,) o None por cuadro -> (len(grilla), columnas) interpolado; None si no hay ninguno."""
    validos = [i for i, f in enumerate(filas) if f is not None]
    if not validos:
        return None
    tv = t[validos]
    m = np.array([filas[i] for i in validos], dtype=np.float64).reshape(len(validos), columnas)
    if len(validos) == 1:
        return np.repeat(m, len(grilla), axis=0)
    return np.stack([np.interp(grilla, tv, m[:, k]) for k in range(columnas)], axis=1)


def actividad(cuadros: Sequence[CuadroPalabra]) -> tuple[float, float]:
    """Fracción de la seña que cada brazo (0, 1) pasa fuera del reposo (con el centro y W medianos)."""
    centro = np.median([c.centro for c in cuadros], axis=0)
    ancho = float(np.median([c.ancho for c in cuadros]))
    return tuple(float(np.mean([not brazo_en_reposo(c, b, centro, ancho) for c in cuadros])) for b in (0, 1))


def espejos_posibles(cuadros: Sequence[CuadroPalabra], mano: str = "auto") -> list[bool]:
    """Con qué espejos hay que describir la seña para compararla.

    Seña de UNA mano (solo un brazo sale del reposo FRACCION_ACTIVA): la
    dominante es esa, sin dudas -> [espejo si es el brazo 0]. Seña de DOS manos:
    no se sabe cuál es la dominante (las dos suben y bajan) -> mano "derecha":
    [False], "izquierda": [True], "auto": [False, True] (se queda la mejor).
    """
    cuadros = [c for c in cuadros if c is not None]
    if not cuadros:
        return [False]
    a0, a1 = actividad(cuadros)
    if a0 >= FRACCION_ACTIVA and a1 < FRACCION_ACTIVA:
        return [True]
    if a1 >= FRACCION_ACTIVA and a0 < FRACCION_ACTIVA:
        return [False]
    if a0 < FRACCION_ACTIVA and a1 < FRACCION_ACTIVA:
        return [a0 > a1]
    return {"derecha": [False], "izquierda": [True]}.get(mano, [False, True])


def pesos_completos(pesos=None) -> tuple:
    """(posición, forma, ejes, no_dominante, activa, cara). Con 5 valores (antes de la v2) la cara va con PESO_CARA."""
    if pesos is None:
        return PESO_POSICION, PESO_FORMA, PESO_EJES, PESO_NO_DOMINANTE, PESO_ACTIVA, PESO_CARA
    pesos = tuple(float(x) for x in pesos)
    return pesos + (PESO_CARA,) if len(pesos) == 5 else pesos


def descriptor(cuadros: Sequence[CuadroPalabra], espejo: bool = False, muestras: int = MUESTRAS,
               pesos=None) -> Optional[np.ndarray]:
    """(muestras, COLUMNAS) de la seña en forma canónica (dominante como diestra). None si no alcanza.

    espejo=True: la dominante es el brazo 0 (zurdo): x de las posiciones negada y
    brazos intercambiados. Ver espejos_posibles().
    """
    pp, pf, pe, pn, pa, pc = pesos_completos(pesos)
    cuadros = [c for c in cuadros if c is not None]
    if len(cuadros) < 2:
        return None
    t = np.array([c.t for c in cuadros])
    if t[-1] - t[0] <= 0:
        return None
    centro = np.median([c.centro for c in cuadros], axis=0)
    ancho = float(np.median([c.ancho for c in cuadros]))
    dom, nod = (0, 1) if espejo else (1, 0)
    fuera = actividad(cuadros)
    grilla = np.linspace(t[0], t[-1], muestras)
    nariz = _interpolar(t, [None if c.nariz is None else (c.nariz - centro) / ancho for c in cuadros], grilla, 2)
    if nariz is None:
        nariz = np.tile(np.array(NARIZ_TIPICA, dtype=np.float64), (muestras, 1))
    bloques = []
    for b, peso in ((dom, 1.0), (nod, pn)):
        p = _interpolar(t, [None if c.muneca[b] is None else (c.muneca[b] - centro) / ancho for c in cuadros],
                        grilla, 2)
        f = _interpolar(t, [c.forma[b] for c in cuadros], grilla, FORMA)
        if b == dom:
            if p is None or f is None:
                return None
        elif p is None or f is None or fuera[b] < FRACCION_ACTIVA:
            bloques.append(np.zeros((muestras, BLOQUE)))
            continue
        cara = p - nariz
        if CARA_MODO != "resta":
            # Solo cuenta cerca de la cara: lejos queda en 0 para todos (sin el corrimiento fijo
            # que da la distancia nariz-hombros, que cambia de persona a persona y con la cámara).
            g = np.clip(1.0 - np.linalg.norm(cara, axis=1) / CARA_RADIO, 0.0, 1.0)[:, None]
            cara = cara * g
            if CARA_MODO == "cerca_y":
                cara = cara * np.array([0.0, 1.0])
        if espejo:
            p = p * np.array([-1.0, 1.0])
            cara = cara * np.array([-1.0, 1.0])
        bloques.append(np.concatenate([p * pp, f[:, :NUM_RASGOS] * pf, f[:, NUM_RASGOS:] * pe, cara * pc],
                                      axis=1) * peso)
    activa = 0.0 if not np.any(bloques[1]) else pa
    return np.concatenate([bloques[0], bloques[1], np.full((muestras, 1), activa)], axis=1)


def descriptores(cuadros: Sequence[CuadroPalabra], mano: str = "auto", muestras: int = MUESTRAS,
                 pesos=None) -> list[np.ndarray]:
    """Los descriptores a probar de una seña (1, o 2 si es de dos manos y no se sabe la dominante)."""
    salida = []
    for e in espejos_posibles(cuadros, mano):
        d = descriptor(cuadros, e, muestras, pesos)
        if d is not None:
            salida.append(d)
    return salida


# ---------------------------------------------------------------- comparación

def dtw_lote(a: np.ndarray, plantillas: np.ndarray, banda: float = BANDA) -> np.ndarray:
    """DTW de `a` (n, F) contra cada plantilla de `plantillas` (T, m, F): (T,) costo medio por paso.

    Igual que core/movimiento.dtw (diagonal x2, horizontal y vertical x1,
    dividido por n + m), vectorizado sobre las plantillas.
    """
    n = a.shape[0]
    total, m = plantillas.shape[0], plantillas.shape[1]
    if total == 0:
        return np.zeros(0)
    w = max(int(np.ceil(banda * max(n, m))), abs(n - m))
    costo = np.sqrt(np.maximum(
        (a * a).sum(1)[None, :, None] + (plantillas * plantillas).sum(2)[:, None, :]
        - 2.0 * np.einsum("nf,tmf->tnm", a, plantillas), 0.0))
    D = np.full((total, n + 1, m + 1), np.inf)
    D[:, 0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(max(1, i - w), min(m, i + w) + 1):
            c = costo[:, i - 1, j - 1]
            D[:, i, j] = np.minimum(np.minimum(D[:, i - 1, j - 1] + 2 * c, D[:, i - 1, j] + c), D[:, i, j - 1] + c)
    return D[:, n, m] / (n + m)


def confianza(distancia):
    return np.clip(1.0 - np.asarray(distancia) / DISTANCIA_MAX, 0.0, 1.0)


class ComparadorPalabras:
    """Plantillas en memoria (ya como descriptores) y búsqueda de la palabra más parecida.

    categorias: etiqueta -> "palabra" (por defecto) u otra cosa (p. ej. "letra":
    las letras deletreadas de CENAREC). Las que no son "palabra" sirven de
    NEGATIVAS: si la seña se parece más a una letra deletreada que a cualquier
    palabra, no se dice nada.

    margen: RELATIVO (v3): se acepta si distancia de la 2.ª palabra >= margen x
    distancia de la 1.ª (antes era una resta de confianzas, 0.05; con personas
    distintas a CENAREC las distancias crecen y una resta fija callaba casi todo).
    duraciones: segundos de cada plantilla (fin - inicio en senas.db), opcional.
    Si están y clasificar() recibe la duración de la seña, no se acepta una seña
    que dure menos de DURACION_RELATIVA_MIN x la plantilla más corta de la palabra.
    """

    def __init__(self, etiquetas: Sequence[str], descriptores: Sequence[np.ndarray], umbral: float = UMBRAL,
                 margen: float = MARGEN, banda: float = BANDA, categorias: Optional[dict] = None,
                 prefiltro: Optional[int] = PREFILTRO, duraciones: Optional[Sequence[Optional[float]]] = None,
                 duracion_relativa: float = DURACION_RELATIVA_MIN):
        if len(etiquetas) != len(descriptores) or not etiquetas:
            raise ValueError("Hacen falta plantillas (etiqueta, descriptor)")
        if duraciones is not None and len(duraciones) != len(etiquetas):
            raise ValueError("duraciones: una por plantilla")
        self.umbral, self.margen, self.banda, self.prefiltro = umbral, margen, banda, prefiltro
        self.duracion_relativa = duracion_relativa
        self._etiquetas = list(etiquetas)
        self._plantillas = np.stack([np.asarray(d, dtype=np.float64) for d in descriptores])
        self.categorias = {e: (categorias or {}).get(e, "palabra") for e in self._etiquetas}
        self.palabras = sorted(e for e in set(self._etiquetas) if self.categorias[e] == "palabra")
        # palabra -> duración de su plantilla más corta (segundos)
        self.duracion_min: dict[str, float] = {}
        for e, d in zip(self._etiquetas, duraciones or []):
            if d is not None and d > 0:
                self.duracion_min[e] = min(float(d), self.duracion_min.get(e, np.inf))

    def distancias(self, candidatos) -> dict:
        """palabra -> distancia de su plantilla más cercana (la mejor de los candidatos).

        candidatos: un descriptor (muestras, COLUMNAS) o la lista de descriptores()."""
        if isinstance(candidatos, np.ndarray):
            candidatos = [candidatos]
        dist = np.full(len(self._etiquetas), np.inf)
        for d in candidatos:
            indices = np.arange(len(self._etiquetas))
            if self.prefiltro and len(indices) > self.prefiltro and d.shape[0] == self._plantillas.shape[1]:
                # Distancia "en línea recta" (cuadro i con cuadro i): barata; el DTW solo con las más cercanas.
                recta = np.linalg.norm(self._plantillas - d[None], axis=2).mean(axis=1)
                indices = np.argpartition(recta, self.prefiltro)[:self.prefiltro]
            dist[indices] = np.minimum(dist[indices], dtw_lote(d, self._plantillas[indices], self.banda))
        salida: dict[str, float] = {}
        for e, x in zip(self._etiquetas, dist):
            if x < salida.get(e, np.inf):
                salida[e] = float(x)
        return salida

    def mejores(self, candidatos, k: int = 5) -> list[tuple[str, float]]:
        """[(palabra, confianza)] de mayor a menor."""
        dist = self.distancias(candidatos)
        orden = sorted(dist.items(), key=lambda p: p[1])[:k]
        return [(e, float(confianza(x))) for e, x in orden]

    def clasificar(self, candidatos, duracion: Optional[float] = None) -> tuple[Optional[str], float, list]:
        """(palabra o None, confianza, top-5). None si no pasa umbral, margen y duración: nunca inventa.

        duracion: segundos de la seña (último cuadro - primero), para el control de DURACION_RELATIVA_MIN."""
        if candidatos is None or (isinstance(candidatos, list) and not candidatos):
            return None, 0.0, []
        dist = self.distancias(candidatos)
        orden = sorted(dist.items(), key=lambda p: p[1])
        top = [(e, float(confianza(x))) for e, x in orden[:5]]
        palabra, d1 = orden[0]
        d2 = orden[1][1] if len(orden) > 1 else np.inf
        conf = top[0][1]
        corta = (duracion is not None and palabra in self.duracion_min
                 and duracion < self.duracion_relativa * self.duracion_min[palabra])
        if conf < self.umbral or d2 < self.margen * d1 or d2 == 0 or corta or self.categorias[palabra] != "palabra":
            return None, conf, top
        return palabra, conf, top
