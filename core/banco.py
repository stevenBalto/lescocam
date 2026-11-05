"""Banco de prueba de palabras (problema 1, fase 1): tomas de webcam SOLO para medir.

Cada toma es un .npz con los landmarks crudos de DetectorCuerpo (formato v1 de
core/cuerpo.a_arrays: manos, lado, score, pose, t, frame) más metadatos:

    etiqueta   palabra que se imitó (tal como en el catálogo de CENAREC)
    persona    quién la hizo (minúsculas, sin espacios)
    camara     con qué cámara ("iphone13", "hp-windows", "hp-linux", "huawei"...); "desconocida" si no se dijo
    luz        "buena" | "media" | "baja"
    distancia  "cerca" | "media" | "lejos"
    angulo     "frente" | "lado"
    fecha      ISO

Ubicación: data/banco/<persona>/<NN>_<ETIQUETA>_<k>.npz  (NN = orden de la palabra en la lista de
esa persona, data/reference/banco/<nombre>.txt; k = número de toma). Cada toma pesa ~100 KB: el banco
SÍ se versiona (el límite del hook es 5 MB por archivo).

Reparto (85 palabras iniciales): cada persona graba 30 = 12 del NÚCLEO común (las graban las 4, para
comparar firmantes con las mismas palabras) + 18 propias. Cada lista va en 3 tandas de 10 (4 del núcleo
+ 6 propias), y con --plan cada tanda cambia luz, distancia y ángulo (ver PLAN).

NUNCA se usan como plantillas ni para entrenar: el banco existe para medir.
Se guardan landmarks, no video: no queda la cara de nadie.
"""
from __future__ import annotations

import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from core.cuerpo import CuadroCuerpo, a_arrays, desde_arrays

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "banco"
LISTAS = RAIZ / "data" / "reference" / "banco"
REGISTROS = RAIZ / "hiloEquipo" / "banco"
PERSONAS = ("christian", "steven", "reyman", "johan")   # un archivo de LISTAS por nombre de pila
TOMAS_POR_PALABRA = 2
PALABRAS_POR_TANDA = 10

# Condiciones por tanda de 10 palabras (luz, distancia, ángulo) y qué hacer en cada una.
PLAN = (
    (("buena", "media", "frente"), "luz normal, a ~1.5 m, de frente"),
    (("media", "lejos", "frente"), "luz normal, aléjate (se ven manos y cintura), de frente"),
    (("baja", "media", "lado"), "luz baja (atenúa o apaga una luz), distancia normal, cuerpo girado ~30 grados"),
)

LUCES = ("buena", "media", "baja")
DISTANCIAS = ("cerca", "media", "lejos")
ANGULOS = ("frente", "lado")


def leer_lista(ruta: Path) -> list[str]:
    return [l.strip() for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def lista_de(persona: str, carpeta: Path = LISTAS) -> Path:
    """Archivo de palabras de una persona: el que lleva su nombre de pila ('Steven Baltodano' -> steven.txt)."""
    nombre = limpiar_persona(persona)
    for p in PERSONAS:
        if nombre == p or nombre.startswith(p + "-") or nombre.startswith(p + "_"):
            return carpeta / f"{p}.txt"
    raise ValueError(f"No hay lista del banco para '{persona}'. Nombres válidos: {', '.join(PERSONAS)}")


def plan_de(indice: int) -> tuple[tuple[str, str, str], str, int]:
    """((luz, distancia, angulo), instrucción, número de tanda 1..3) de la palabra `indice` (desde 0) de la lista."""
    t = min(indice // PALABRAS_POR_TANDA, len(PLAN) - 1)
    return PLAN[t][0], PLAN[t][1], t + 1


def limpiar_persona(nombre: str) -> str:
    """'Christian Paniagua' -> 'christian-paniagua' (solo letras, números, - y _)."""
    sin = unicodedata.normalize("NFKD", nombre.strip().lower()).encode("ascii", "ignore").decode()
    sin = sin.replace(" ", "-")
    return "".join(c for c in sin if c.isalnum() or c in "-_") or "anonimo"


def sin_tildes(texto: str) -> str:
    """Para dibujar con cv2.putText (no pinta Ñ ni tildes)."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def _nombre(orden: int, etiqueta: str, toma: int) -> str:
    seguro = "".join(c if c.isalnum() else "_" for c in sin_tildes(etiqueta)).strip("_")
    return f"{orden:02d}_{seguro}_{toma}.npz"


def carpeta_persona(persona: str, raiz: Path = CARPETA) -> Path:
    return raiz / limpiar_persona(persona)


def contar_tomas(persona: str, orden: int, raiz: Path = CARPETA) -> int:
    carpeta = carpeta_persona(persona, raiz)
    return len(list(carpeta.glob(f"{orden:02d}_*.npz"))) if carpeta.exists() else 0


def guardar_toma(cuadros: list[CuadroCuerpo], etiqueta: str, orden: int, persona: str, luz: str, distancia: str,
                 angulo: str, raiz: Path = CARPETA, camara: str = "desconocida") -> Path:
    """Guarda una toma. Devuelve la ruta. Nunca pisa una toma existente."""
    if luz not in LUCES or distancia not in DISTANCIAS or angulo not in ANGULOS:
        raise ValueError(f"Condición inválida: {luz}/{distancia}/{angulo}")
    if not cuadros:
        raise ValueError("La toma no tiene cuadros")
    carpeta = carpeta_persona(persona, raiz)
    carpeta.mkdir(parents=True, exist_ok=True)
    k = contar_tomas(persona, orden, raiz) + 1
    ruta = carpeta / _nombre(orden, etiqueta, k)
    while ruta.exists():
        k += 1
        ruta = carpeta / _nombre(orden, etiqueta, k)
    datos = a_arrays(cuadros)
    datos.update(etiqueta=np.array(etiqueta), persona=np.array(limpiar_persona(persona)), camara=np.array(limpiar_persona(camara)),
                 luz=np.array(luz),
                 distancia=np.array(distancia), angulo=np.array(angulo),
                 fecha=np.array(datetime.now().isoformat(timespec="seconds")))
    tmp = ruta.with_name(ruta.stem + ".tmp.npz")
    np.savez_compressed(tmp, **datos)
    tmp.replace(ruta)
    return ruta


class Toma:
    """Una toma cargada: cuadros de cuerpo + metadatos."""

    def __init__(self, ruta: Path):
        datos = np.load(ruta, allow_pickle=False)
        self.ruta = Path(ruta)
        self.cuadros = desde_arrays(datos)
        self.etiqueta = str(datos["etiqueta"])
        self.persona = str(datos["persona"])
        self.camara = str(datos["camara"]) if "camara" in datos.files else "desconocida"
        self.luz = str(datos["luz"])
        self.distancia = str(datos["distancia"])
        self.angulo = str(datos["angulo"])
        self.fecha = str(datos["fecha"])


def cargar_tomas(raiz: Path = CARPETA, persona: Optional[str] = None) -> list[Toma]:
    """Todas las tomas del banco (o de una persona), en orden estable."""
    if not raiz.exists():
        return []
    carpetas = [carpeta_persona(persona, raiz)] if persona else sorted(p for p in raiz.iterdir() if p.is_dir())
    return [Toma(r) for c in carpetas if c.exists() for r in sorted(c.glob("*.npz"))]


def cobertura_cuerpo(cuadros: list[CuadroCuerpo]) -> float:
    """Fracción de cuadros donde se ve el cuerpo (hay pose). Sirve para avisar de mal encuadre."""
    if not cuadros:
        return 0.0
    return sum(1 for c in cuadros if c.pose is not None) / len(cuadros)


def cobertura_manos(cuadros: list[CuadroCuerpo]) -> float:
    """Fracción de cuadros donde se ve al menos una mano. Si es ~0, las manos no entraron en cuadro."""
    if not cuadros:
        return 0.0
    return sum(1 for c in cuadros if c.manos) / len(cuadros)


def asignar_camara(persona: str, camara: str, raiz: Path = CARPETA) -> int:
    """Pone `camara` en las tomas de `persona` que no la tienen o dicen 'desconocida'. Devuelve cuántas cambió."""
    cambiadas = 0
    for ruta in sorted(carpeta_persona(persona, raiz).glob("*.npz")):
        datos = dict(np.load(ruta, allow_pickle=False))
        if "camara" in datos and str(datos["camara"]) != "desconocida":
            continue
        datos["camara"] = np.array(limpiar_persona(camara))
        tmp = ruta.with_name(ruta.stem + ".tmp.npz")
        np.savez_compressed(tmp, **datos)
        tmp.replace(ruta)
        cambiadas += 1
    return cambiadas
