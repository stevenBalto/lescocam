"""Descriptores de ASL Citizen para entrenar el modelo de señas (problema 1, fase 4).

Cada video de landmarks_v1.npz (scripts/construir_landmarks_asl.py) pasa por el MISMO camino
que CENAREC, el banco y la cámara en vivo:

    desde_arrays -> cuadro_palabra -> segmentar (Segmentador) -> la seña más larga
    -> descriptor con PESOS_CRUDOS (los mismos de las plantillas de senas.db): (MUESTRAS, COLUMNAS)

Con la mano dominante dudosa (seña de dos manos) se guardan las dos variantes (espejo y no):
las dos son la misma seña y el modelo aprende a juntarlas. Si el Segmentador no encuentra
seña (el firmante no bajó las manos, o duró > DURACION_MAX), se describe el tramo con las
manos fuera de reposo; si tampoco hay, el video se descarta y se cuenta.

Salida: data/dictionary/asl_citizen/descriptores_v3.npz (ignorado por git; licencia: no se
distribuye y se borra al terminar la investigación, ver extraer_asl_citizen.py)
    x (N, MUESTRAS, COLUMNAS) float32, video (N,) índice en landmarks_v1, espejo (N,) bool,
    glosas, firmantes, particiones (N,), duracion (N,) s, resumen (JSON)

Uso:
    .venv/Scripts/python -m scripts.descriptores_asl [--procesos 4]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from core import palabras as P
from core.cuerpo import desde_arrays
from scripts.construir_landmarks_asl import CARPETA, SALIDA as LANDMARKS, cargar
from scripts.construir_palabras import PESOS_CRUDOS
from scripts.entrada_modelo import entradas

SALIDA = CARPETA / "descriptores_v3.npz"
SALIDA_PUNTOS = CARPETA / "descriptores_v3p.npz"   # --con-puntos: + 21 puntos de cada mano (209 columnas)

_LM = None
_PUNTOS = False


def sena_de(cuadros: list, tiempos: list) -> tuple[list | None, str]:
    """(la seña a describir, cómo se obtuvo: 'segmentador' | 'fuera_reposo' | 'nada')."""
    senas = P.segmentar(cuadros, tiempos)
    if senas:
        return max(senas, key=lambda s: s[-1].t - s[0].t), "segmentador"
    fuera = [c for c in cuadros if c is not None and not P.en_reposo(c)]
    if len(fuera) >= 2 and fuera[-1].t - fuera[0].t >= P.DURACION_MIN:
        return fuera, "fuera_reposo"
    return None, "nada"


def describir(cuadros: list, tiempos: list, con_puntos: bool = False) -> tuple[list, str, float]:
    """([(espejo, entrada del modelo)], cómo, duración) de un video ya en CuadroPalabra."""
    sena, como = sena_de(cuadros, tiempos)
    if sena is None:
        return [], como, 0.0
    salida = entradas(sena, "auto", con_puntos)
    return salida, (como if salida else "nada"), P.duracion(sena)


def _iniciar(ruta: str, con_puntos: bool = False) -> None:
    global _LM, _PUNTOS
    _LM, _PUNTOS = cargar(Path(ruta)), con_puntos


def _trabajo(i: int):
    cuerpo = desde_arrays(_LM.video(i))
    cuadros = [P.cuadro_palabra(c) for c in cuerpo]
    variantes, como, dur = describir(cuadros, [c.t for c in cuerpo], _PUNTOS)
    return i, variantes, como, dur


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--landmarks", type=Path, default=LANDMARKS)
    p.add_argument("--salida", type=Path, default=None, help=f"por defecto {SALIDA.name} o, con puntos, {SALIDA_PUNTOS.name}")
    p.add_argument("--con-puntos", action="store_true", help="agregar los 21 puntos de cada mano (209 columnas)")
    p.add_argument("--procesos", type=int, default=4)
    p.add_argument("--max", type=int, default=0, help="solo los primeros N videos (prueba)")
    a = p.parse_args(argv)
    a.salida = a.salida or (SALIDA_PUNTOS if a.con_puntos else SALIDA)

    lm = cargar(a.landmarks)
    n = min(len(lm), a.max) if a.max else len(lm)
    inicio = time.perf_counter()
    filas, comos, sin = [], Counter(), 0
    with Pool(a.procesos, initializer=_iniciar, initargs=(str(a.landmarks), a.con_puntos)) as pool:
        for k, (i, variantes, como, dur) in enumerate(pool.imap_unordered(_trabajo, range(n), chunksize=16), 1):
            comos[como] += 1
            for e, d in variantes:
                filas.append((i, e, d, dur))
            if k % 1000 == 0:
                print(f"[{k}/{n}] {time.perf_counter() - inicio:.0f} s", flush=True)
    filas.sort(key=lambda f: (f[0], f[1]))
    idx = np.array([f[0] for f in filas], dtype=np.int32)
    resumen = {"videos": n, "descriptores": len(filas), "como": dict(comos),
               "videos_con_descriptor": int(len(set(idx.tolist()))),
               "muestras": P.MUESTRAS, "columnas": int(filas[0][2].shape[1]) if filas else 0, "con_puntos": a.con_puntos, "version_descriptor": P.VERSION_DESCRIPTOR,
               "pesos": list(PESOS_CRUDOS)}
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    tmp = a.salida.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, x=np.stack([f[2] for f in filas]), video=idx,
                        espejo=np.array([f[1] for f in filas], dtype=bool),
                        duracion=np.array([f[3] for f in filas], dtype=np.float32),
                        glosas=lm.glosas[idx], firmantes=lm.firmantes[idx], particiones=lm.particiones[idx],
                        resumen=np.array(json.dumps(resumen, ensure_ascii=False)))
    tmp.replace(a.salida)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
    print(f"{time.perf_counter() - inicio:.0f} s -> {a.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
