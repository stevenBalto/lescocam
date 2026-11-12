"""Entrena el modelo de señas por similitud con ASL Citizen (problema 1, fase 4).

Datos: data/dictionary/asl_citizen/descriptores_v3.npz (scripts/descriptores_asl.py).

Separación (semilla fija):
  * GLOSAS NUEVAS: --reservar (15 %) de las glosas no se usan para entrenar NUNCA. Son lo que más
    se parece a LESCO: señas que el modelo no vio, de personas que no vio.
  * Entrenamiento: partición train de ASL Citizen, sin las glosas nuevas (35 firmantes).
  * La partición val (6 firmantes que no están en train) y el test de ASL Citizen no se entrenan.

Evaluación (top-1 por coseno; cada video aporta sus variantes de espejo, gana la mejor):
  A. glosas conocidas, firmantes nuevos: consultas = val; galería = 1 video por glosa de train.
  B. GLOSAS NUEVAS (la que importa): galería = 1 video por glosa (como CENAREC: una persona);
     consultas = los demás videos de esas glosas, de otras personas. Se compara con el DTW del
     motor actual y con la SUMA de los dos (parecidos en z por consulta) sobre las mismas consultas.

Por defecto (elegido en la fase 4 con A): 12 épocas, abandono 0.2, weight decay 0.05, margen
ArcFace 0.4. Con más épocas sobreajusta: la pérdida va a ~0 y A deja de subir.
  C. CENAREC: las 85 palabras de senas.db; cada repetición se busca entre las otras.

Uso:
    .venv/Scripts/python -m scripts.entrenar_embedding                 # entrena, evalúa y guarda
    .venv/Scripts/python -m scripts.entrenar_embedding --epocas 5      # prueba corta
Salida: data/dictionary/asl_citizen/modelo/embedding_v1.pt y reporte_v1.json (ignorados por git).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from core import palabras as P
from core import senas_db
from scripts.construir_landmarks_asl import CARPETA
from scripts.descriptores_asl import SALIDA as DESCRIPTORES
from scripts.modelo_senas import CabezaArcFace, ModeloSenas, guardar

MODELO = CARPETA / "modelo" / "embedding_v1.pt"
B = P.BLOQUE
POSICIONES = [0, 1, B, B + 1]                       # muñeca (x, y) de cada brazo
CARA = [B - 2, B - 1, 2 * B - 2, 2 * B - 1]          # posición respecto de la cara
ACTIVA = 2 * B                                       # marca "la no dominante cuenta"


# ------------------------------------------------------------------ datos

def separar(glosas: np.ndarray, particiones: np.ndarray, reservar: float, semilla: int) -> tuple[set, np.ndarray]:
    """(glosas nuevas, máscara de entrenamiento)."""
    rng = np.random.default_rng(semilla)
    todas = np.array(sorted(set(glosas.tolist())))
    nuevas = set(rng.choice(todas, int(round(reservar * len(todas))), replace=False).tolist())
    entrenar = (particiones == "train") & ~np.isin(glosas, list(nuevas))
    return nuevas, entrenar


def galeria_y_consultas(video, glosas, firmantes, mascara, semilla: int) -> tuple[np.ndarray, np.ndarray]:
    """Dentro de `mascara`: 1 video por glosa a la galería (con todas sus variantes) y las filas de
    los videos de OTROS firmantes de esa glosa a consultas. Devuelve (filas galería, filas consulta)."""
    rng = np.random.default_rng(semilla)
    por_glosa = defaultdict(list)
    for i in np.nonzero(mascara)[0]:
        por_glosa[glosas[i]].append(i)
    gal, con = [], []
    for g in sorted(por_glosa):
        filas = por_glosa[g]
        vids = sorted({int(video[i]) for i in filas})
        if len(vids) < 2:
            continue
        elegido = vids[rng.integers(len(vids))]
        firm = firmantes[[i for i in filas if video[i] == elegido][0]]
        gal += [i for i in filas if video[i] == elegido]
        con += [i for i in filas if firmantes[i] != firm]
    return np.array(gal, dtype=np.int64), np.array(con, dtype=np.int64)


# ------------------------------------------------------------------ aumentación (en GPU, por lote)

def aumentar(x: torch.Tensor, gen: torch.Generator) -> torch.Tensor:
    """Variaciones que da otra persona u otra cámara: ritmo, tamaño y lugar de las manos, ruido."""
    b, t, c = x.shape
    dev = x.device
    r = lambda *s: torch.rand(*s, generator=gen, device=dev)
    n = lambda *s: torch.randn(*s, generator=gen, device=dev)
    # ritmo: grilla de tiempo deformada (monótona) e interpolación lineal
    pasos = 0.5 + r(b, t - 1)
    grilla = torch.cat([torch.zeros(b, 1, device=dev), pasos.cumsum(1)], 1)
    grilla = grilla / grilla[:, -1:] * (t - 1)
    i0 = grilla.floor().long().clamp(0, t - 2)
    w = (grilla - i0).unsqueeze(-1)
    g0 = torch.gather(x, 1, i0.unsqueeze(-1).expand(-1, -1, c))
    g1 = torch.gather(x, 1, (i0 + 1).unsqueeze(-1).expand(-1, -1, c))
    y = g0 * (1 - w) + g1 * w
    # tamaño y lugar: escala y corrimiento de las posiciones (otra persona, otro encuadre)
    activa = (x[:, :, ACTIVA:ACTIVA + 1] > 0).float()
    esc = 0.85 + 0.3 * r(b, 1, 1)
    pos = torch.tensor(POSICIONES + CARA, device=dev)
    y[:, :, pos] = y[:, :, pos] * esc
    corr = 0.08 * n(b, 1, 2)
    y[:, :, [0, 1]] += corr
    y[:, :, [B, B + 1]] += corr * activa
    # ruido de MediaPipe, solo donde hay datos (la no dominante inactiva sigue en 0)
    ruido = 0.03 * n(b, t, c)
    ruido[:, :, B:2 * B] *= activa
    if c > P.COLUMNAS:                               # con puntos: dominante (63) y no dominante (63)
        mitad = P.COLUMNAS + (c - P.COLUMNAS) // 2
        y[:, :, mitad:] = y[:, :, mitad:] * activa
        ruido[:, :, mitad:] *= activa
    ruido[:, :, ACTIVA] = 0
    return y + ruido


# ------------------------------------------------------------------ evaluación

@torch.no_grad()
def embeber(modelo, x: np.ndarray, dev: str, lote: int = 4096) -> np.ndarray:
    modelo.eval()
    out = [modelo(torch.from_numpy(x[i:i + lote]).float().to(dev)).cpu().numpy() for i in range(0, len(x), lote)]
    return np.concatenate(out) if out else np.zeros((0, modelo.config["embedding"]), np.float32)


def top1_por_video(sim_glosa: np.ndarray, video_c: np.ndarray, glosa_c: np.ndarray, clases: np.ndarray) -> dict:
    """sim_glosa (filas consulta, clases): parecido de cada fila con cada glosa (mayor = mejor).
    Junta las variantes de un mismo video (gana la mejor) y mide top-1 / top-5 por video."""
    mejor = {}
    for k, v in enumerate(video_c):
        mejor[v] = sim_glosa[k] if v not in mejor else np.maximum(mejor[v], sim_glosa[k])
    verdad = {v: glosa_c[k] for k, v in enumerate(video_c)}
    idx = {g: j for j, g in enumerate(clases)}
    t1 = t5 = 0
    for v, s in mejor.items():
        orden = np.argsort(-s)
        j = idx[verdad[v]]
        t1 += orden[0] == j
        t5 += j in orden[:5]
    n = len(mejor)
    return {"videos": n, "clases": len(clases), "top1": t1 / max(n, 1), "top5": t5 / max(n, 1)}


def sim_por_glosa(sim: np.ndarray, glosa_g: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(consultas, filas galería) -> (consultas, glosas): máximo por glosa."""
    clases = np.array(sorted(set(glosa_g.tolist())))
    salida = np.full((sim.shape[0], len(clases)), -np.inf, dtype=np.float32)
    for j, g in enumerate(clases):
        salida[:, j] = sim[:, glosa_g == g].max(1)
    return salida, clases


def evaluar_embedding(modelo, x, video, glosas, gal, con, dev) -> dict:
    eg, ec = embeber(modelo, x[gal], dev), embeber(modelo, x[con], dev)
    s, clases = sim_por_glosa(ec @ eg.T, glosas[gal])
    return top1_por_video(s, video[con], glosas[con], clases)


def zfilas(s: np.ndarray) -> np.ndarray:
    """Cada fila (una consulta) a media 0 y desvío 1, para sumar parecidos de escalas distintas."""
    return (s - s.mean(1, keepdims=True)) / np.maximum(s.std(1, keepdims=True), 1e-9)


def evaluar_dtw_y_fusion(modelo, x, video, glosas, gal, con, dev, maximo: int = 0,
                         pesos=(0.0, 0.3, 0.5, 0.7, 1.0), semilla: int = 7) -> dict:
    """El motor actual (DTW con los pesos v3), el modelo y la suma de los dos (z por consulta) sobre
    la misma galería y consultas. Clave = peso del modelo (0 = solo DTW, 1 = solo modelo)."""
    if maximo:
        vids = np.array(sorted(set(video[con].tolist())))
        if len(vids) > maximo:
            vids = np.random.default_rng(semilla).choice(vids, maximo, replace=False)
        con = con[np.isin(video[con], vids)]
    w = senas_db.pesos_columnas().astype(np.float64)
    k = P.COLUMNAS                                   # el DTW del motor usa solo el descriptor
    plantillas = x[gal, :, :k].astype(np.float64) * w
    d = np.stack([P.dtw_lote(x[i, :, :k].astype(np.float64) * w, plantillas) for i in con])
    sd, clases = sim_por_glosa(-d, glosas[gal])
    se, _ = sim_por_glosa(embeber(modelo, x[con], dev) @ embeber(modelo, x[gal], dev).T, glosas[gal])
    return {str(a): top1_por_video(a * zfilas(se) + (1 - a) * zfilas(sd), video[con], glosas[con], clases)
            for a in pesos}


def cenarec(ruta_db: Path) -> tuple[np.ndarray, np.ndarray]:
    datos = senas_db.leer(ruta_db)
    cat = {e: v["categoria"] for e, v in datos["palabras"].items()}
    filas = [(e, d) for e, d in datos["plantillas"] if cat.get(e) == "palabra"]
    return np.stack([d for _, d in filas]).astype(np.float32), np.array([e for e, _ in filas])


def evaluar_cenarec(eg: np.ndarray, etiquetas: np.ndarray, dist: np.ndarray | None = None) -> dict:
    """Cada plantilla contra todas las demás (sin sí misma): top-1 de su palabra.
    eg: embeddings (parecido = producto punto) o, con dist, distancias DTW ya calculadas."""
    s = -dist if dist is not None else eg @ eg.T
    np.fill_diagonal(s, -np.inf)
    acierto = [etiquetas[np.argmax(s[i])] == etiquetas[i] for i in range(len(etiquetas))
               if (etiquetas == etiquetas[i]).sum() > 1]
    return {"plantillas": len(acierto), "top1": float(np.mean(acierto)) if acierto else 0.0}


# ------------------------------------------------------------------ entrenamiento

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--datos", type=Path, default=DESCRIPTORES)
    p.add_argument("--salida", type=Path, default=MODELO)
    p.add_argument("--db", type=Path, default=senas_db.RUTA_DB)
    p.add_argument("--epocas", type=int, default=12)
    p.add_argument("--lote", type=int, default=512)
    p.add_argument("--lr", type=float, default=2e-3)
    p.add_argument("--ancho", type=int, default=128)
    p.add_argument("--bloques", type=int, default=4)
    p.add_argument("--margen", type=float, default=0.4)
    p.add_argument("--reservar", type=float, default=0.15)
    p.add_argument("--semilla", type=int, default=7)
    p.add_argument("--abandono", type=float, default=0.2)
    p.add_argument("--wd", type=float, default=0.05, help="weight decay de AdamW")
    p.add_argument("--cada", type=int, default=5, help="evaluar cada N épocas")
    p.add_argument("--sin-aumentar", action="store_true")
    p.add_argument("--dtw-max", type=int, default=800, help="videos de consulta para el DTW de referencia (0 = todos)")
    a = p.parse_args(argv)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(a.semilla)
    d = np.load(a.datos)
    x, video, glosas, firmantes, part = d["x"], d["video"], d["glosas"], d["firmantes"], d["particiones"]
    nuevas, ent = separar(glosas, part, a.reservar, a.semilla)
    clases = np.array(sorted(set(glosas[ent].tolist())))
    y_ent = np.searchsorted(clases, glosas[ent])

    # A: galería solo de train (1 video por glosa) y consultas solo de val (firmantes que no están en train)
    conocidas = np.isin(glosas, clases)
    gal_a, _ = galeria_y_consultas(video, glosas, firmantes, conocidas & (part == "train"), a.semilla)
    con_a = np.nonzero(conocidas & (part == "val") & np.isin(glosas, glosas[gal_a]))[0]
    gal_b, con_b = galeria_y_consultas(video, glosas, firmantes, np.isin(glosas, list(nuevas)), a.semilla)
    if x.shape[2] == P.COLUMNAS:
        cx, ce = cenarec(a.db)
    else:                                            # con puntos: las plantillas salen del cache de CENAREC
        from scripts.entrada_modelo import plantillas_cenarec
        cx, ce = plantillas_cenarec(True)

    modelo = ModeloSenas(columnas=x.shape[2], ancho=a.ancho, bloques=a.bloques, abandono=a.abandono).to(dev)
    xe = torch.from_numpy(x[ent]).float()
    modelo.media.copy_(xe.reshape(-1, x.shape[2]).mean(0).to(dev))
    modelo.desvio.copy_(xe.reshape(-1, x.shape[2]).std(0).clamp_min(1e-3).to(dev))
    cabeza = CabezaArcFace(modelo.config["embedding"], len(clases), margen=a.margen).to(dev)
    params = list(modelo.parameters()) + list(cabeza.parameters())
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=a.wd)
    xe, ye = xe.to(dev), torch.from_numpy(y_ent).long().to(dev)
    pasos = a.epocas * ((len(xe) + a.lote - 1) // a.lote)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, a.lr, total_steps=pasos, pct_start=0.1)
    gen = torch.Generator(device=dev).manual_seed(a.semilla)
    n_param = sum(q.numel() for q in modelo.parameters())
    print(f"{dev} | {n_param:,} parámetros | entrenar {len(xe)} filas, {len(clases)} glosas | glosas nuevas {len(nuevas)} | "
          f"eval A {len(set(video[con_a]))} videos, B {len(set(video[con_b]))} videos / {len(set(glosas[gal_b]))} glosas, "
          f"CENAREC {len(ce)} plantillas", flush=True)

    historia, mejor, inicio = [], (-1.0, None), time.perf_counter()
    for ep in range(1, a.epocas + 1):
        modelo.train()
        orden = torch.randperm(len(xe), device=dev, generator=gen)
        total = 0.0
        for i in range(0, len(xe), a.lote):
            k = orden[i:i + a.lote]
            xb = xe[k] if a.sin_aumentar else aumentar(xe[k], gen)
            perdida = cabeza(modelo(xb), ye[k])
            opt.zero_grad(set_to_none=True)
            perdida.backward()
            torch.nn.utils.clip_grad_norm_(params, 5.0)
            opt.step()
            sched.step()
            total += perdida.item() * len(k)
        if ep % a.cada == 0 or ep == a.epocas or ep == 1:
            ra = evaluar_embedding(modelo, x, video, glosas, gal_a, con_a, dev)
            rb = evaluar_embedding(modelo, x, video, glosas, gal_b, con_b, dev)
            rc = evaluar_cenarec(embeber(modelo, cx, dev), ce)
            historia.append({"epoca": ep, "perdida": total / len(xe), "A": ra["top1"], "B": rb["top1"], "C": rc["top1"]})
            print(f"época {ep:3d} | pérdida {total / len(xe):.3f} | A {ra['top1']:.1%} | B {rb['top1']:.1%} "
                  f"(top5 {rb['top5']:.1%}) | CENAREC {rc['top1']:.1%} | {time.perf_counter() - inicio:.0f} s", flush=True)
            if ra["top1"] > mejor[0]:          # se elige con A (glosas conocidas), no con B ni CENAREC
                mejor = (ra["top1"], {k: v.detach().clone() for k, v in modelo.state_dict().items()}, ep)

    modelo.load_state_dict(mejor[1])
    final = {"A": evaluar_embedding(modelo, x, video, glosas, gal_a, con_a, dev),
             "B": evaluar_embedding(modelo, x, video, glosas, gal_b, con_b, dev),
             "C_cenarec": evaluar_cenarec(embeber(modelo, cx, dev), ce)}
    print("DTW de referencia (motor actual) ...", flush=True)
    w = senas_db.pesos_columnas().astype(np.float64)
    cw = cx[:, :, :P.COLUMNAS].astype(np.float64) * w
    dist_c = np.stack([P.dtw_lote(c, cw) for c in cw])
    final["dtw"] = {"C_cenarec": evaluar_cenarec(None, ce, dist_c)}
    final["B_dtw_y_fusion"] = evaluar_dtw_y_fusion(modelo, x, video, glosas, gal_b, con_b, dev, a.dtw_max, semilla=a.semilla)
    reporte = {"epoca_elegida": mejor[2], "parametros": n_param, "args": {k: str(v) for k, v in vars(a).items()},
               "glosas_nuevas": sorted(nuevas), "historia": historia, "final": final}
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    guardar(modelo, a.salida, {"version_descriptor": P.VERSION_DESCRIPTOR, "reporte": {k: v for k, v in reporte.items()
                                                                                       if k != "glosas_nuevas"}})
    reporte_ruta = a.salida.with_name(a.salida.stem.replace("embedding", "reporte") + ".json")
    if reporte_ruta == a.salida:
        reporte_ruta = a.salida.with_name(a.salida.name + ".reporte.json")
    reporte_ruta.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(final, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
