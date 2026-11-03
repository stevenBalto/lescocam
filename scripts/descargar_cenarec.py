"""Descarga los videos del Diccionario LESCO de CENAREC.

Uso autorizado por CENAREC para LESCOCam (acuerdo en reunión; ver hiloBackend/).
Los videos NO se versionan ni se redistribuyen: quedan en data/dictionary/cenarec/
(ignorado por git). Solo se usan para extraer los puntos de las manos.

Va de a un pedido por vez con pausa, para no cargar el servidor, y retoma donde
quedó si se corta (salta los videos ya descargados).

Uso:
    .venv/bin/python -m scripts.descargar_cenarec            # todo
    .venv/bin/python -m scripts.descargar_cenarec --max 20   # prueba con 20
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://lesco.cenarec.go.cr/"
LISTA = BASE + "DiccLESCO.php"
AGENTE = "LESCOCam-proyecto-academico (uso autorizado por CENAREC)"
CARPETA = Path("data/dictionary/cenarec")
CATALOGO = CARPETA / "catalogo.json"
PAUSA = 1.0  # segundos entre pedidos

RE_PALABRA = re.compile(r'href="DiccLESCO\.php\?idw=(\d+)" class="word">([^<]+)<')
RE_VIDEO = re.compile(r'<source[^>]*type="video/mp4"[^>]*src="([^"]+)"')


def pedir(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def nombre_archivo(idw: int, etiqueta: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ_-]+", "_", etiqueta).strip("_")
    return f"{idw:05d}_{limpio}.mp4"


def leer_catalogo() -> dict:
    if CATALOGO.exists():
        return json.loads(CATALOGO.read_text(encoding="utf-8"))
    return {"fuente": LISTA, "palabras": {}}


def guardar_catalogo(cat: dict) -> None:
    tmp = CATALOGO.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(CATALOGO)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--max", type=int, default=0, help="descargar como mucho N videos nuevos (0 = todos)")
    a = p.parse_args(argv)

    (CARPETA / "videos").mkdir(parents=True, exist_ok=True)
    pagina = pedir(LISTA).decode("utf-8", errors="replace")
    palabras = {}
    for idw, etiqueta in RE_PALABRA.findall(pagina):
        palabras.setdefault(int(idw), html.unescape(etiqueta).strip())
    print(f"{len(palabras)} palabras en el diccionario")

    cat = leer_catalogo()
    nuevas = errores = 0
    for i, (idw, etiqueta) in enumerate(sorted(palabras.items(), key=lambda p: p[1]), 1):
        clave = str(idw)
        dato = cat["palabras"].get(clave)
        if dato and (CARPETA / "videos" / dato["archivo"]).exists():
            continue
        if a.max and nuevas >= a.max:
            break
        try:
            time.sleep(PAUSA)
            ficha = pedir(f"{LISTA}?idw={idw}").decode("utf-8", errors="replace")
            m = RE_VIDEO.search(ficha)
            if not m:
                print(f"  [{i}] {etiqueta}: sin video")
                cat["palabras"][clave] = {"etiqueta": etiqueta, "archivo": None, "error": "sin video"}
                errores += 1
                continue
            url = urllib.parse.urljoin(BASE, urllib.parse.quote(m.group(1), safe="/:%"))
            archivo = nombre_archivo(idw, etiqueta)
            time.sleep(PAUSA)
            datos = pedir(url)
            destino = CARPETA / "videos" / archivo
            tmp = destino.with_suffix(".part")
            tmp.write_bytes(datos)
            tmp.replace(destino)
            cat["palabras"][clave] = {"etiqueta": etiqueta, "archivo": archivo, "url": url,
                                      "bytes": len(datos)}
            nuevas += 1
            print(f"  [{i}/{len(palabras)}] {etiqueta} ({len(datos) // 1024} KB)", flush=True)
        except Exception as e:  # red caída, 404...: se anota y se sigue
            print(f"  [{i}] {etiqueta}: error {e}")
            cat["palabras"][clave] = {"etiqueta": etiqueta, "archivo": None, "error": str(e)}
            errores += 1
        if nuevas % 20 == 0:
            guardar_catalogo(cat)
    guardar_catalogo(cat)
    total = sum(1 for d in cat["palabras"].values() if d.get("archivo"))
    print(f"\nNuevas: {nuevas} · errores: {errores} · total descargadas: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
