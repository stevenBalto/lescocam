"""Extrae las dos manos y el cuerpo de una muestra de ASL Citizen (problema 1, fase 3).

ASL Citizen (Microsoft Research; ~84 mil videos, ~2,7 mil señas ASL, 52 firmantes)
se usa para entrenar (fase 4) el modelo que convierte cada seña en un vector.

LICENCIA (obligatoria): solo investigación no comercial.
  * NO se distribuyen los datos ni sus modificaciones (los landmarks cuentan): nada de
    data/dictionary/asl_citizen/ entra a git (está en .gitignore; `git check-ignore` lo confirma).
  * No se contacta a ningún participante.
  * Al terminar la investigación se DESTRUYEN los datos personales: el zip, los videos
    temporales, la extracción y landmarks_v1.npz (borrar data/dictionary/asl_citizen/).

Estructura esperada del zip (se busca por nombre de archivo, no por ruta exacta):
    .../videos/<archivo>.mp4
    .../splits/train.csv, val.csv, test.csv   (columnas "Participant ID", "Video file",
                                                "Gloss", "ASL-LEX Code")

Qué hace:
  1. Lee los CSV y los videos DIRECTO del zip con zipfile (cada video se extrae a un archivo
     temporal propio del proceso, en el temp del sistema, y se borra al terminar; el zip no
     se descomprime entero). El zip no se modifica.
  2. Arma una MUESTRA ESTRATIFICADA reproducible (--n, --semilla): solo train y val (test
     queda reservado y no se toca), glosas con >= 2 videos, parejo entre glosas (cuota
     ~N/glosas, lo que sobra se reparte entre las glosas con más videos) y entre firmantes
     (dentro de cada glosa se prefiere al firmante menos usado hasta el momento). Se guarda
     el índice en data/dictionary/asl_citizen/muestra.json.
  3. Por video, el mismo camino que en vivo: frame espejado (cámara selfie) ->
     DetectorCuerpo(recorte=True) (el que usa la app; un detector nuevo por video) ->
     core.cuerpo.a_arrays -> data/dictionary/asl_citizen/extraccion/<id>.npz.
     REANUDABLE: si el .npz existe se salta. Un video roto se anota en errores.json y sigue.

Los videos los grabaron personas con su webcam/celular (distinta resolución y orientación):
OpenCV aplica la rotación guardada en el mp4 y, para ir más rápido, los cuadros se reducen a
--alto-max píxeles de alto (las coordenadas son normalizadas, no cambian de significado).

Uso:
    .venv/Scripts/python -m scripts.extraer_asl_citizen --procesos 4 --saltar-fotogramas 2
    .venv/Scripts/python -m scripts.extraer_asl_citizen --solo-muestra          # solo arma muestra.json
    .venv/Scripts/python -m scripts.extraer_asl_citizen --zip prueba.zip --carpeta salida/ --n 8
Luego: .venv/Scripts/python -m scripts.construir_landmarks_asl
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import random
import sys
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "dictionary" / "asl_citizen"
ZIP = CARPETA / "ASL_Citizen.zip"
TAMANO_ZIP = 45924134223
PARTICIONES = ("train", "val", "test")
USABLES = ("train", "val")     # test queda reservado


# ---------------------------------------------------------------- lectura del zip

def indexar_zip(zf: zipfile.ZipFile) -> tuple[dict, dict]:
    """(csv por partición -> nombre en el zip, video (nombre de archivo) -> nombre en el zip)."""
    csvs, videos = {}, {}
    for nombre in zf.namelist():
        base = nombre.rsplit("/", 1)[-1]
        if not base or nombre.endswith("/") or nombre.startswith("__MACOSX") or base.startswith("._"):
            continue
        bajo = base.lower()
        if bajo.endswith(".csv") and Path(bajo).stem in PARTICIONES:
            csvs[Path(bajo).stem] = nombre
        elif bajo.endswith(".mp4"):
            videos[base] = nombre
    return csvs, videos


def leer_particiones(zf: zipfile.ZipFile, csvs: dict) -> list[dict]:
    """Filas [{id, archivo, glosa, firmante, particion}] de los CSV de partición."""
    filas = []
    for part, nombre in csvs.items():
        texto = io.TextIOWrapper(zf.open(nombre), encoding="utf-8-sig", newline="")
        for r in csv.DictReader(texto):
            r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
            archivo = r.get("video file") or r.get("video_file") or r.get("video")
            glosa = r.get("gloss")
            firmante = r.get("participant id") or r.get("participant_id") or r.get("participant")
            if not (archivo and glosa):
                continue
            filas.append({"id": Path(archivo).stem, "archivo": archivo, "glosa": glosa,
                          "firmante": firmante or "?", "particion": part})
    return filas


def cuotas_por_glosa(tamanos: dict, n: int) -> dict:
    """Reparto parejo de n entre glosas con tope = videos disponibles (sobrante -> las que más tienen)."""
    cuota = {g: 0 for g in tamanos}
    activas = sorted(g for g, t in tamanos.items() if t > 0)
    restante = min(n, sum(tamanos.values()))
    while restante > 0 and activas:
        paso = max(1, restante // len(activas))
        for g in list(activas):
            dar = min(paso, tamanos[g] - cuota[g], restante)
            cuota[g] += dar
            restante -= dar
            if cuota[g] >= tamanos[g]:
                activas.remove(g)
            if restante == 0:
                break
    return cuota


def armar_muestra(filas: list[dict], n: int, semilla: int) -> list[dict]:
    """Muestra estratificada (glosa y firmante), solo train/val, glosas con >= 2 videos."""
    rng = random.Random(semilla)
    por_glosa = defaultdict(list)
    for f in filas:
        if f["particion"] in USABLES:
            por_glosa[f["glosa"]].append(f)
    por_glosa = {g: v for g, v in por_glosa.items() if len(v) >= 2}
    cuota = cuotas_por_glosa({g: len(v) for g, v in por_glosa.items()}, n)
    usos = Counter()                       # veces que ya se eligió a cada firmante
    elegidos = []
    for g in sorted(por_glosa, key=lambda g: (cuota[g], rng.random())):   # las de cuota chica primero
        candidatos = sorted(por_glosa[g], key=lambda f: f["id"])
        rng.shuffle(candidatos)
        for _ in range(cuota[g]):
            mejor = min(candidatos, key=lambda f: usos[f["firmante"]])    # el primero entre empates (ya mezclado)
            candidatos.remove(mejor)
            usos[mejor["firmante"]] += 1
            elegidos.append(mejor)
    elegidos.sort(key=lambda f: f["id"])
    return elegidos


# ---------------------------------------------------------------- trabajo por video

_ZF = None


def _pico_memoria_mb() -> float:
    """Pico de memoria residente del proceso (MB); 0 si no se puede medir."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            k32 = ctypes.WinDLL("kernel32")
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            info = ctypes.WinDLL("psapi").GetProcessMemoryInfo
            info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            info(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
            return pmc.PeakWorkingSetSize / 2 ** 20
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except Exception:
        return 0.0


def _iniciar(ruta_zip: str) -> None:
    """Cada proceso abre su propio ZipFile (no se comparte entre procesos)."""
    global _ZF
    _ZF = zipfile.ZipFile(ruta_zip)


def extraer_cuadros(ruta_video: str, saltar: int, alto_max: int, recorte: bool = True) -> tuple[dict, float]:
    """(arrays de core.cuerpo.a_arrays, fps original). Detector nuevo por video (arrastra el seguimiento)."""
    import cv2
    from core.cuerpo import DetectorCuerpo, a_arrays
    det = DetectorCuerpo(recorte=recorte)
    cap = cv2.VideoCapture(ruta_video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if not fps or fps != fps or fps > 240:
        fps = 30.0
    cuadros, i = [], 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            idx, i = i, i + 1
            if idx % saltar:
                continue
            alto = frame.shape[0]
            if alto_max and alto > alto_max:
                k = alto_max / alto
                frame = cv2.resize(frame, (max(1, int(frame.shape[1] * k)), alto_max), interpolation=cv2.INTER_AREA)
            cuadros.append(det.procesar(cv2.flip(frame, 1), idx / fps))
    finally:
        cap.release()
        det.cerrar()
    if not cuadros:
        raise ValueError("el video no tiene cuadros legibles")
    return a_arrays(cuadros), float(fps)


def _trabajo(args):
    f, nombre_zip, destino, saltar, alto_max, recorte = args
    destino = Path(destino)
    if destino.exists():
        return f["id"], 0.0, 0, 0.0, "cache"
    inicio = time.perf_counter()
    tmp_video = None
    try:
        fd, tmp_video = tempfile.mkstemp(suffix=".mp4", prefix=f"aslc_{os.getpid()}_")
        with os.fdopen(fd, "wb") as out, _ZF.open(nombre_zip) as src:
            while True:
                bloque = src.read(1 << 20)
                if not bloque:
                    break
                out.write(bloque)
        datos, fps = extraer_cuadros(tmp_video, saltar, alto_max, recorte)
        tmp = destino.with_suffix(".tmp.npz")
        np.savez_compressed(tmp, fps=np.float64(fps), saltar=np.int32(saltar), id=np.array(f["id"]),
                            glosa=np.array(f["glosa"]), firmante=np.array(f["firmante"]),
                            particion=np.array(f["particion"]), **datos)
        tmp.replace(destino)
        return f["id"], time.perf_counter() - inicio, len(datos["t"]), _pico_memoria_mb(), "ok"
    except Exception as e:   # un video corrupto no frena el resto
        return f["id"], time.perf_counter() - inicio, 0, _pico_memoria_mb(), f"error: {type(e).__name__}: {e}"
    finally:
        if tmp_video and os.path.exists(tmp_video):
            try:
                os.remove(tmp_video)
            except OSError:
                pass


def _fmt(seg: float) -> str:
    seg = int(seg)
    return f"{seg // 3600}h{seg % 3600 // 60:02d}m" if seg >= 3600 else f"{seg // 60}m{seg % 60:02d}s"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--zip", type=Path, default=ZIP)
    p.add_argument("--carpeta", type=Path, default=CARPETA, help="donde van muestra.json, errores.json y extraccion/")
    p.add_argument("--n", type=int, default=15000, help="videos de la muestra")
    p.add_argument("--semilla", type=int, default=7)
    p.add_argument("--procesos", type=int, default=4, help="ojo con la RAM: ver la recomendación en la entrega")
    p.add_argument("--saltar-fotogramas", type=int, default=1, dest="saltar",
                   help="procesar 1 de cada N cuadros (2 = 15 fps)")
    p.add_argument("--alto-max", type=int, default=480, help="reduce los cuadros a este alto (0 = sin reducir)")
    p.add_argument("--sin-recorte", action="store_true", help="DetectorCuerpo() sin recorte (no recomendado)")
    p.add_argument("--rehacer-muestra", action="store_true", help="ignorar muestra.json existente")
    p.add_argument("--solo-muestra", action="store_true", help="solo arma muestra.json y sale")
    p.add_argument("--max", type=int, default=0, help="procesar como mucho N videos de la muestra")
    a = p.parse_args(argv)
    if a.saltar < 1:
        p.error("--saltar-fotogramas debe ser >= 1")

    if not zipfile.is_zipfile(a.zip):
        print(f"{a.zip} no es un zip completo todavía (¿sigue la descarga?).", file=sys.stderr)
        return 2
    if a.zip == ZIP and a.zip.stat().st_size != TAMANO_ZIP:
        print(f"Aviso: el zip mide {a.zip.stat().st_size} bytes y se esperaban {TAMANO_ZIP}.", file=sys.stderr)

    a.carpeta.mkdir(parents=True, exist_ok=True)
    ruta_muestra, ruta_err, salida = a.carpeta / "muestra.json", a.carpeta / "errores.json", a.carpeta / "extraccion"
    salida.mkdir(exist_ok=True)

    with zipfile.ZipFile(a.zip) as zf:
        csvs, videos = indexar_zip(zf)
        if not videos or not any(k in csvs for k in USABLES):
            print(f"Estructura inesperada: {len(videos)} mp4, CSV {sorted(csvs)}", file=sys.stderr)
            return 2
        if ruta_muestra.exists() and not a.rehacer_muestra:
            muestra = json.loads(ruta_muestra.read_text(encoding="utf-8"))["videos"]
            print(f"Muestra existente: {len(muestra)} videos ({ruta_muestra})")
        else:
            filas = [f for f in leer_particiones(zf, csvs) if f["archivo"] in videos]
            muestra = armar_muestra(filas, a.n, a.semilla)
            ruta_muestra.write_text(json.dumps({
                "n": len(muestra), "semilla": a.semilla, "particiones": list(USABLES),
                "glosas": len({f["glosa"] for f in muestra}), "firmantes": len({f["firmante"] for f in muestra}),
                "videos": muestra}, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"Muestra: {len(muestra)} videos, {len({f['glosa'] for f in muestra})} glosas, "
                  f"{len({f['firmante'] for f in muestra})} firmantes -> {ruta_muestra}")
    if a.solo_muestra:
        return 0
    if a.max:
        muestra = muestra[:a.max]

    trabajos = [(f, videos[f["archivo"]], str(salida / f"{f['id']}.npz"), a.saltar, a.alto_max, not a.sin_recorte)
                for f in muestra if f["archivo"] in videos]
    pendientes = sum(not Path(t[2]).exists() for t in trabajos)
    print(f"{pendientes} por extraer ({len(trabajos) - pendientes} ya hechos), {a.procesos} procesos, "
          f"1 de cada {a.saltar} cuadros", flush=True)

    errores = json.loads(ruta_err.read_text(encoding="utf-8")) if ruta_err.exists() else {}
    hechos, nuevos, seg_total, frames, pico = 0, 0, 0.0, 0, 0.0
    inicio = time.perf_counter()
    with Pool(a.procesos, initializer=_iniciar, initargs=(str(a.zip),)) as pool:
        for vid, seg, n, mem, estado in pool.imap_unordered(_trabajo, trabajos, chunksize=1):
            hechos += 1
            if estado == "ok":
                nuevos += 1
                seg_total += seg
                frames += n
                errores.pop(vid, None)
            elif estado != "cache":
                errores[vid] = estado
                ruta_err.write_text(json.dumps(errores, ensure_ascii=False, indent=1), encoding="utf-8")
            pico = max(pico, mem)
            if estado != "cache" and (nuevos % 25 == 0 or estado != "ok" or hechos == len(trabajos)):
                reloj = time.perf_counter() - inicio
                por_video = reloj / max(nuevos, 1)
                resto = (pendientes - nuevos) * por_video
                print(f"[{hechos}/{len(trabajos)}] {vid}: {estado} | {por_video:.2f} s/video de reloj, "
                      f"{seg_total / max(nuevos, 1):.1f} s/video por proceso, pico {pico:.0f} MB/proceso, "
                      f"faltan ~{_fmt(max(resto, 0))}", flush=True)
    total = time.perf_counter() - inicio
    ruta_err.write_text(json.dumps(errores, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nListo: {nuevos} videos nuevos en {_fmt(total)} ({total / max(nuevos, 1):.2f} s/video de reloj, "
          f"{1000 * seg_total / max(frames, 1):.1f} ms/cuadro por proceso), pico {pico:.0f} MB/proceso, "
          f"{len(errores)} con error (errores.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
