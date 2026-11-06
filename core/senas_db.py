"""Plantillas de palabras en SQLite: data/reference/senas.db.

CAMBIO DE CONTRATO: la app móvil tiene que leer este archivo y armar los mismos
descriptores en vivo (core/palabras.py). Formato (FORMATO_DB = 1):

    meta(clave TEXT PRIMARY KEY, valor TEXT)
        formato             "1"
        version_descriptor  core.palabras.VERSION_DESCRIPTOR
        version_vector      core.landmarks.VERSION_VECTOR (rasgos de la forma)
        muestras            filas de cada plantilla (MUESTRAS)
        columnas            columnas de cada fila (COLUMNAS = 83)
        escala              los datos son int16 / escala (4096: rango +-8, paso 0.00024)
        pesos               JSON, lista de 83 números: se multiplica cada columna al cargar
        constantes          JSON con las constantes de segmentación y comparación
        fuente              de dónde salen las plantillas
        creado              fecha ISO
    palabras(id INTEGER PRIMARY KEY, etiqueta TEXT UNIQUE,
             categoria TEXT: "palabra" o "letra" (letra deletreada: plantilla NEGATIVA, si gana no se dice nada),
             idw INTEGER (ficha de CENAREC o NULL), manos INTEGER (1 o 2), fuente TEXT)
    plantillas(id INTEGER PRIMARY KEY, palabra_id INTEGER -> palabras.id,
               repeticion INTEGER (1, 2...), fuente TEXT, inicio REAL, fin REAL (segundos en el video),
               datos BLOB)

`datos` = muestras x columnas int16 little-endian, fila por fila. Cada fila
(SIN pesos, en forma canónica: la dominante como diestra):

    0-1    posición de la muñeca dominante: (muñeca - centro de hombros) / ancho de hombros
    2-32   31 rasgos de la forma de la mano dominante (core/rasgos.py)
    33-38  ejes "y" y "z" del marco de la palma dominante (core/rasgos.marco_palma)
    39-40  posición de la muñeca dominante respecto de la cara: c = (muñeca - nariz) / ancho de hombros,
           x max(0, 1 - |c| / CARA_RADIO) (solo cerca de la cara; ver core/palabras.py).
           Desde version_descriptor 2
    41-81  lo mismo para la mano NO dominante (todo 0 si no participa)
    82     1 si la no dominante participa, 0 si no

Para comparar: descriptor = datos / escala * pesos (columna a columna) y DTW
(core/palabras.dtw_lote). Es el mismo número que da core.palabras.descriptor().

Por qué SQLite y no JSON: binario chico (int16), se agregan o borran palabras
sin reescribir todo, se puede consultar por etiqueta y sqflite lo lee en Flutter.
Un .db en git se reemplaza entero en cada cambio: se versiona solo el de las
palabras iniciales (< 1 MB) y se regenera con scripts/construir_palabras.py
desde el cache de extracción; el de las 1072 se arma igual y no se versiona.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from core import palabras as P
from core.landmarks import VERSION_VECTOR

RAIZ = Path(__file__).resolve().parent.parent
RUTA_DB = RAIZ / "data" / "reference" / "senas.db"
FORMATO_DB = 1
ESCALA = 4096

ESQUEMA = """
CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE palabras (
    id INTEGER PRIMARY KEY,
    etiqueta TEXT NOT NULL UNIQUE,
    categoria TEXT NOT NULL DEFAULT 'palabra',
    idw INTEGER,
    manos INTEGER NOT NULL,
    fuente TEXT NOT NULL
);
CREATE TABLE plantillas (
    id INTEGER PRIMARY KEY,
    palabra_id INTEGER NOT NULL REFERENCES palabras(id) ON DELETE CASCADE,
    repeticion INTEGER NOT NULL,
    fuente TEXT NOT NULL,
    inicio REAL,
    fin REAL,
    datos BLOB NOT NULL
);
CREATE INDEX plantillas_palabra ON plantillas(palabra_id);
"""


class VersionIncompatible(ValueError):
    """senas.db es de otro formato o de otra versión del descriptor."""


def pesos_columnas(pesos=None) -> np.ndarray:
    """(COLUMNAS,) con el peso de cada columna (los de core/palabras.py si pesos es None)."""
    pp, pf, pe, pn, pa, pc = P.pesos_completos(pesos)
    bloque = np.concatenate([np.full(2, pp), np.full(P.NUM_RASGOS, pf), np.full(6, pe), np.full(2, pc)])
    return np.concatenate([bloque, bloque * pn, [pa]])


def constantes() -> dict:
    nombres = ("Y_REPOSO", "T_ARRANQUE", "T_FIN", "PREVIOS", "DURACION_MIN", "DURACION_MAX", "HUECO_MAX",
               "VISIBILIDAD_MIN", "W_MIN", "MUESTRAS", "FRACCION_ACTIVA", "BANDA", "DISTANCIA_MAX", "UMBRAL",
               "MARGEN", "CARA_MODO", "CARA_RADIO", "NARIZ_TIPICA")
    return {n: getattr(P, n) for n in nombres}


def a_blob(crudo: np.ndarray) -> bytes:
    q = np.clip(np.round(np.asarray(crudo, dtype=np.float64) * ESCALA), -32768, 32767).astype("<i2")
    return q.tobytes()


def desde_blob(datos: bytes, muestras: int, columnas: int) -> np.ndarray:
    return np.frombuffer(datos, dtype="<i2").astype(np.float64).reshape(muestras, columnas) / ESCALA


def escribir(ruta: Path | str, entradas: Sequence[dict], fuente: str) -> None:
    """Crea senas.db desde cero (archivo temporal + reemplazo).

    entradas: [{"etiqueta", "idw", "manos", "fuente", "plantillas": [{"repeticion", "fuente", "inicio",
               "fin", "crudo": (MUESTRAS, COLUMNAS) sin pesos}]}]
    """
    ruta = Path(ruta)
    tmp = ruta.with_suffix(".db.tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp)
    try:
        con.executescript(ESQUEMA)
        meta = {"formato": FORMATO_DB, "version_descriptor": P.VERSION_DESCRIPTOR, "version_vector": VERSION_VECTOR,
                "muestras": P.MUESTRAS, "columnas": P.COLUMNAS, "escala": ESCALA,
                "pesos": json.dumps([round(float(x), 6) for x in pesos_columnas()]),
                "constantes": json.dumps(constantes()), "fuente": fuente,
                "creado": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
        con.executemany("INSERT INTO meta VALUES (?, ?)", [(k, str(v)) for k, v in meta.items()])
        for e in sorted(entradas, key=lambda x: x["etiqueta"]):
            cur = con.execute("INSERT INTO palabras (etiqueta, categoria, idw, manos, fuente) VALUES (?, ?, ?, ?, ?)",
                              (e["etiqueta"], e.get("categoria", "palabra"), e.get("idw"), int(e["manos"]),
                               e["fuente"]))
            for p in e["plantillas"]:
                crudo = np.asarray(p["crudo"])
                if crudo.shape != (P.MUESTRAS, P.COLUMNAS):
                    raise ValueError(f"{e['etiqueta']}: plantilla {crudo.shape}, se esperaba {(P.MUESTRAS, P.COLUMNAS)}")
                con.execute("INSERT INTO plantillas (palabra_id, repeticion, fuente, inicio, fin, datos) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (cur.lastrowid, int(p["repeticion"]), p["fuente"], p.get("inicio"), p.get("fin"),
                             a_blob(crudo)))
        con.commit()
        con.execute("VACUUM")
    finally:
        con.close()
    tmp.replace(ruta)


def leer(ruta: Path | str = RUTA_DB) -> dict:
    """{"meta": {...}, "plantillas": [(etiqueta, crudo (MUESTRAS, COLUMNAS)), ...], "palabras": {etiqueta: fila}}."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Armala con: .venv/bin/python -m scripts.construir_palabras")
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    try:
        meta = dict(con.execute("SELECT clave, valor FROM meta"))
        if meta.get("formato") != str(FORMATO_DB):
            raise VersionIncompatible(f"{ruta}: formato {meta.get('formato')}, se esperaba {FORMATO_DB}")
        if meta.get("version_descriptor") != str(P.VERSION_DESCRIPTOR) or meta.get("version_vector") != str(VERSION_VECTOR):
            raise VersionIncompatible(f"{ruta}: descriptor {meta.get('version_descriptor')} / vector "
                                      f"{meta.get('version_vector')}; el motor usa {P.VERSION_DESCRIPTOR} / {VERSION_VECTOR}")
        muestras, columnas = int(meta["muestras"]), int(meta["columnas"])
        if muestras != P.MUESTRAS or columnas != P.COLUMNAS:
            raise VersionIncompatible(f"{ruta}: plantillas {muestras}x{columnas}, el motor usa {P.MUESTRAS}x{P.COLUMNAS}")
        palabras = {fila[0]: {"idw": fila[1], "manos": fila[2], "categoria": fila[3]}
                    for fila in con.execute("SELECT etiqueta, idw, manos, categoria FROM palabras")}
        plantillas = [(e, desde_blob(d, muestras, columnas)) for e, d in con.execute(
            "SELECT p.etiqueta, t.datos FROM plantillas t JOIN palabras p ON p.id = t.palabra_id "
            "ORDER BY p.etiqueta, t.repeticion")]
    finally:
        con.close()
    return {"meta": meta, "plantillas": plantillas, "palabras": palabras}


def comparador(ruta: Path | str = RUTA_DB, pesos=None, etiquetas: Optional[set] = None, **kw) -> P.ComparadorPalabras:
    """ComparadorPalabras con las plantillas de senas.db (pesos aplicados una sola vez, al cargar)."""
    datos = leer(ruta)
    w = pesos_columnas(pesos)
    plantillas = [(e, c) for e, c in datos["plantillas"] if etiquetas is None or e in etiquetas]
    categorias = {e: d["categoria"] for e, d in datos["palabras"].items()}
    return P.ComparadorPalabras([e for e, _ in plantillas], [c * w for _, c in plantillas], categorias=categorias,
                                **kw)
