"""Descarga los videos del Diccionario de LESCO de Hands-On (diccionario.handsonlesco.com).

Uso autorizado por Hands-On LESCO para LESCOCam. Los videos NO se versionan ni se
redistribuyen: quedan en data/dictionary/handson/videos/ (ignorado por git).

La página no tiene botón de descarga y sirve los videos desde Vimeo, que solo los
entrega a un navegador. Por eso se usa yt-dlp con la suplantación de Chrome
(curl_cffi) y la página de Hands-On como origen. Se baja solo la imagen (sin audio):
alcanza para extraer los puntos de las manos.

Va por letra, en orden (A, B, C, ...): primero arma la lista de esa letra, la guarda
en el catálogo y baja todos sus videos antes de pasar a la siguiente. Va de a un
video con pausa y retoma donde quedó (salta los ya descargados).

Uso:
    .venv/bin/python -m scripts.descargar_handson                   # todas las letras
    .venv/bin/python -m scripts.descargar_handson --letras A B      # solo esas
    .venv/bin/python -m scripts.descargar_handson --letras A --max 20   # prueba con 20
    .venv/bin/python -m scripts.descargar_handson --solo-lista      # arma el catálogo sin bajar
"""
from __future__ import annotations

import argparse
import html
import json
import re
import string
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://diccionario.handsonlesco.com/"
LISTA = BASE + "lista-videos?letter={letra}&page={pagina}"
AGENTE = "LESCOCam-proyecto-academico (uso autorizado por Hands-On LESCO)"
CARPETA = Path("data/dictionary/handson")
VIDEOS = CARPETA / "videos"
CATALOGO = CARPETA / "catalogo.json"
PAUSA = 1.0          # segundos entre pedidos
MAX_PAGINAS = 40     # tope de seguridad por letra
BYTES_MIN = 20_000   # un video de verdad pesa mucho más que esto

RE_TARJETA = re.compile(r'data-video-id="(\d+)".*?title="Haga clic para reproducir: ([^"]*)"', re.S)
RE_RESULTADOS = re.compile(r"(\d+)\s+resultados")


def pedir(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def tarjetas(pagina_html: str) -> list[tuple[str, str]]:
    """[(id de Vimeo, palabra)] de una página de la lista."""
    return [(i, html.unescape(t).strip()) for i, t in RE_TARJETA.findall(pagina_html)]


def nombre_archivo(vimeo_id: str, etiqueta: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ_-]+", "_", etiqueta).strip("_") or "sin_nombre"
    return f"{limpio}_{vimeo_id}.mp4"


def leer_catalogo() -> dict:
    if CATALOGO.exists():
        return json.loads(CATALOGO.read_text(encoding="utf-8"))
    return {"fuente": BASE, "palabras": {}}


def guardar_catalogo(cat: dict) -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    tmp = CATALOGO.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(CATALOGO)


def listar_letra(letra: str, cat: dict) -> list[str]:
    """Recorre las páginas de la letra y anota en el catálogo cada palabra. Devuelve los ids de la letra."""
    ids: list[str] = []
    esperados = None
    for pagina in range(1, MAX_PAGINAS + 1):
        time.sleep(PAUSA)
        t = pedir(LISTA.format(letra=letra, pagina=pagina))
        if esperados is None and (m := RE_RESULTADOS.search(t)):
            esperados = int(m.group(1))
        encontradas = tarjetas(t)
        if not encontradas:
            break
        for vid, etiqueta in encontradas:
            if vid not in ids:
                ids.append(vid)
            dato = cat["palabras"].setdefault(vid, {"etiqueta": etiqueta, "letra": letra})
            dato["etiqueta"] = etiqueta
    if esperados is not None and esperados != len(ids):
        print(f"  aviso: la página dice {esperados} resultados y se encontraron {len(ids)}", file=sys.stderr)
    guardar_catalogo(cat)
    return ids


def descargar(ydl, vimeo_id: str, destino: Path) -> None:
    ydl.params["outtmpl"] = {"default": str(destino.with_suffix("")) + ".%(ext)s"}
    ydl.download([f"https://player.vimeo.com/video/{vimeo_id}"])
    if not destino.exists() or destino.stat().st_size < BYTES_MIN:
        destino.unlink(missing_ok=True)
        raise RuntimeError("el archivo quedó vacío o incompleto")


def crear_descargador():
    import yt_dlp
    from yt_dlp.networking.impersonate import ImpersonateTarget
    return yt_dlp.YoutubeDL({
        "quiet": True,
        "no_warnings": True,
        "format": "bv",     # solo imagen
        "http_headers": {"Referer": BASE},
        "impersonate": ImpersonateTarget("chrome"),
        "retries": 3,
        "noprogress": True,
    })


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--letras", nargs="+", default=list(string.ascii_uppercase), help="letras a procesar, en orden")
    p.add_argument("--max", type=int, default=0, help="bajar como mucho N videos nuevos en total (0 = todos)")
    p.add_argument("--solo-lista", action="store_true", help="solo armar el catálogo, sin bajar videos")
    a = p.parse_args(argv)

    VIDEOS.mkdir(parents=True, exist_ok=True)
    cat = leer_catalogo()
    ydl = None if a.solo_lista else crear_descargador()
    nuevos = 0
    fallos: list[tuple[str, str, str]] = []
    for letra in (l.upper() for l in a.letras):
        print(f"== Letra {letra}: armando la lista...", flush=True)
        ids = listar_letra(letra, cat)
        print(f"   {len(ids)} videos en la lista", flush=True)
        if a.solo_lista:
            continue
        for n, vid in enumerate(ids, 1):
            dato = cat["palabras"][vid]
            archivo = nombre_archivo(vid, dato["etiqueta"])
            destino = VIDEOS / archivo
            if destino.exists() and destino.stat().st_size >= BYTES_MIN:
                dato["archivo"] = archivo
                continue
            if a.max and nuevos >= a.max:
                guardar_catalogo(cat)
                print(f"Listo: se bajaron {nuevos} (tope --max).")
                return 0
            try:
                time.sleep(PAUSA)
                descargar(ydl, vid, destino)
                dato["archivo"] = archivo
                nuevos += 1
                print(f"   [{letra} {n}/{len(ids)}] {dato['etiqueta']}", flush=True)
            except Exception as e:  # un video que falla no frena al resto
                fallos.append((letra, dato["etiqueta"], str(e)[:120]))
                print(f"   [{letra} {n}/{len(ids)}] FALLÓ {dato['etiqueta']}: {str(e)[:100]}", file=sys.stderr, flush=True)
            if n % 10 == 0:
                guardar_catalogo(cat)
        guardar_catalogo(cat)
        print(f"== Letra {letra} terminada.", flush=True)
    print(f"Listo: {nuevos} videos nuevos, {len(fallos)} con error.")
    for letra, etiqueta, motivo in fallos:
        print(f"  {letra} {etiqueta}: {motivo}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
