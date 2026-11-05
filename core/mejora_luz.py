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
