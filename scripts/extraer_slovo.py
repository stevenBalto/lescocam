"""Extrae las dos manos y el cuerpo de Slovo (lengua de señas rusa) — problema 1, fase 5.

Slovo (SberDevices, 2023): 20 400 videos, 1000 señas + "no_event", 194 personas grabadas con su
celular o laptop. Se usa para entrenar el modelo del PRODUCTO (el de ASL Citizen es solo de
laboratorio): lo que hace bueno al modelo es la variedad de personas.

LICENCIA (aprobada por Christian, 2026-11-13): licencia pública propia, reelaboración de CC BY-SA 4.0
(https://github.com/ai-forever/slovo, license/en_us.pdf). Permite uso comercial. Obligaciones:
  * Dar el crédito (autores, aviso de la licencia, enlace) donde se use.
  * Si se distribuye material adaptado (a lo conservador, el modelo entrenado), va con una licencia
    con los mismos elementos o compatible con BY-SA.
  * Los datos (zip, videos, landmarks) NO entran a git: todo data/dictionary/ está en .gitignore.

Se usa slovo_full360.zip (videos ORIGINALES reducidos a 360 px, con reposo antes y después de la
seña; los "recortados" empiezan ya en la seña y el Segmentador no los cortaría). Estructura:
    annotations.tsv   attachment_id, text, user_id, height, width, length, train, begin, end
    train/<id>.mp4, test/<id>.mp4

Por video, el mismo camino que ASL Citizen (scripts/extraer_asl_citizen._trabajo): frame espejado ->
DetectorCuerpo(recorte=True) -> core.cuerpo.a_arrays -> data/dictionary/slovo/extraccion/<id>.npz
(glosa = text, firmante = user_id, particion = train/test). Reanudable; errores en errores.json.
Se extraen las 20 400 (train y test): el modelo se mide en el banco LESCO, no en Slovo.

Uso:
    .venv/Scripts/python -m scripts.extraer_slovo --procesos 4 --saltar-fotogramas 2
    .venv/Scripts/python -m scripts.extraer_slovo --max 20          # prueba
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import zipfile
from multiprocessing import Pool
from pathlib import Path

from scripts import extraer_asl_citizen as A

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "dictionary" / "slovo"
ZIP = CARPETA / "slovo_full360.zip"
TAMANO_ZIP = 12935161603


def leer_anotaciones(texto: str, videos: dict) -> list[dict]:
    """Filas [{id, archivo, glosa, firmante, particion, inicio, fin}] de annotations.tsv con video en el zip."""
    filas = []
    for r in csv.DictReader(io.StringIO(texto), delimiter="\t"):
        vid = (r.get("attachment_id") or "").strip()
        archivo = f"{vid}.mp4"
        if not vid or archivo not in videos:
            continue
        filas.append({"id": vid, "archivo": archivo, "glosa": (r.get("text") or "").strip(),
                      "firmante": (r.get("user_id") or "?").strip(),
                      "particion": "train" if (r.get("train") or "").strip() == "True" else "test",
                      "inicio": int(float(r.get("begin") or 0)), "fin": int(float(r.get("end") or 0))})
    filas.sort(key=lambda f: f["id"])
    return filas


def indexar(zf: zipfile.ZipFile) -> tuple[str | None, dict]:
    """(nombre de annotations.tsv en el zip, archivo .mp4 -> nombre en el zip)."""
    tsv, videos = None, {}
    for nombre in zf.namelist():
        base = nombre.rsplit("/", 1)[-1]
        if base == "annotations.tsv":
            tsv = nombre
        elif base.lower().endswith(".mp4") and not base.startswith("._"):
            videos[base] = nombre
    return tsv, videos


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--zip", type=Path, default=ZIP)
    p.add_argument("--carpeta", type=Path, default=CARPETA, help="donde van indice.json, errores.json y extraccion/")
    p.add_argument("--procesos", type=int, default=4)
    p.add_argument("--saltar-fotogramas", type=int, default=2, dest="saltar", help="1 de cada N cuadros (2 = 15 fps)")
    p.add_argument("--alto-max", type=int, default=480, help="reduce los cuadros a este alto (0 = sin reducir)")
    p.add_argument("--max", type=int, default=0, help="procesar como mucho N videos (prueba)")
    a = p.parse_args(argv)
    if a.saltar < 1:
        p.error("--saltar-fotogramas debe ser >= 1")
    if not zipfile.is_zipfile(a.zip):
        print(f"{a.zip} no es un zip completo.", file=sys.stderr)
        return 2
    if a.zip == ZIP and a.zip.stat().st_size != TAMANO_ZIP:
        print(f"Aviso: el zip mide {a.zip.stat().st_size} bytes y se esperaban {TAMANO_ZIP}.", file=sys.stderr)

    a.carpeta.mkdir(parents=True, exist_ok=True)
    ruta_err, salida = a.carpeta / "errores.json", a.carpeta / "extraccion"
    salida.mkdir(exist_ok=True)
    with zipfile.ZipFile(a.zip) as zf:
        tsv, videos = indexar(zf)
        if tsv is None or not videos:
            print(f"Estructura inesperada: {len(videos)} mp4, annotations.tsv {'sí' if tsv else 'no'}", file=sys.stderr)
            return 2
        filas = leer_anotaciones(zf.read(tsv).decode("utf-8-sig"), videos)
    (a.carpeta / "indice.json").write_text(json.dumps({
        "n": len(filas), "glosas": len({f["glosa"] for f in filas}),
        "firmantes": len({f["firmante"] for f in filas}), "videos": filas}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"Slovo: {len(filas)} videos, {len({f['glosa'] for f in filas})} glosas, "
          f"{len({f['firmante'] for f in filas})} personas")
    if a.max:
        filas = filas[:a.max]

    trabajos = [(f, videos[f["archivo"]], str(salida / f"{f['id']}.npz"), a.saltar, a.alto_max, True) for f in filas]
    pendientes = sum(not Path(t[2]).exists() for t in trabajos)
    print(f"{pendientes} por extraer ({len(trabajos) - pendientes} ya hechos), {a.procesos} procesos, "
          f"1 de cada {a.saltar} cuadros", flush=True)
    errores = json.loads(ruta_err.read_text(encoding="utf-8")) if ruta_err.exists() else {}
    hechos = nuevos = 0
    inicio = time.perf_counter()
    with Pool(a.procesos, initializer=A._iniciar, initargs=(str(a.zip),)) as pool:
        for vid, _, _, mem, estado in pool.imap_unordered(A._trabajo, trabajos, chunksize=1):
            hechos += 1
            if estado == "ok":
                nuevos += 1
                errores.pop(vid, None)
            elif estado != "cache":
                errores[vid] = estado
                ruta_err.write_text(json.dumps(errores, ensure_ascii=False, indent=1), encoding="utf-8")
            if estado != "cache" and (nuevos % 100 == 0 or estado != "ok" or hechos == len(trabajos)):
                reloj = time.perf_counter() - inicio
                resto = (pendientes - nuevos) * reloj / max(nuevos, 1)
                print(f"[{hechos}/{len(trabajos)}] {estado} | {reloj / max(nuevos, 1):.2f} s/video, "
                      f"pico {mem:.0f} MB, faltan ~{A._fmt(max(resto, 0))}", flush=True)
    ruta_err.write_text(json.dumps(errores, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nListo: {nuevos} nuevos en {A._fmt(time.perf_counter() - inicio)}, {len(errores)} con error (errores.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
