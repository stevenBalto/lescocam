"""Mide el modelo de señas (fase 4) y su suma con el DTW contra el banco de prueba (problema 1, fase 5).

Cada toma va por el mismo camino que scripts/evaluar_banco.py (seña más larga del Segmentador)
y se compara con TODAS las plantillas de senas.db (85 palabras + letras negativas):

    DTW     -distancia del motor actual (descriptor con pesos v3, sin prefiltro)
    modelo  coseno del vector de la seña con el de cada plantilla (descriptor crudo)
    suma    peso * z(modelo) + (1 - peso) * z(DTW), z por toma sobre todas las etiquetas
            (peso 0.5 por defecto: elegido con ASL Citizen en la fase 4, NO con el banco)

Por etiqueta vale su mejor plantilla y la mejor variante de espejo de la toma.

ACEPTAR (decir la palabra): la mejor etiqueta tiene que ser una palabra (no una letra), su puntaje
>= UMBRAL, ventaja sobre la 2.ª >= MARGEN y la duración no menor que DURACION_RELATIVA_MIN x la
plantilla más corta. UMBRAL y MARGEN se AJUSTAN con dos personas y se VALIDAN con las otras dos
(christian+steven <-> reyman+johan): el número que vale es el de validación. Criterio de ajuste:
la mayor tasa de "dice bien" con aceptación errónea <= --tope-erronea en las personas de ajuste.

Uso:
    .venv/Scripts/python -m scripts.evaluar_banco_modelo
    .venv/Scripts/python -m scripts.evaluar_banco_modelo --peso 0.7 --json resultado.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np

from core import banco
from core import palabras as P
from core import senas_db
from scripts.construir_palabras import PESOS_CRUDOS
from scripts.entrenar_embedding import MODELO, embeber

GRUPOS = (("christian", "steven"), ("reyman", "johan"))


def grupo_de(persona: str) -> int:
    for g, nombres in enumerate(GRUPOS):
        if any(persona == n or persona.startswith(n + "-") for n in nombres):
            return g
    return -1


def z(s: np.ndarray) -> np.ndarray:
    return (s - s.mean()) / max(float(s.std()), 1e-9)


class Puntuador:
    """DTW + modelo contra todas las plantillas de senas.db."""

    def __init__(self, ruta_db: Path, ruta_modelo: Path, dispositivo: str = "cpu"):
        from scripts.modelo_senas import cargar
        self.comparador = senas_db.comparador(ruta_db, prefiltro=None)
        datos = senas_db.leer(ruta_db)
        self.etiquetas = sorted({e for e, _ in datos["plantillas"]})
        self.categorias = {e: datos["palabras"][e]["categoria"] for e in self.etiquetas}
        self.es_palabra = np.array([self.categorias[e] == "palabra" for e in self.etiquetas])
        self.modelo, self.dev = cargar(ruta_modelo, dispositivo), dispositivo
        self.con_puntos = self.modelo.config["columnas"] > P.COLUMNAS
        if self.con_puntos:              # los puntos no están en senas.db: las plantillas salen del cache de CENAREC
            from scripts.entrada_modelo import plantillas_cenarec
            crudos, etiquetas = plantillas_cenarec(True)
        else:
            crudos = np.stack([d for _, d in datos["plantillas"]]).astype(np.float32)
            etiquetas = [e for e, _ in datos["plantillas"]]
        conocidas = np.array([e in self.categorias for e in etiquetas])   # el cache puede traer palabras que la db no
        self._emb = embeber(self.modelo, crudos[conocidas], dispositivo)
        self._fila = np.array([self.etiquetas.index(e) for e in np.asarray(etiquetas)[conocidas]])

    def puntajes(self, sena: list) -> Optional[dict]:
        """{'dtw': (E,), 'modelo': (E,)} por etiqueta (mayor = más parecido) o None si no hay descriptor."""
        from scripts.entrada_modelo import entradas
        pesados = P.descriptores(sena, "auto")
        crudos = [d for _, d in entradas(sena, "auto", self.con_puntos)]
        if not pesados or not crudos:
            return None
        dist = self.comparador.distancias(pesados)
        dtw = -np.array([dist[e] for e in self.etiquetas])
        sim = (embeber(self.modelo, np.stack(crudos).astype(np.float32), self.dev) @ self._emb.T).max(0)
        modelo = np.full(len(self.etiquetas), -np.inf)
        np.maximum.at(modelo, self._fila, sim)
        # etiquetas sin plantilla del modelo (letras / Hands-On que no están en el cache de CENAREC):
        # el peor puntaje de la toma, para que z no dé NaN y no ganen nunca por el modelo
        modelo[~np.isfinite(modelo)] = sim.min()
        return {"dtw": dtw, "modelo": modelo}


def evaluar_tomas(tomas: list, puntuador: Puntuador) -> list[dict]:
    filas = []
    for t in tomas:
        cp = [P.cuadro_palabra(c) for c in t.cuadros]
        senas = P.segmentar(cp, [c.t for c in t.cuadros])
        fila = {"persona": t.persona, "grupo": grupo_de(t.persona), "etiqueta": t.etiqueta, "camara": t.camara,
                "archivo": t.ruta.name, "puntajes": None, "duracion": 0.0}
        if senas:
            sena = max(senas, key=lambda s: s[-1].t - s[0].t)
            fila["puntajes"], fila["duracion"] = puntuador.puntajes(sena), P.duracion(sena)
        filas.append(fila)
    return filas


def combinar(p: dict, peso: float) -> np.ndarray:
    if peso >= 1:
        return z(p["modelo"])
    if peso <= 0:
        return z(p["dtw"])
    return peso * z(p["modelo"]) + (1 - peso) * z(p["dtw"])


def decisiones(filas: list[dict], puntuador: Puntuador, peso: float) -> list[dict]:
    """Por toma: mejor palabra (top-1/top-3), mejor etiqueta en general, puntaje y ventaja sobre la 2.ª."""
    salida = []
    for f in filas:
        d = {"etiqueta": f["etiqueta"], "grupo": f["grupo"], "persona": f["persona"], "hubo_sena": f["puntajes"] is not None}
        if d["hubo_sena"]:
            s = combinar(f["puntajes"], peso)
            orden = np.argsort(-s)
            pal = [i for i in orden if puntuador.es_palabra[i]]
            d.update(top=[puntuador.etiquetas[i] for i in pal[:3]], mejor=puntuador.etiquetas[orden[0]],
                     s1=float(s[orden[0]]), ventaja=float(s[orden[0]] - s[orden[1]]),
                     corta=_corta(puntuador, puntuador.etiquetas[orden[0]], f["duracion"]))
        salida.append(d)
    return salida


def _corta(puntuador: Puntuador, palabra: str, duracion: float) -> bool:
    minimo = puntuador.comparador.duracion_min.get(palabra)
    return minimo is not None and duracion < P.DURACION_RELATIVA_MIN * minimo


def aceptada(d: dict, puntuador: Puntuador, umbral: float, margen: float) -> Optional[str]:
    if not d["hubo_sena"] or d["corta"] or puntuador.categorias[d["mejor"]] != "palabra":
        return None
    return d["mejor"] if d["s1"] >= umbral and d["ventaja"] >= margen else None


def metricas(ds: list[dict], puntuador: Puntuador, umbral: float = np.inf, margen: float = 0.0) -> dict:
    n = len(ds)
    if not n:
        return {"n": 0}
    top1 = sum(1 for d in ds if d["hubo_sena"] and d["top"][0] == d["etiqueta"])
    top3 = sum(1 for d in ds if d["hubo_sena"] and d["etiqueta"] in d["top"])
    dichas = [aceptada(d, puntuador, umbral, margen) for d in ds]
    bien = sum(1 for d, a in zip(ds, dichas) if a == d["etiqueta"])
    mal = sum(1 for d, a in zip(ds, dichas) if a is not None and a != d["etiqueta"])
    return {"n": n, "top1": top1 / n, "top3": top3 / n, "aceptada_bien": bien / n, "aceptacion_erronea": mal / n}


def ajustar(ds: list[dict], puntuador: Puntuador, tope: float) -> tuple[float, float]:
    """(umbral, margen) con más 'dice bien' y errónea <= tope en estas tomas."""
    con = [d for d in ds if d["hubo_sena"]]
    umbrales = sorted({float(np.floor(d["s1"] * 1000) / 1000) for d in con}) or [np.inf]   # floor: el umbral no rechaza su toma
    margenes = np.unique(np.quantile([d["ventaja"] for d in con], np.linspace(0, 0.95, 40))) if con else [0.0]
    mejor = (-1.0, -1.0, np.inf, 0.0)
    for m in margenes:
        for u in umbrales[::max(1, len(umbrales) // 120)]:
            r = metricas(ds, puntuador, u, m)
            if r["aceptacion_erronea"] <= tope and (r["aceptada_bien"], -u) > (mejor[0], mejor[1]):
                mejor = (r["aceptada_bien"], -u, u, float(m))
    return mejor[2], mejor[3]


def validacion_cruzada(ds: list[dict], puntuador: Puntuador, tope: float) -> dict:
    """Ajusta con un grupo, mide con el otro, y al revés; suma las tomas de validación."""
    resultado, validadas = {}, []
    for g in (0, 1):
        ajuste = [d for d in ds if d["grupo"] == g]
        valida = [d for d in ds if d["grupo"] == 1 - g]
        u, m = ajustar(ajuste, puntuador, tope)
        validadas += [(d, u, m) for d in valida]
        resultado[f"ajuste_{'+'.join(GRUPOS[g])}"] = {"umbral": u, "margen": m, "ajuste": metricas(ajuste, puntuador, u, m),
                                                      "validacion": metricas(valida, puntuador, u, m)}
    n = len(validadas)
    bien = sum(1 for d, u, m in validadas if aceptada(d, puntuador, u, m) == d["etiqueta"])
    mal = sum(1 for d, u, m in validadas if aceptada(d, puntuador, u, m) not in (None, d["etiqueta"]))
    resultado["validacion_total"] = {"n": n, "aceptada_bien": bien / max(n, 1), "aceptacion_erronea": mal / max(n, 1)}
    return resultado


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--banco", type=Path, default=banco.CARPETA)
    p.add_argument("--db", type=Path, default=senas_db.RUTA_DB)
    p.add_argument("--modelo", type=Path, default=MODELO)
    p.add_argument("--peso", type=float, default=0.5, help="peso del modelo en la suma (0 = solo DTW, 1 = solo modelo)")
    p.add_argument("--tope-erronea", type=float, default=0.01, help="errónea máxima al ajustar umbral y margen")
    p.add_argument("--json", type=Path)
    a = p.parse_args(argv)

    tomas = banco.cargar_tomas(a.banco)
    if not tomas:
        print(f"No hay tomas en {a.banco}")
        return 1
    puntuador = Puntuador(a.db, a.modelo)
    filas = evaluar_tomas(tomas, puntuador)
    resumen = {}
    for peso, nombre in ((0.0, "dtw"), (1.0, "modelo"), (a.peso, f"suma_{a.peso}")):
        ds = decisiones(filas, puntuador, peso)
        r = {"total": metricas(ds, puntuador), "por_persona": {}}
        for persona in sorted({d["persona"] for d in ds}):
            r["por_persona"][persona] = metricas([d for d in ds if d["persona"] == persona], puntuador)
        r["validacion_cruzada"] = validacion_cruzada(ds, puntuador, a.tope_erronea)
        resumen[nombre] = r
        t, v = r["total"], r["validacion_cruzada"]["validacion_total"]
        print(f"{nombre:<10} top1 {t['top1']:6.1%}  top3 {t['top3']:6.1%} | validación cruzada: dice bien "
              f"{v['aceptada_bien']:6.1%}  ERRÓNEA {v['aceptacion_erronea']:5.1%}")
        for persona, m in r["por_persona"].items():
            print(f"    {persona:<22} top1 {m['top1']:6.1%}  top3 {m['top3']:6.1%}")
    if a.json:
        a.json.write_text(json.dumps(resumen, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
