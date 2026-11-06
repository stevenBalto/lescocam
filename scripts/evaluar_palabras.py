"""Mide el reconocimiento de PALABRAS (core/palabras.py) con los videos de CENAREC.

Usa el cache de scripts/extraer_cenarec.py (no corre MediaPipe salvo para medir
su tiempo). Cada video tiene la seña DOS veces: una repetición hace de
plantilla y la otra de prueba, y al revés.

  1. cruzada: top-1, top-5, confianza y margen, palabras aceptadas (umbral +
     margen) y aceptadas mal, pares más confundidos.
  2. variantes: la prueba sale del video transformado (15 fps, cámara 4:3, más
     cerca, más lejos, girada, corrida, espejo = zurdo; ver extraer_cenarec.py)
     o con otra velocidad (+-30 %, sobre el cache), y la plantilla del video
     original. Mide también si el segmentador sigue encontrando las 2 repeticiones.
  3. negativas (no tiene que decir nada): pedazos de una seña (primer y último
     40 %), transiciones (fin de una palabra + comienzo de otra sin reposo) y el
     video del abecedario entero por el reconocedor en vivo.
  4. escala: plantillas de 85, ~300 y todas las palabras con cache; cómo cae el
     acierto de las 85 iniciales y de todas.
  5. umbrales: aceptadas bien / mal y falsos positivos para varios umbral y margen.
  6. velocidad: ms por frame (rasgos + segmentador; MediaPipe aparte) y por
     comparación contra N plantillas.

Uso:
    .venv/bin/python -m scripts.evaluar_palabras                  # todo
    .venv/bin/python -m scripts.evaluar_palabras --solo cruzada variantes
    .venv/bin/python -m scripts.evaluar_palabras --pesos 2 0.5 0.5 0.7 1 1   # probar pesos
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from collections import Counter
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from core import palabras as P
from scripts.construir_palabras import cargar_video
from scripts.extraer_cenarec import EXTRACCION, LISTA, catalogo, leer_lista, ruta_cache

VARIANTES_VIDEO = ("15fps", "4x3", "cerca", "lejos", "giro", "desplazado", "espejo")
VARIANTES_ELEGIDAS = None   # --variantes
VELOCIDADES = {"rapido": 1.3, "lento": 0.7}
ABECEDARIO = EXTRACCION / "otros" / "abecedario-lesco.npz"
SEMILLA = 7


# ---------------------------------------------------------------- carga (en paralelo)

def _cargar(args):
    etiqueta, ruta = args
    cuadros, tiempos = cargar_video(ruta)
    return etiqueta, cuadros, tiempos


def cargar(etiquetas, variante="base", procesos=6) -> dict:
    """etiqueta -> (cuadros, tiempos) de las que tienen cache de esa variante."""
    cat = catalogo()
    trabajos = [(e, ruta_cache(cat[e]["idw"], variante)) for e in etiquetas
                if e in cat and ruta_cache(cat[e]["idw"], variante).exists()]
    with Pool(procesos) as pool:
        return {e: (c, t) for e, c, t in pool.imap_unordered(_cargar, trabajos, chunksize=4)}


def con_velocidad(cuadros, tiempos, factor: float, fps: float = 30.0):
    """La misma toma hecha `factor` veces más rápido, vista por una cámara de `fps`."""
    duracion = tiempos[-1] / factor
    salida, ts = [], []
    for k in range(int(duracion * fps) + 1):
        t = k / fps
        i = min(int(round(t * factor * fps)), len(cuadros) - 1)
        c = cuadros[i]
        salida.append(None if c is None else replace(c, t=t))
        ts.append(t)
    return salida, ts


# ---------------------------------------------------------------- piezas

def referencias(senas: dict, rep: int, pesos=None):
    """(etiquetas, descriptores) con la repetición `rep` de cada palabra (diestra, como senas.db)."""
    etq, desc = [], []
    for e, reps in senas.items():
        if len(reps) > rep:
            d = P.descriptor(reps[rep], P.espejos_posibles(reps[rep], "derecha")[0], pesos=pesos)
            if d is not None:
                etq.append(e)
                desc.append(d)
    return etq, desc


NEGATIVAS_LETRAS: dict = {}   # etiqueta LETRA-X -> repeticiones (si se usa --letras)


def comparador(senas: dict, rep: int, pesos=None, prefiltro=P.PREFILTRO) -> P.ComparadorPalabras:
    """Comparador con la repetición `rep` de cada palabra (+ las letras deletreadas como negativas si hay)."""
    etq, desc = referencias(senas, rep, pesos)
    categorias = {}
    for e, reps in NEGATIVAS_LETRAS.items():
        for s in reps:
            d = P.descriptor(s, P.espejos_posibles(s, "derecha")[0], pesos=pesos)
            if d is not None:
                etq.append(e)
                desc.append(d)
                categorias[e] = "letra"
    return P.ComparadorPalabras(etq, desc, categorias=categorias, prefiltro=prefiltro)


def elegir_reps(senas_video: list) -> list:
    if len(senas_video) > 2:
        largas = sorted(senas_video, key=lambda s: s[-1].t - s[0].t, reverse=True)[:2]
        return sorted(largas, key=lambda s: s[0].t)
    return senas_video


def emparejar(base: list, otras: list, factor: float = 1.0) -> list:
    """Para cada repetición de `base`, la seña de `otras` que más se le superpone en el tiempo (o None)."""
    salida = []
    for b in base:
        b0, b1 = b[0].t / factor, b[-1].t / factor
        mejor, solape = None, 0.0
        for o in otras:
            s = min(b1, o[-1].t) - max(b0, o[0].t)
            if s > solape:
                mejor, solape = o, s
        salida.append(mejor)
    return salida


class Resultado:
    def __init__(self):
        self.filas = []   # (verdad, top [(palabra, conf)], aceptada o None)

    def agregar(self, verdad, top, aceptada):
        self.filas.append((verdad, top, aceptada))

    def resumen(self) -> dict:
        n = len(self.filas)
        if not n:
            return {"n": 0}
        top1 = sum(bool(t) and t[0][0] == v for v, t, _ in self.filas)
        top5 = sum(any(p == v for p, _ in t) for v, t, _ in self.filas)
        acept = sum(a is not None for _, _, a in self.filas)
        bien = sum(a == v for v, _, a in self.filas)
        conf = [t[0][1] for v, t, _ in self.filas if t and t[0][0] == v]
        marg = [t[0][1] - t[1][1] for v, t, _ in self.filas if t and t[0][0] == v and len(t) > 1]
        return {"n": n, "top1": top1 / n, "top5": top5 / n, "aceptadas": acept / n, "bien": bien / n,
                "mal": (acept - bien) / n, "conf": float(np.median(conf)) if conf else 0.0,
                "margen": float(np.median(marg)) if marg else 0.0}

    def confusiones(self, k=10):
        return Counter((v, t[0][0]) for v, t, _ in self.filas if t and t[0][0] != v).most_common(k)


def fmt(r: dict) -> str:
    if not r.get("n"):
        return "sin datos"
    return (f"n={r['n']:4d}  top-1 {100 * r['top1']:5.1f} %  top-5 {100 * r['top5']:5.1f} %  "
            f"aceptadas {100 * r['aceptadas']:5.1f} % (bien {100 * r['bien']:5.1f} %, mal {100 * r['mal']:4.1f} %)  "
            f"conf. mediana {r['conf']:.2f}  margen {r['margen']:.2f}")


def probar(comp: P.ComparadorPalabras, verdad, sena, res: Resultado, mano="auto", pesos=None):
    cand = P.descriptores(sena, mano, pesos=pesos) if sena is not None else []
    if not cand:
        res.agregar(verdad, [], None)
        return
    palabra, _, top = comp.clasificar(cand)
    res.agregar(verdad, top, palabra)


# ---------------------------------------------------------------- secciones

def cruzada(senas, pesos, mostrar=True) -> Resultado:
    res = Resultado()
    for ref in (0, 1):
        comp = comparador(senas, ref, pesos)
        for e, reps in senas.items():
            if len(reps) > 1 - ref:
                probar(comp, e, reps[1 - ref], res, pesos=pesos)
    if mostrar:
        print("\n== 1. Validación cruzada (una repetición contra la otra) ==")
        print(fmt(res.resumen()))
        print("Confusiones:", ", ".join(f"{v}->{p} x{n}" for (v, p), n in res.confusiones()) or "ninguna")
    return res


def variantes(etiquetas, senas_base, datos_base, pesos, procesos) -> dict:
    print("\n== 2. Variantes (prueba transformada contra plantilla original) ==")
    salida = {}
    comps = [comparador(senas_base, r, pesos) for r in (0, 1)]
    nombres = list(VELOCIDADES) + list(VARIANTES_VIDEO)
    for v in nombres:
        if v in VELOCIDADES:
            datos = {e: con_velocidad(c, t, VELOCIDADES[v]) for e, (c, t) in datos_base.items()}
            factor = VELOCIDADES[v]
        else:
            datos = cargar(etiquetas, v, procesos)
            factor = 1.0
        if not datos:
            print(f"{v:11s} sin cache (scripts/extraer_cenarec.py --variante {v})")
            continue
        res, dos = Resultado(), 0
        for e, (c, t) in datos.items():
            if e not in senas_base:
                continue
            otras = P.segmentar(c, t)
            dos += len(otras) == 2
            for k, o in enumerate(emparejar(senas_base[e], otras, factor)):
                probar(comps[1 - k], e, o, res, pesos=pesos)
        salida[v] = res
        print(f"{v:11s} 2 repeticiones en {dos}/{len(datos)}  {fmt(res.resumen())}")
    return salida


def pedazos(senas, rng) -> list:
    """Señas que NO son palabras: primer y último 40 % de cada repetición y transiciones A->B sin reposo."""
    salida = []
    for e, reps in senas.items():
        for s in reps:
            t0, t1 = s[0].t, s[-1].t
            salida.append(("comienzo", [c for c in s if c.t <= t0 + 0.4 * (t1 - t0)], e))
            salida.append(("final", [c for c in s if c.t >= t1 - 0.4 * (t1 - t0)], e))
    etiquetas = sorted(senas)
    for e in etiquetas:
        otra = rng.choice([x for x in etiquetas if x != e])
        a, b = senas[e][0], senas[otra][-1]
        ma, mb = (a[0].t + a[-1].t) / 2, (b[0].t + b[-1].t) / 2
        mitad_a = [c for c in a if c.t >= ma]
        mitad_b = [c for c in b if c.t <= mb]
        if mitad_a and mitad_b:
            corrimiento = mitad_a[-1].t + 1 / 30 - mitad_b[0].t
            salida.append(("transicion", mitad_a + [replace(c, t=c.t + corrimiento) for c in mitad_b], f"{e}+{otra}"))
    return salida


def deletreo(cuadros, tiempos) -> list:
    """Tramos del video del abecedario como si fueran señas: cada letra sola y de a 3 letras seguidas
    (deletrear una palabra corta), con los tramos de data/dictionary/evaluacion_landmarks.json."""
    import json
    ruta = EXTRACCION.parent.parent / "evaluacion_landmarks.json"
    if not ruta.exists():
        return []
    tramos = json.loads(ruta.read_text(encoding="utf-8"))["tramos"]
    salida = []
    for k in range(len(tramos)):
        for ancho, tipo in ((1, "letra"), (3, "3 letras")):
            if k + ancho > len(tramos):
                continue
            a, b = tramos[k]["inicio"], tramos[k + ancho - 1]["fin"]
            s = [c for c in cuadros[a:b + 1] if c is not None]
            if len(s) >= 4 and s[-1].t - s[0].t <= P.DURACION_MAX:
                salida.append((tipo, s, tramos[k]["letra"]))
    return salida


def negativas(senas, pesos, comp=None, mostrar=True) -> dict:
    comp = comp or comparador(senas, 0, pesos)
    rng = random.Random(SEMILLA)
    cuenta, aceptadas, confs, ejemplos, propia = Counter(), Counter(), {}, {}, Counter()
    piezas = pedazos(senas, rng)
    if ABECEDARIO.exists():
        piezas += deletreo(*cargar_video(ABECEDARIO))
    for tipo, s, origen in piezas:
        cand = P.descriptores(s, pesos=pesos) if len(s) >= 2 else []
        cuenta[tipo] += 1
        if cand:
            palabra, conf, top = comp.clasificar(cand)
            confs.setdefault(tipo, []).append((top[0][1], top[0][1] - top[1][1]))
            aceptadas[tipo] += palabra is not None
            if palabra is not None:
                ejemplos.setdefault(tipo, Counter())[palabra] += 1
                propia[tipo] += palabra in str(origen).split("+")
    abc = None
    if ABECEDARIO.exists():
        from core.reconocedor_palabras import ReconocedorPalabras
        cuadros, tiempos = cargar_video(ABECEDARIO)
        rec = ReconocedorPalabras(comp)
        dichas, senas_abc = [], 0
        for c, t in zip(cuadros, tiempos):
            antes = rec.ultima
            p = rec.actualizar_cuadro(c, t)
            senas_abc += rec.ultima is not antes
            if p:
                dichas.append((round(t, 1), p))
        p = rec.terminar()
        if p:
            dichas.append(("fin", p))
        abc = (senas_abc, dichas, tiempos[-1])
        confs["abecedario"] = []
    if mostrar:
        print("\n== 3. Negativas (no tienen que decir nada) ==")
        for tipo in cuenta:
            c = np.array(confs.get(tipo, [(0, 0)]))
            print(f"{tipo:11s} {aceptadas[tipo]:3d}/{cuenta[tipo]} aceptadas ({propia[tipo]} como la palabra de origen)  "
                  f"(conf. mediana {np.median(c[:, 0]):.2f}, p90 {np.percentile(c[:, 0], 90):.2f})  "
                  f"{dict(ejemplos.get(tipo, Counter()).most_common(6))}")
        if abc:
            print(f"abecedario  video de {abc[2]:.0f} s: {abc[0]} señas cortadas, {len(abc[1])} palabras dichas "
                  f"{abc[1][:12]}")
        else:
            print("abecedario  sin cache (scripts/extraer_cenarec.py --video data/dictionary/videos/abecedario-lesco.mp4)")
    return {"cuenta": cuenta, "aceptadas": aceptadas, "confs": confs, "abecedario": abc}


def escala(iniciales, procesos, pesos):
    print("\n== 4. Escala (plantillas de más palabras) ==")
    cat = catalogo()
    todas = sorted(e for e in cat if ruta_cache(cat[e]["idw"]).exists() and e not in NEGATIVAS_LETRAS)
    if len(todas) <= len(iniciales):
        print("Hay cache solo de las iniciales: correr scripts/extraer_cenarec.py --todas")
        return
    inicio = time.perf_counter()
    datos = cargar(todas, "base", procesos)
    senas = {e: elegir_reps(P.segmentar(c, t)) for e, (c, t) in datos.items()}
    print(f"({len(senas)} videos cargados y segmentados en {time.perf_counter() - inicio:.0f} s; "
          f"con 2 repeticiones: {sum(len(P.segmentar(c, t)) == 2 for c, t in datos.values())})")
    rng = random.Random(SEMILLA)
    resto = [e for e in todas if e not in iniciales]
    rng.shuffle(resto)
    tamanos = [len(iniciales), 300, len(todas)]
    for n in tamanos:
        elegidas = set(iniciales) | set(resto[:max(0, n - len(iniciales))])
        sub = {e: senas[e] for e in elegidas if e in senas}
        res_ini, res_todas = Resultado(), Resultado()
        for ref in (0, 1):
            comp = comparador(sub, ref, pesos)
            for e, reps in sub.items():
                if len(reps) > 1 - ref:
                    probar(comp, e, reps[1 - ref], res_todas, pesos=pesos)
                    if e in iniciales:
                        res_ini.filas.append(res_todas.filas[-1])
        print(f"{len(sub):5d} palabras | las 85 iniciales: {fmt(res_ini.resumen())}")
        print(f"{'':5s}          | todas:           {fmt(res_todas.resumen())}")
        if n == tamanos[-1]:
            print("Confusiones (todas):", ", ".join(f"{v}->{p}" for (v, p), _ in res_todas.confusiones(25)))
            sin = Resultado()
            for ref in (0, 1):
                comp = comparador(sub, ref, pesos, prefiltro=None)
                for e, reps in sub.items():
                    if len(reps) > 1 - ref:
                        probar(comp, e, reps[1 - ref], sin, pesos=pesos)
            print(f"{'':5s}          | sin prefiltro:   {fmt(sin.resumen())}")


def umbrales(res_validas: list, neg_senas, pesos):
    print("\n== 5. Umbral y margen (aceptadas bien / mal en cruzada+variantes; negativas aceptadas) ==")
    filas = [f for r in res_validas for f in r.filas if f[1]]
    comp = comparador(neg_senas, 0, pesos)
    rng = random.Random(SEMILLA)
    negs, letras = [], []
    piezas = pedazos(neg_senas, rng)
    if ABECEDARIO.exists():
        piezas += deletreo(*cargar_video(ABECEDARIO))
    for tipo, s, origen in piezas:
        cand = P.descriptores(s, pesos=pesos) if len(s) >= 2 else []
        if cand:
            top = comp.mejores(cand, 2)
            # Un pedazo de una palabra reconocido como esa misma palabra no es un invento.
            if top[0][0] not in str(origen).split("+") and comp.categorias[top[0][0]] == "palabra":
                (letras if tipo == "letra" else negs).append(top)
    print("negativas = pedazos y transiciones dichos como OTRA palabra; letras = tramos del abecedario dichos como palabra")
    print(f"{'umbral':>7s} {'margen':>7s} {'bien':>7s} {'mal':>6s} {'negativas':>10s} {'letras':>7s}")
    n_neg = sum(1 for tipo, _, _ in piezas if tipo != "letra")
    n_letras = sum(1 for tipo, _, _ in piezas if tipo == "letra")
    for u in (0.4, 0.5, 0.6, 0.7):
        for m in (0.0, 0.03, 0.05, 0.1):
            bien = sum(t[0][1] >= u and t[0][1] - t[1][1] >= m and t[0][0] == v for v, t, _ in filas)
            mal = sum(t[0][1] >= u and t[0][1] - t[1][1] >= m and t[0][0] != v for v, t, _ in filas)
            neg = sum(t[0][1] >= u and t[0][1] - t[1][1] >= m for t in negs)
            let = sum(t[0][1] >= u and t[0][1] - t[1][1] >= m for t in letras)
            print(f"{u:7.2f} {m:7.2f} {100 * bien / len(filas):6.1f}% {100 * mal / len(filas):5.1f}% "
                  f"{neg:6d}/{n_neg} {let:4d}/{n_letras}")


def velocidad(datos_base, senas):
    print("\n== 6. Velocidad ==")
    from core.cuerpo import desde_arrays
    cat = catalogo()
    e = sorted(datos_base)[0]
    crudos = desde_arrays(np.load(ruta_cache(cat[e]["idw"])))
    inicio = time.perf_counter()
    seg = P.Segmentador()
    for c in crudos:
        seg.actualizar(P.cuadro_palabra(c), c.t)
    por_frame = (time.perf_counter() - inicio) * 1000 / len(crudos)
    print(f"rasgos del cuerpo + segmentador: {por_frame:.2f} ms/frame (MediaPipe manos + pose lite, aparte: "
          f"ver scripts/extraer_cenarec.py; medido ~19 + ~10 ms/frame en un solo proceso)")
    reps = [s for r in senas.values() for s in r]
    d = P.descriptores(reps[0])
    for n in (170, 600, 2144):
        plantillas = [P.descriptor(reps[i % len(reps)], False) for i in range(n)]
        for prefiltro in (None, P.PREFILTRO):
            comp = P.ComparadorPalabras([str(i) for i in range(n)], plantillas, prefiltro=prefiltro)
            inicio = time.perf_counter()
            for _ in range(5):
                comp.mejores(d)
            ms = (time.perf_counter() - inicio) * 1000 / 5
            print(f"clasificar una seña contra {n:5d} plantillas, DTW con {'todas' if not prefiltro else prefiltro:>5}: "
                  f"{ms:6.1f} ms ({len(d)} descriptor/es; una vez por seña)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lista", type=Path, default=LISTA)
    p.add_argument("--solo", nargs="*", choices=("cruzada", "variantes", "negativas", "escala", "umbrales", "velocidad"))
    p.add_argument("--pesos", nargs="+", type=float, help="posición forma ejes no_dominante activa [cara]")
    p.add_argument("--procesos", type=int, default=6)
    p.add_argument("--sin-letras", action="store_true",
                   help="no usar las letras deletreadas de CENAREC (LETRA-*) como plantillas negativas")
    a = p.parse_args(argv)
    secciones = set(a.solo or ("cruzada", "variantes", "negativas", "escala", "umbrales", "velocidad"))
    pesos = tuple(a.pesos) if a.pesos else None

    iniciales = leer_lista(a.lista)
    if not a.sin_letras:
        letras = cargar([e for e in catalogo() if e.startswith("LETRA-")], "base", a.procesos)
        NEGATIVAS_LETRAS.update({e: elegir_reps(P.segmentar(c, t)) for e, (c, t) in letras.items()})
        print(f"Letras deletreadas como negativas: {len(NEGATIVAS_LETRAS)}")
    datos = cargar(iniciales, "base", a.procesos)
    if not datos:
        print("No hay cache: correr scripts/extraer_cenarec.py", file=sys.stderr)
        return 1
    senas = {e: elegir_reps(P.segmentar(c, t)) for e, (c, t) in sorted(datos.items())}
    print(f"{len(senas)} palabras; repeticiones encontradas: "
          f"{dict(Counter(len(P.segmentar(c, t)) for c, t in datos.values()))}")
    validas = []
    if secciones & {"cruzada", "umbrales"}:
        validas.append(cruzada(senas, pesos, "cruzada" in secciones))
    if secciones & {"variantes", "umbrales"}:
        validas += list(variantes(iniciales, senas, datos, pesos, a.procesos).values())
    if "negativas" in secciones:
        negativas(senas, pesos)
    if "umbrales" in secciones:
        umbrales(validas, senas, pesos)
    if "escala" in secciones:
        escala(iniciales, a.procesos, pesos)
    if "velocidad" in secciones:
        velocidad(datos, senas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
