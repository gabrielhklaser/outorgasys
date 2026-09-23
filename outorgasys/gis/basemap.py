# -*- coding: utf-8 -*-
"""
Basemap para as pranchas cartograficas.

Tenta obter imagem de satelite / mapa de vias via ``contextily``. Quando nao ha
rede (o caso de ambientes sandboxados), desenha um fundo cartografico sintetico
quadriculado e **sinaliza explicitamente** ao chamador que a base e sintetica -
o relatorio nunca apresenta fundo sintetico como se fosse imagem real.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .. import config as C

CACHE_TILES = C.DATA / "cache" / "tiles"


class BasemapResult:
    def __init__(self, imagem=None, extensao=None, provedor: str = "",
                 sintetico: bool = True, mensagem: str = ""):
        self.imagem = imagem
        self.extensao = extensao
        self.provedor = provedor
        self.sintetico = sintetico
        self.mensagem = mensagem

    @property
    def rotulo(self) -> str:
        if self.sintetico:
            return "Fundo cartografico sintetico (sem rede para obter imagem de satelite)"
        return f"Imagem de base: {self.provedor}"


def _provedores():
    """Lista de provedores em ordem de preferencia."""
    try:
        import xyzservices.providers as p  # noqa: PLC0415

        saida = []
        for nome in ("Esri.WorldImagery", "OpenStreetMap.Mapnik", "CartoDB.Positron"):
            obj = p
            for parte in nome.split("."):
                obj = getattr(obj, parte, None)
                if obj is None:
                    break
            if obj is not None:
                saida.append((nome, obj))
        return saida
    except Exception:  # noqa: BLE001
        return []


def obter(imagem_de_rede: bool = True, usar_cache: bool = True) -> BasemapResult:
    """Resolve o provedor de basemap disponivel, sem baixar nada ainda."""
    if not imagem_de_rede:
        return BasemapResult(sintetico=True, mensagem="Basemap desativado por configuracao.")
    provs = _provedores()
    if not provs:
        return BasemapResult(sintetico=True,
                             mensagem="xyzservices indisponivel; usando fundo sintetico.")
    nome, obj = provs[0]
    return BasemapResult(provedor=nome, sintetico=False)


def adicionar(ax, bbox_webmercator: tuple[float, float, float, float],
              resultado: BasemapResult | None = None,
              alpha: float = 0.85, zorder: int = 0) -> BasemapResult:
    """Desenha o basemap no eixo informado (coordenadas ja em Web Mercator)."""
    import matplotlib.pyplot as plt  # noqa: PLC0415

    res = resultado or obter()
    if not res.sintetico:
        try:
            import contextily as cx  # noqa: PLC0415

            provs = dict(_provedores())
            cx.add_basemap(ax, crs="EPSG:3857", source=provs[res.provedor],
                           zoom="auto", alpha=alpha, zorder=zorder,
                           attribution=False, reset_extent=False)
            return BasemapResult(provedor=res.provedor, sintetico=False,
                                 mensagem="Basemap obtido via contextily.")
        except Exception as exc:  # noqa: BLE001
            res = BasemapResult(sintetico=True,
                                mensagem=f"contextily indisponivel: {type(exc).__name__}: {exc}")

    _fundo_sintetico(ax, bbox_webmercator)
    return res


def _fundo_sintetico(ax, bbox: tuple[float, float, float, float]) -> None:
    """Grade metrica + faixas de relevo neutras, para o mapa nao ficar vazio."""
    import matplotlib.pyplot as plt  # noqa: PLC0415
    from matplotlib.patches import Rectangle  # noqa: PLC0415

    minx, miny, maxx, maxy = bbox
    ax.set_facecolor("#f4f1ea")
    passo = (maxx - minx) / 20.0
    if passo <= 0:
        passo = 1.0

    # Mosaico suave
    x = minx
    col = 0
    while x < maxx:
        y = miny
        lin = 0
        while y < maxy:
            if (lin + col) % 2 == 0:
                ax.add_patch(Rectangle((x, y), passo, passo, facecolor="#eae5d9",
                                       edgecolor="none", zorder=0))
            y += passo
            lin += 1
        x += passo
        col += 1

    # Grade metrica de referencia
    for i in range(1, 20):
        gx = minx + i * passo
        ax.plot([gx, gx], [miny, maxy], color="#cfc7b5", linewidth=0.35, zorder=1)
        gy = miny + i * passo
        ax.plot([minx, maxx], [gy, gy], color="#cfc7b5", linewidth=0.35, zorder=1)
