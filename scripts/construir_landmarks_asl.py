"""Arma landmarks_v1.npz, el archivo FINAL "listo para entrenar" de ASL Citizen (insumo de la fase 4).

Lee los .npz por video de data/dictionary/asl_citizen/extraccion/ (los deja
scripts/extraer_asl_citizen.py, formato v1 de core/cuerpo.a_arrays) y los junta en
data/dictionary/asl_citizen/landmarks_v1.npz con los cuadros de todos los videos uno tras
otro (índice de offsets para ubicar cada video sin recorrer todo):

    manos   (T, 2, 21, 3) float16   x, y normalizadas (0-1) y z relativa; NaN = no hay mano.
    lado    (T, 2)        int8      0 = Left, 1 = Right, -1 = no hay
    score   (T, 2)        float16   confianza de la mano (0-1)
    pose    (T, 33, 4)    float16   x, y, z, visibilidad; NaN = sin persona
    t       (T,)          float32   segundos desde el inicio del video
    offsets (V + 1,)      int64     los cuadros del video i son [offsets[i], offsets[i+1])
    ids, glosas, firmantes, particiones (V,) texto;  frame (V, 2) int32 (ancho, alto) en px
    fps (V,) float32 del video original;  saltar (V,) int32 (1 = todos los cuadros, 2 = 15 fps)
    resumen (JSON en texto)

float16 guarda ~3 cifras decimales: entre 0,5 y 1 el paso es 0,0005 (menos de medio pixel en
640 de ancho) y mucho más fino cerca de 0; es menos que el ruido de MediaPipe. t va en float32
(error < 1 microsegundo). score va en float16; lado, frame y los metadatos conservan su tipo.

Uso:
    .venv/Scripts/python -m scripts.construir_landmarks_asl
    .venv/Scripts/python -m scripts.construir_landmarks_asl --sin-comprimir    # más rápido de leer, pesa más

Lectura:
    from scripts.construir_landmarks_asl import cargar
    d = cargar()                  # objeto Landmarks
    d.video(i)                    # arrays de un video, aptos para core.cuerpo.desde_arrays
    d.glosas[i], d.particiones[i], d.resumen

Licencia: solo investigación no comercial; este archivo NO se distribuye (ver
extraer_asl_citizen.py) y se destruye al terminar la investigación.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "dictionary" / "asl_citizen"
SALIDA = CARPETA / "landmarks_v1.npz"
CAMPOS_CUADRO = ("t", "manos", "lado", "score", "pose")
CAMPOS_META = ("ids", "glosas", "firmantes", "particiones", "frame", "fps", "saltar")
TIPOS = {"manos": np.float16, "lado": np.int8, "score": np.float16, "pose": np.float16, "t": np.float32}


def construir(carpeta: Path = CARPETA, salida: Path | None = None, comprimir: bool = True) -> dict:
    """Junta los .npz de carpeta/extraccion en `salida`; devuelve el resumen."""
    salida = salida or carpeta / "landmarks_v1.npz"
    archivos = [f for f in sorted((carpeta / "extraccion").glob("*.npz")) if not f.name.endswith(".tmp.npz")]
    if not archivos:
        raise SystemExit(f"No hay .npz en {carpeta / 'extraccion'}")
    partes = {k: [] for k in CAMPOS_CUADRO}
    meta = {k: [] for k in CAMPOS_META}
    largos, omitidos = [], []
    for f in archivos:
        try:
            with np.load(f) as d:
                n = len(d["t"])
                if n == 0:
                    raise ValueError("sin cuadros")
                cuadros = {k: np.asarray(d[k]).astype(TIPOS[k]) for k in CAMPOS_CUADRO}
                fila = {"ids": str(d["id"]), "glosas": str(d["glosa"]), "firmantes": str(d["firmante"]),
                        "particiones": str(d["particion"]), "frame": np.asarray(d["frame"], dtype=np.int32),
                        "fps": float(d["fps"]), "saltar": int(d["saltar"]) if "saltar" in d.files else 1}
        except Exception as e:      # archivo dañado: se anota y se sigue
            omitidos.append(f"{f.name}: {e}")
            continue
        for k in CAMPOS_CUADRO:
            partes[k].append(cuadros[k])
        for k in CAMPOS_META:
            meta[k].append(fila[k])
        largos.append(n)
    if not largos:
        raise SystemExit("Ningún .npz válido")
    offsets = np.concatenate([[0], np.cumsum(largos)]).astype(np.int64)
    arrays = {k: np.concatenate(v) for k, v in partes.items()}
    T = int(offsets[-1])
    con_cuerpo = ~np.isnan(arrays["pose"][:, 0, 0])
    existe = ~np.isnan(arrays["manos"][:, :, 0, 0])            # (T, 2)
    resumen = {
        "videos": len(largos), "glosas": len(set(meta["glosas"])), "firmantes": len(set(meta["firmantes"])),
        "fotogramas": T, "fotogramas_por_video_medio": round(T / len(largos), 1),
        "pct_con_cuerpo": round(100 * float(con_cuerpo.mean()), 2),
        "pct_con_alguna_mano": round(100 * float(existe.any(1).mean()), 2),
        "pct_con_dos_manos": round(100 * float(existe.all(1).mean()), 2),
        "particiones": {p: meta["particiones"].count(p) for p in sorted(set(meta["particiones"]))},
        "formato": "v1 (core/cuerpo.a_arrays); manos/pose/score en float16, t en float32",
        "omitidos": omitidos,
    }
    salida.parent.mkdir(parents=True, exist_ok=True)
    tmp = salida.with_suffix(".tmp.npz")
    (np.savez_compressed if comprimir else np.savez)(
        tmp, **arrays, offsets=offsets,
        ids=np.array(meta["ids"]), glosas=np.array(meta["glosas"]), firmantes=np.array(meta["firmantes"]),
        particiones=np.array(meta["particiones"]), frame=np.stack(meta["frame"]),
        fps=np.array(meta["fps"], dtype=np.float32), saltar=np.array(meta["saltar"], dtype=np.int32),
        resumen=np.array(json.dumps(resumen, ensure_ascii=False)))
    tmp.replace(salida)
    resumen["tamano_mb"] = round(salida.stat().st_size / 2 ** 20, 2)
    return resumen


class Landmarks:
    """Acceso al archivo construido: atributos con los metadatos y video(i) con los cuadros de un video."""

    def __init__(self, datos):
        self._d = datos
        self.offsets = np.asarray(datos["offsets"])
        for k in CAMPOS_META:
            setattr(self, k, np.asarray(datos[k]))
        self.resumen = json.loads(str(np.asarray(datos["resumen"])))

    def __len__(self) -> int:
        return len(self.offsets) - 1

    def video(self, i: int) -> dict:
        """Arrays del video i en el formato de core.cuerpo.a_arrays, listos para desde_arrays."""
        a, b = int(self.offsets[i]), int(self.offsets[i + 1])
        s = {k: np.asarray(self._d[k][a:b]) for k in CAMPOS_CUADRO}
        s["t"] = s["t"].astype(np.float64)
        for k in ("manos", "score", "pose"):
            s[k] = s[k].astype(np.float32)
        s["frame"] = self.frame[i]
        return s

    def indices(self, particion: str | None = None, glosa: str | None = None) -> np.ndarray:
        m = np.ones(len(self), dtype=bool)
        if particion:
            m &= self.particiones == particion
        if glosa:
            m &= self.glosas == glosa
        return np.nonzero(m)[0]


def cargar(ruta: Path = SALIDA) -> Landmarks:
    """Abre landmarks_v1.npz y lo lee entero a la RAM una vez (~0,6 GB con 15 mil videos).
    No hay mmap: numpy lo ignora en .npz y releería todo el array en cada video."""
    with np.load(ruta) as d:
        return Landmarks({k: d[k] for k in d.files})


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--carpeta", type=Path, default=CARPETA)
    p.add_argument("--salida", type=Path, default=None)
    p.add_argument("--sin-comprimir", action="store_true")
    a = p.parse_args(argv)
    inicio = time.perf_counter()
    r = construir(a.carpeta, a.salida, not a.sin_comprimir)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"{time.perf_counter() - inicio:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
