"""Mejoras de imagen para poca luz y contraluz (problema 4 — luz y contraste).

La idea: cuando el frame llega oscuro, MediaPipe deja de encontrar las manos.
Antes de detectar se puede aclarar la imagen. Dos herramientas:

  gamma()  sube las sombras con una curva (LUT). Aclara lo oscuro sin quemar
           lo claro. Es lo que más ayuda en poca luz pareja.
  clahe()  realce de contraste LOCAL sobre la luminancia. Ayuda cuando una
           parte está bien y otra oscura (contraluz): levanta la zona oscura
           sin lavar el resto.

El brillo se mide EN LA ZONA DE LA MANO, no en todo el cuadro: en contraluz el
cuadro entero puede estar muy iluminado (la ventana) mientras la mano está
oscura. La pose de MediaPipe encuentra las muñecas aun en contraluz, así que la
caja alrededor de las muñecas da una medida fiable de cuánta luz tiene la mano.
"""
from __future__ import annotations

import cv2
import numpy as np

# Muñecas en MediaPipe Pose (mismos índices que core/cuerpo.py).
MUNECA_IZQ, MUNECA_DER = 15, 16

ESTRATEGIAS = ("ninguna", "gamma", "clahe", "gamma_clahe",
               "denoise_gamma", "denoise_clahe", "denoise_gamma_clahe")


def gamma(frame, g: float = 2.2):
    """Aclara subiendo las sombras con una LUT. g > 1 aclara; g = 1 no toca nada."""
    if g == 1.0:
        return frame
    lut = np.clip((np.arange(256) / 255.0) ** (1.0 / g) * 255.0, 0, 255).astype(np.uint8)
    return cv2.LUT(frame, lut)


def denoise(frame, d: int = 7, sigma: float = 80.0):
    """Quita ruido conservando los bordes (bilateral). En poca luz el ruido es lo que
    más estorba: si se aclara sin quitarlo primero, gamma/CLAHE lo amplifican."""
    return cv2.bilateralFilter(frame, d, sigma, sigma)


def clahe(frame, clip: float = 2.0, grid: int = 8):
    """Realce de contraste local (CLAHE) sobre la luminancia (canal L de LAB)."""
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    canal_l, canal_a, canal_b = cv2.split(lab)
    canal_l = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid)).apply(canal_l)
    return cv2.cvtColor(cv2.merge((canal_l, canal_a, canal_b)), cv2.COLOR_LAB2BGR)


def mejorar(frame, estrategia: str):
    """Aplica una estrategia por nombre (ver ESTRATEGIAS)."""
    if estrategia == "ninguna":
        return frame
    if estrategia == "gamma":
        return gamma(frame)
    if estrategia == "clahe":
        return clahe(frame)
    if estrategia == "gamma_clahe":
        return clahe(gamma(frame))
    if estrategia == "denoise_gamma":
        return gamma(denoise(frame))
    if estrategia == "denoise_clahe":
        return clahe(denoise(frame))
    if estrategia == "denoise_gamma_clahe":
        return clahe(gamma(denoise(frame)))
    raise ValueError(f"estrategia desconocida: {estrategia}")


def brillo(frame, caja=None) -> float:
    """Luminancia media (0-255) del frame, o de una caja (x0, y0, x1, y1) en píxeles."""
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if caja is None:
        return float(gris.mean())
    x0, y0, x1, y1 = caja
    region = gris[max(0, y0):max(0, y1), max(0, x0):max(0, x1)]
    return float(region.mean()) if region.size else float(gris.mean())


def caja_munecas(pose_norm, ancho: int, alto: int, radio: float = 0.13):
    """Caja (x0, y0, x1, y1) en píxeles alrededor de las muñecas de la pose.

    pose_norm: array (33, >=2) con x/ancho, y/alto (coords normalizadas de MediaPipe),
    o None si no hay persona. Devuelve None si no hay muñecas usables.
    """
    if pose_norm is None:
        return None
    puntos = []
    for i in (MUNECA_IZQ, MUNECA_DER):
        x, y = float(pose_norm[i, 0]), float(pose_norm[i, 1])
        if np.isfinite(x) and np.isfinite(y):
            puntos.append((x, y))
    if not puntos:
        return None
    r = int(radio * ancho)
    xs = [int(x * ancho) for x, _ in puntos]
    ys = [int(y * alto) for _, y in puntos]
    return (min(xs) - r, min(ys) - r, max(xs) + r, max(ys) + r)


def caja_puntos(puntos_norm, ancho: int, alto: int, margen: float = 0.25):
    """Caja (x0, y0, x1, y1) en píxeles que cubre unos landmarks (x, y normalizados),
    con un margen alrededor. puntos_norm: iterable de (x, y[, z]). None si está vacío."""
    xs, ys = [], []
    for p in puntos_norm:
        x, y = float(p[0]), float(p[1])
        if np.isfinite(x) and np.isfinite(y):
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    ancho_caja = (max(xs) - min(xs)) or 0.1
    alto_caja = (max(ys) - min(ys)) or 0.1
    mx, my = margen * ancho_caja, margen * alto_caja
    return (int((min(xs) - mx) * ancho), int((min(ys) - my) * alto),
            int((max(xs) + mx) * ancho), int((max(ys) + my) * alto))


# ---------------------------------------------------------------- medidor de luz (fase 3)

# El nivel de luz depende SOLO del brillo, medido en la zona central-baja del cuadro
# (donde están el torso y las manos; se evita el techo/la ventana de arriba). NO se
# ata a si hay o no manos: así el nivel es continuo y se recupera solo cuando vuelve
# la luz, sin intervención manual.
#
# Umbrales (luma 0-255) con HISTÉRESIS: el umbral para empeorar de nivel y el de
# mejorar son distintos, para que no parpadee en el límite. Calibrados con el banco
# de luz (brillo en la mano: base ~68, poca_luz_1 ~30, poca_luz_2 ~18, poca_luz_3 ~11);
# se afinan con cámara real.
LUZ_REGULAR_ENTRA = 35.0   # buena  -> regular (empieza a mejorar la imagen)
LUZ_REGULAR_SALE = 45.0   # regular -> buena
LUZ_BAJA_ENTRA = 16.0     # regular -> baja (pedir más luz)
LUZ_BAJA_SALE = 23.0      # baja    -> regular
MUY_OSCURO = 18.0         # por debajo de esto, aclarar con gamma; si no, con CLAHE

NIVELES = ("buena", "regular", "baja")

# Zona central-baja del cuadro donde se mide el brillo (fracciones del ancho/alto).
_ZONA = (0.25, 0.30, 0.75, 0.95)


def brillo_central(frame) -> float:
    """Luma media (0-255) de la zona central-baja del cuadro (torso y manos)."""
    alto, ancho = frame.shape[:2]
    fx0, fy0, fx1, fy1 = _ZONA
    return brillo(frame, (int(fx0 * ancho), int(fy0 * alto), int(fx1 * ancho), int(fy1 * alto)))


class MedidorLuz:
    """Decide, cuadro a cuadro y solo por el brillo, el nivel de luz y si mejorar.

    Uso en el bucle de cámara:
        frame2, nivel, pedir, estrategia = medidor.antes_de_detectar(frame)

    - "buena": luz suficiente; no se toca la imagen.
    - "regular": poca luz; se aclara la imagen automáticamente (y se sigue detectando).
    - "baja": muy poca luz; se pide más luz.
    El nivel es continuo: sube y baja con la luz, con histéresis para no parpadear, y
    se recupera solo (no depende de que haya manos).
    """

    def __init__(self):
        self._nivel = "buena"

    def _clasificar(self, b: float) -> str:
        nivel = self._nivel
        if nivel == "baja":
            if b > LUZ_BAJA_SALE:
                nivel = "regular"
        elif b < LUZ_BAJA_ENTRA:
            nivel = "baja"
        if nivel == "buena" and b < LUZ_REGULAR_ENTRA:
            nivel = "regular"
        elif nivel == "regular" and b > LUZ_REGULAR_SALE:
            nivel = "buena"
        return nivel

    def antes_de_detectar(self, frame):
        b = brillo_central(frame)
        self._nivel = nivel = self._clasificar(b)
        aplicar = nivel != "buena"
        estrategia = "denoise_gamma" if b < MUY_OSCURO else "denoise_clahe"
        salida = mejorar(frame, estrategia) if aplicar else frame
        return salida, nivel, nivel == "baja", (estrategia if aplicar else "ninguna")
