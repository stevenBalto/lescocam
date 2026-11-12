"""Modelo de señas por similitud (problema 1, fase 4): descriptor v3 -> vector de EMBEDDING números.

Entrada: el descriptor CRUDO del motor (core/palabras.descriptor con PESOS_CRUDOS, el mismo que
guarda senas.db), (MUESTRAS=24, COLUMNAS=83). Salida: vector de norma 1; dos señas se parecen
si su producto punto (coseno) es alto. Se reconoce buscando la plantilla de CENAREC más parecida.

Red chica (~0,3 M parámetros) para que entre en el celular más adelante (ONNX/TFLite, fase 5):
    normalización por columna (media y desvío de entrenamiento, guardados en el modelo)
    -> Linear(83, ANCHO) -> BLOQUES convoluciones temporales residuales (k=5, dilatación 1, 2, 4...)
    -> pooling (media + máximo en el tiempo) -> Linear -> L2

Solo usa PyTorch (requirements-train.txt). Licencia: los pesos salen de ASL Citizen (solo
investigación no comercial); se guardan en data/dictionary/asl_citizen/modelo/ (ignorado por
git) y NO se distribuyen hasta revisar la licencia.
"""
from __future__ import annotations

import json

import torch
from torch import nn
from torch.nn import functional as F

EMBEDDING = 128


class Bloque(nn.Module):
    def __init__(self, ancho: int, dilatacion: int, abandono: float):
        super().__init__()
        self.norma = nn.LayerNorm(ancho)
        self.conv1 = nn.Conv1d(ancho, ancho, 5, padding=2 * dilatacion, dilation=dilatacion)
        self.conv2 = nn.Conv1d(ancho, ancho, 1)
        self.abandono = nn.Dropout(abandono)

    def forward(self, x):                      # x (B, T, C)
        y = self.norma(x).transpose(1, 2)
        y = self.conv2(F.gelu(self.conv1(y))).transpose(1, 2)
        return x + self.abandono(y)


class ModeloSenas(nn.Module):
    def __init__(self, columnas: int = 83, ancho: int = 128, bloques: int = 4, embedding: int = EMBEDDING,
                 abandono: float = 0.1):
        super().__init__()
        self.config = {"columnas": columnas, "ancho": ancho, "bloques": bloques, "embedding": embedding,
                       "abandono": abandono}
        self.register_buffer("media", torch.zeros(columnas))
        self.register_buffer("desvio", torch.ones(columnas))
        self.entrada = nn.Linear(columnas, ancho)
        self.bloques = nn.ModuleList([Bloque(ancho, 2 ** (i % 3), abandono) for i in range(bloques)])
        self.norma = nn.LayerNorm(2 * ancho)
        self.salida = nn.Linear(2 * ancho, embedding)

    def forward(self, x):                      # x (B, T, columnas) crudo
        x = (x - self.media) / self.desvio
        h = self.entrada(x)
        for b in self.bloques:
            h = b(h)
        h = torch.cat([h.mean(1), h.amax(1)], dim=1)
        return F.normalize(self.salida(self.norma(h)), dim=1)


class CabezaArcFace(nn.Module):
    """Clasificador con margen angular aditivo (ArcFace): junta la misma glosa de firmantes distintos."""

    def __init__(self, embedding: int, clases: int, escala: float = 30.0, margen: float = 0.25):
        super().__init__()
        self.pesos = nn.Parameter(torch.randn(clases, embedding) * 0.01)
        self.escala, self.margen = escala, margen

    def forward(self, e, y):
        cos = e @ F.normalize(self.pesos, dim=1).T
        theta = torch.acos(cos.clamp(-1 + 1e-6, 1 - 1e-6))
        # con theta + margen > pi el coseno deja de bajar: ahí se usa la forma lineal de siempre
        objetivo = torch.where(theta + self.margen < torch.pi, torch.cos(theta + self.margen),
                               cos - self.margen * torch.sin(torch.tensor(self.margen)))
        uno = F.one_hot(y, cos.shape[1]).bool()
        return F.cross_entropy(self.escala * torch.where(uno, objetivo, cos), y)


def guardar(modelo: ModeloSenas, ruta, extra: dict | None = None) -> None:
    # extra va como texto JSON: torch.load(weights_only=True) no acepta tipos de numpy
    texto = json.dumps(extra or {}, ensure_ascii=False, default=lambda v: v.item() if hasattr(v, "item") else str(v))
    torch.save({"config": modelo.config, "estado": modelo.state_dict(), "extra": texto}, ruta)


def cargar(ruta, dispositivo: str = "cpu") -> ModeloSenas:
    d = torch.load(ruta, map_location=dispositivo, weights_only=True)
    m = ModeloSenas(**d["config"])
    m.load_state_dict(d["estado"])
    return m.eval().to(dispositivo)
