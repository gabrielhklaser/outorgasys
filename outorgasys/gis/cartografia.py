# -*- coding: utf-8 -*-
"""
Cartografia automatizada (Agente 2).

Produz as tres pranchas exigidas, em PNG/JPG a 300 DPI, todas com titulo
padronizado, coordenadas do poco, norte geografico, escala grafica metrica e
legenda:

* ``mapa_situacao.jpg``    - localizacao e situacao (ponto, limite da propriedade,
  buffer de 500 m, vias de acesso e malha viaria do entorno).
* ``mapa_geologico.jpg``   - contexto geologico local (unidades/formacoes, contatos
  litologicos e o poco sobreposto).
* ``mapa_hidrologico.jpg`` - contexto hidrografico e hidrogeologico (drenagem,
  nascentes, corpos d'agua no raio de 500 m, ottobacia e sistema aquifer).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import patheffects as pe  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, Polygon as MplPolygon  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.offsetbox import AnchoredOffsetbox, TextArea, VPacker  # noqa: E402

from .. import config as C
from . import basemap, geo

CRS_WEB = "EPSG:3857"

# Paletas
COR_AGUA = "#4a90d9"
COR_DRENAGEM = "#2b7bba"
COR_POCO = "#c00000"
COR_BUFFER = "#d94f4f"
COR_PROPRIEDADE = "#2e7d32"
COR_VIA = "#8a8a8a"
COR_POLUICAO = "#e07b00"
COR_GEO = ["#e8d5a3", "#c8b78a", "#d9c9a8", "#bfae86", "#d3c1a5", "#cab98d",
           "#e0d3b3", "#d5c8a0", "#c1b189", "#d8cba6", "#c6b492", "#ded1b0"]
COR_HIDRO = ["#bcd9f2", "#a8cbe8", "#cfe4f7", "#9ec2e0", "#d8eaf9", "#b3d3ef"]


# --------------------------------------------------------------------------------------
# Helpers de prancha
# --------------------------------------------------------------------------------------


def _fig(titulo: str, subtitulo: str):
    fig, ax = plt.subplots(figsize=(C.LARGURA_MAPA_POL, C.ALTURA_MAPA_POL), dpi=C.DPI_MAPAS)
    fig.suptitle(titulo, fontsize=14.5, fontweight="bold", ha="center", y=0.965)
    ax.text(0.5, 1.005, subtitulo, transform=ax.transAxes, ha="center",
            fontsize=9, color="#444444")
    return fig, ax


def _to_web(gdf):
    if gdf is None or not len(gdf):
        return None
    if gdf.crs is None:
        gdf = gdf.set_crs(C.CRS_GEOGRAFICO)
    return gdf.to_crs(CRS_WEB)


def _plot_geometrias(ax, gdf, **kw) -> bool:
    """Plota pontos/linhas/poligonos de forma robusta."""
    if gdf is None or not len(gdf):
        return False
    try:
        g = _to_web(gdf)
        if g is None:
            return False
        g.plot(ax=ax, **kw)
        return True
    except Exception:  # noqa: BLE001
        return False


def _desenhar_poco(ax, ponto_web, raio_m_web: float) -> None:
    ax.plot([ponto_web.x], [ponto_web.y], marker="o", markersize=11,
            color=COR_POCO, markeredgecolor="white", markeredgewidth=1.6, zorder=25)
    ax.plot([ponto_web.x], [ponto_web.y], marker="+", markersize=7,
            color="white", zorder=26)
    ax.annotate(
        "POCO", (ponto_web.x, ponto_web.y),
        textcoords="offset points", xytext=(10, 10), fontsize=9.5, fontweight="bold",
        color=COR_POCO,
        path_effects=[pe.withStroke(linewidth=3, foreground="white")],
        zorder=27,
    )


def _desenhar_buffer(ax, ponto_web, raio_m_web: float, cor: str = COR_BUFFER) -> None:
    ax.add_patch(Circle((ponto_web.x, ponto_web.y), raio_m_web, fill=False,
                        edgecolor=cor, linewidth=1.8, linestyle="--", zorder=18))
    ax.add_patch(Circle((ponto_web.x, ponto_web.y), raio_m_web, fill=True,
                        facecolor=cor, alpha=0.06, edgecolor="none", zorder=6))
    ax.annotate(
        f"Raio de seguranca\n{C.RAIO_SEGURANCA_M:.0f} m (SIOUT RS)",
        (ponto_web.x, ponto_web.y + raio_m_web),
        textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7.8,
        color=cor, fontweight="bold",
        path_effects=[pe.withStroke(linewidth=3, foreground="white")],
        zorder=27,
    )


def _norte(ax, x: float = 0.965, y: float = 0.12) -> None:
    """Norte geografico simples e sempre legivel."""
    ax.annotate(
        "N", xy=(x, y + 0.075), xycoords="axes fraction", ha="center", va="center",
        fontsize=11, fontweight="bold", color="#222222",
    )
    ax.annotate(
        "", xy=(x, y + 0.055), xytext=(x, y - 0.03), xycoords="axes fraction",
        arrowprops={"arrowstyle": "-|>", "color": "#222222", "linewidth": 1.6},
    )


def _escala(ax, lat: float, comprimento_alvo_m: float | None = None) -> None:
    """Escala grafica metrica corrigida pela distorcao do Web Mercator."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    largura_merc = xlim[1] - xlim[0]
    # No Web Mercator, 1 unidade do eixo = cos(lat) metros no terreno.
    metro_para_merc = 1.0 / max(0.2, math.cos(math.radians(lat)))
    largura_m = largura_merc / metro_para_merc

    alvo = comprimento_alvo_m or (largura_m / 5.0)
    bons = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000, 10000]
    escolha = min(bons, key=lambda v: abs(v - alvo))

    comp_merc = escolha * metro_para_merc
    x0 = xlim[0] + 0.03 * largura_merc
    y0 = ylim[0] + 0.04 * (ylim[1] - ylim[0])
    altura = 0.012 * (ylim[1] - ylim[0])

    n_div = 4
    for i in range(n_div):
        xi = x0 + i * (comp_merc / n_div)
        ax.add_patch(plt.Rectangle(
            (xi, y0), comp_merc / n_div, altura,
            facecolor="black" if i % 2 == 0 else "white",
            edgecolor="black", linewidth=0.8, zorder=30))
    for i, rot in enumerate(["0", "", f"{escolha/2:g}", "", f"{escolha:g} m"]):
        xi = x0 + i * (comp_merc / n_div)
        ax.text(xi, y0 + altura * 1.25, rot, ha="center", va="bottom", fontsize=7.2,
                zorder=30)


def _legenda(ax, handles: Sequence[Any], titulo: str = "Legenda",
             loc: str = "lower left") -> None:
    if not handles:
        return
    leg = ax.legend(handles=list(handles), title=titulo, loc=loc, fontsize=7.4,
                    title_fontsize=8.2, framealpha=0.94, edgecolor="#999999",
                    fancybox=False)
    leg.set_zorder(40)


def _rodape(fig, linhas: Sequence[str]) -> None:
    texto = "   |   ".join([t for t in linhas if t])
    fig.text(0.5, 0.028, texto, ha="center", fontsize=7.4, color="#555555")


def _cartucho(ax, info: dict) -> None:
    """Cartucho tecnico no canto superior esquerdo."""
    linhas = [f"{k}: {v}" for k, v in info.items() if v]
    if not linhas:
        return
    txt = "\n".join(linhas)
    ax.text(0.012, 0.985, txt, transform=ax.transAxes, ha="left", va="top",
            fontsize=7.2, color="#111111",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "white",
                  "edgecolor": "#777777", "linewidth": 0.8, "alpha": 0.92},
            zorder=45)


def _salvar(fig, destino: Path, dpi: int = C.DPI_MAPAS) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return destino


def _handle_cor(cor: str, rotulo: str, **kw) -> Any:
    return plt.Rectangle((0, 0), 1, 1, facecolor=cor, edgecolor="#555555",
                         linewidth=0.6, label=rotulo, **kw)


# --------------------------------------------------------------------------------------
# Mapa 1 - Localizacao e situacao
# --------------------------------------------------------------------------------------


def mapa_situacao(destino: Path, contexto: dict) -> Path:
    """Mapa de localizacao: ponto, propriedade, buffer de 500 m, vias e entorno."""
    coord = contexto["coordenadas"]
    lat, lon = coord["lat"], coord["lon"]
    titulo = "MAPA 1 - LOCALIZACAO E SITUACAO DO POCO"
    subtitulo = (f"{contexto.get('nome_poco') or 'Poco'} - "
                 f"{contexto.get('municipio') or '-'}/{contexto.get('uf', 'RS')}")
    fig, ax = _fig(titulo, subtitulo)

    bbox = geo.bbox_ao_redor(lat, lon, C.RAIO_SEGURANCA_M * 3.2)
    bbox = geo.bbox_expandido(bbox, 1.02)

    from shapely.geometry import Point  # noqa: PLC0415
    import geopandas as gpd  # noqa: PLC0415

    pt_geo = gpd.GeoSeries([Point(lon, lat)], crs=C.CRS_GEOGRAFICO)
    pt_web = pt_geo.to_crs(CRS_WEB).iloc[0]
    pt_utm = pt_geo.to_crs(coord["epsg"]).iloc[0]
    raio_web = C.RAIO_SEGURANCA_M / max(0.2, math.cos(math.radians(lat)))

    # ---- limites do mapa -------------------------------------------------------------
    bbox_web = gpd.GeoSeries(
        [__import__("shapely").geometry.box(*bbox)], crs=C.CRS_GEOGRAFICO
    ).to_crs(CRS_WEB).total_bounds
    ax.set_xlim(bbox_web[0], bbox_web[2])
    ax.set_ylim(bbox_web[1], bbox_web[3])

    # ---- basemap ---------------------------------------------------------------------
    bm = basemap.adicionar(ax, tuple(bbox_web))

    handles: list[Any] = []

    # ---- buffer de seguranca ---------------------------------------------------------
    _desenhar_buffer(ax, pt_web, raio_web)
    handles.append(Line2D([], [], color=COR_BUFFER, linewidth=1.8, linestyle="--",
                          label=f"Raio de seguranca ({C.RAIO_SEGURANCA_M:.0f} m)"))

    # ---- limite da propriedade -------------------------------------------------------
    prop = contexto.get("propriedade_gdf")
    if prop is not None and len(prop):
        _plot_geometrias(ax, prop, facecolor="none", edgecolor=COR_PROPRIEDADE,
                         linewidth=2.0, zorder=12)
        handles.append(Line2D([], [], color=COR_PROPRIEDADE, linewidth=2.0,
                              label="Limite da propriedade / terreno"))

    # ---- malha viaria e vias de acesso -----------------------------------------------
    vias = contexto.get("vias_gdf")
    if vias is not None and len(vias):
        _plot_geometrias(ax, vias, color=COR_VIA, linewidth=1.15, zorder=14, alpha=0.95)
        handles.append(Line2D([], [], color=COR_VIA, linewidth=1.4,
                              label="Malha viaria / vias de acesso (OSM)"))

    # ---- corpos d'agua do entorno ----------------------------------------------------
    agua = contexto.get("corpos_dagua_gdf")
    if agua is not None and len(agua):
        _plot_geometrias(ax, agua, color=COR_AGUA, alpha=0.55, zorder=13)
        handles.append(_handle_cor(COR_AGUA, "Corpos d'agua", alpha=0.75))

    # ---- sede municipal (referencia de localizacao) -----------------------------------
    sede = contexto.get("municipio_gdf")
    if sede is not None and len(sede):
        _plot_geometrias(ax, sede, facecolor="none", edgecolor="#777777",
                         linewidth=1.4, linestyle="-.", zorder=11)
        handles.append(Line2D([], [], color="#777777", linewidth=1.4, linestyle="-.",
                              label=f"Limite municipal ({contexto.get('municipio')})"))

    # ---- ponto do poco ----------------------------------------------------------------
    _desenhar_poco(ax, pt_web, raio_web)
    handles.append(Line2D([], [], color=COR_POCO, marker="o", linestyle="",
                          markersize=8, markeredgecolor="white",
                          label="Poco (ponto de captacao)"))

    ax.set_axis_off()
    _norte(ax)
    _escala(ax, lat)
    _legenda(ax, handles)
    _cartucho(ax, {
        "Coordenadas (SIRGAS 2000)": f"{lat:.6f}, {lon:.6f}",
        "UTM fuso " + coord.get("fuso", "22S"): f"E {coord['utm_e']:.1f} m  N {coord['utm_n']:.1f} m",
        "Municipio": contexto.get("municipio"),
        "Requerente": contexto.get("requerente"),
    })
    _rodape(fig, [
        bm.rotulo,
        "Projecao: Web Mercator (EPSG:3857) para a base; distancias em UTM SIRGAS 2000 "
        f"fuso {coord.get('fuso', '22S')}",
        f"Escala aproximada 1:{contexto.get('escala_aprox', '-')}",
    ])
    return _salvar(fig, destino)


# --------------------------------------------------------------------------------------
# Mapa 2 - Geologico local
# --------------------------------------------------------------------------------------


def mapa_geologico(destino: Path, contexto: dict) -> Path:
    """Mapa geologico: unidades semi-transparentes, contatos e o poco."""
    coord = contexto["coordenadas"]
    lat, lon = coord["lat"], coord["lon"]
    titulo = "MAPA 2 - CONTEXTO GEOLOGICO LOCAL"
    subtitulo = (f"Unidades e formacoes geologicas - "
                 f"{contexto.get('municipio') or '-'}/{contexto.get('uf', 'RS')}")
    fig, ax = _fig(titulo, subtitulo)

    import geopandas as gpd  # noqa: PLC0415
    from shapely.geometry import Point  # noqa: PLC0415

    bbox = geo.bbox_ao_redor(lat, lon, C.RAIO_SEGURANCA_M * 3.2)
    bbox = geo.bbox_expandido(bbox, 1.02)
    bbox_web = gpd.GeoSeries(
        [__import__("shapely").geometry.box(*bbox)], crs=C.CRS_GEOGRAFICO
    ).to_crs(CRS_WEB).total_bounds
    ax.set_xlim(bbox_web[0], bbox_web[2])
    ax.set_ylim(bbox_web[1], bbox_web[3])

    bm = basemap.adicionar(ax, tuple(bbox_web))
    handles: list[Any] = []

    geo_gdf = contexto.get("geologia_gdf")
    if geo_gdf is not None and len(geo_gdf):
        g = _to_web(geo_gdf).copy()
        g = g[g.geometry.intersects(gpd.GeoSeries(
            [__import__("shapely").geometry.box(*bbox_web)], crs=CRS_WEB).iloc[0])]
        # atributo de agrupamento
        col = contexto.get("geologia_campo_rotulo") or "Name"
        if col not in g.columns:
            col = "Name" if "Name" in g.columns else g.columns[0]
        g["_rotulo"] = g[col].astype(str).fillna("-")
        unidades = sorted(g["_rotulo"].unique().tolist())
        cores = {u: COR_GEO[i % len(COR_GEO)] for i, u in enumerate(unidades)}
        g["_cor"] = g["_rotulo"].map(cores)
        g.plot(ax=ax, color=g["_cor"], alpha=0.55, edgecolor="#6b5a3a",
               linewidth=0.8, zorder=10)
        # contatos litologicos
        g.boundary.plot(ax=ax, color="#5a4a2a", linewidth=1.0, zorder=11)
        for u in unidades[:14]:
            handles.append(_handle_cor(cores[u], str(u)[:52], alpha=0.55))
        if len(unidades) > 14:
            handles.append(Line2D([], [], color="none",
                                  label=f"... e outras {len(unidades) - 14} unidades"))
        handles.append(Line2D([], [], color="#5a4a2a", linewidth=1.0,
                              label="Contato litologico"))

    falhas = contexto.get("falhas_gdf")
    if falhas is not None and len(falhas):
        _plot_geometrias(ax, falhas, color="#8b0000", linewidth=1.6,
                         linestyle=(0, (6, 3)), zorder=13)
        handles.append(Line2D([], [], color="#8b0000", linewidth=1.6,
                              linestyle=(0, (6, 3)),
                              label="Falhas / fraturas estruturais"))

    _desenhar_buffer(ax, gpd.GeoSeries([Point(lon, lat)], crs=C.CRS_GEOGRAFICO)
                     .to_crs(CRS_WEB).iloc[0],
                     C.RAIO_SEGURANCA_M / max(0.2, math.cos(math.radians(lat))),
                     cor="#8b4513")
    handles.append(Line2D([], [], color="#8b4513", linewidth=1.8, linestyle="--",
                          label=f"Raio de seguranca ({C.RAIO_SEGURANCA_M:.0f} m)"))

    pt_web = gpd.GeoSeries([Point(lon, lat)], crs=C.CRS_GEOGRAFICO).to_crs(CRS_WEB).iloc[0]
    _desenhar_poco(ax, pt_web, C.RAIO_SEGURANCA_M / max(0.2, math.cos(math.radians(lat))))
    handles.append(Line2D([], [], color=COR_POCO, marker="o", linestyle="",
                          markersize=8, markeredgecolor="white", label="Poco"))

    ax.set_axis_off()
    _norte(ax)
    _escala(ax, lat)
    _legenda(ax, handles)
    _cartucho(ax, {
        "Formacao geologica": contexto.get("formacao_geologica"),
        "Litologia predominante": contexto.get("litologia"),
        "Fonte vetorial": contexto.get("fonte_geologia"),
        "Coordenadas": f"{lat:.6f}, {lon:.6f}",
    })
    _rodape(fig, [
        bm.rotulo,
        "Unidades geologicas em poligonos semi-transparentes sobre a imagem de fundo",
        "Projecao: Web Mercator (EPSG:3857); distancias em UTM SIRGAS 2000",
    ])
    return _salvar(fig, destino)


# --------------------------------------------------------------------------------------
# Mapa 3 - Hidrografico e hidrogeologico
# --------------------------------------------------------------------------------------


def mapa_hidrologico(destino: Path, contexto: dict) -> Path:
    """Mapa hidrografico/hidrogeologico: drenagem, nascentes, ottobacia, aquifer."""
    coord = contexto["coordenadas"]
    lat, lon = coord["lat"], coord["lon"]
    titulo = "MAPA 3 - CONTEXTO HIDROGRAFICO E HIDROGEOLOGICO LOCAL"
    subtitulo = (f"Rede de drenagem, corpos d'agua e sistema aquifer - "
                 f"{contexto.get('municipio') or '-'}/{contexto.get('uf', 'RS')}")
    fig, ax = _fig(titulo, subtitulo)

    import geopandas as gpd  # noqa: PLC0415
    from shapely.geometry import Point  # noqa: PLC0415
    import shapely  # noqa: PLC0415

    raio = C.RAIO_SEGURANCA_M * 3.2
    bbox = geo.bbox_ao_redor(lat, lon, raio)
    bbox = geo.bbox_expandido(bbox, 1.02)
    bbox_web = gpd.GeoSeries([shapely.geometry.box(*bbox)],
                             crs=C.CRS_GEOGRAFICO).to_crs(CRS_WEB).total_bounds
    ax.set_xlim(bbox_web[0], bbox_web[2])
    ax.set_ylim(bbox_web[1], bbox_web[3])

    bm = basemap.adicionar(ax, tuple(bbox_web))
    handles: list[Any] = []

    # ---- ottobacia / area de contribuicao --------------------------------------------
    otto = contexto.get("ottobacia_gdf")
    if otto is not None and len(otto):
        _plot_geometrias(ax, otto, facecolor="#cfe4f7", alpha=0.30,
                         edgector="#4a90d9", edgecolor="#4a90d9", linewidth=1.2,
                         linestyle="--", zorder=8)
        handles.append(_handle_cor("#cfe4f7", "Ottobacia / area de contribuicao",
                                   alpha=0.5))

    # ---- sistema aquifer (dominio hidrogeologico) ------------------------------------
    aq = contexto.get("aquifero_gdf")
    if aq is not None and len(aq):
        g = _to_web(aq)
        col = contexto.get("aquifero_campo_rotulo") or "Name"
        if col not in g.columns:
            col = "Name" if "Name" in g.columns else g.columns[0]
        g = g.copy()
        g["_rotulo"] = g[col].astype(str).fillna("-")
        unidades = sorted(g["_rotulo"].unique().tolist())
        cores = {u: COR_HIDRO[i % len(COR_HIDRO)] for i, u in enumerate(unidades)}
        g.plot(ax=ax, color=g["_rotulo"].map(cores), alpha=0.35,
               edgecolor="none", zorder=9)
        for u in unidades[:10]:
            handles.append(_handle_cor(cores[u], f"Aquifero: {str(u)[:44]}", alpha=0.45))

    # ---- rede de drenagem -------------------------------------------------------------
    drenagem = contexto.get("drenagem_gdf")
    if drenagem is not None and len(drenagem):
        _plot_geometrias(ax, drenagem, color=COR_DRENAGEM, linewidth=1.6, zorder=15)
        handles.append(Line2D([], [], color=COR_DRENAGEM, linewidth=1.8,
                              label="Rede de drenagem (rios, arroios)"))

    # ---- corpos d'agua ----------------------------------------------------------------
    agua = contexto.get("corpos_dagua_gdf")
    if agua is not None and len(agua):
        _plot_geometrias(ax, agua, color=COR_AGUA, alpha=0.60, zorder=14)
        handles.append(_handle_cor(COR_AGUA, "Corpos d'agua", alpha=0.7))

    # ---- nascentes --------------------------------------------------------------------
    nasc = contexto.get("nascentes_gdf")
    if nasc is not None and len(nasc):
        g = _to_web(nasc)
        if g is not None:
            g.plot(ax=ax, marker="^", color="#00695c", markersize=42, zorder=17)
            handles.append(Line2D([], [], color="#00695c", marker="^", linestyle="",
                                  markersize=7, label="Nascentes"))

    # ---- fonts de poluicao ------------------------------------------------------------
    pol = contexto.get("fontes_poluicao_gdf")
    if pol is not None and len(pol):
        _plot_geometrias(ax, pol, facecolor=COR_POLUICAO, alpha=0.55,
                         edgecolor="#a05a00", linewidth=1.0, zorder=16)
        handles.append(_handle_cor(COR_POLUICAO, "Fonte potencial de poluicao", alpha=0.6))

    # ---- buffer de 500 m ---------------------------------------------------------------
    _desenhar_buffer(ax, gpd.GeoSeries([Point(lon, lat)], crs=C.CRS_GEOGRAFICO)
                     .to_crs(CRS_WEB).iloc[0],
                     C.RAIO_SEGURANCA_M / max(0.2, math.cos(math.radians(lat))))
    handles.append(Line2D([], [], color=COR_BUFFER, linewidth=1.8, linestyle="--",
                          label=f"Raio de seguranca ({C.RAIO_SEGURANCA_M:.0f} m)"))

    # ---- corpo hidrico mais proximo ---------------------------------------------------
    corpo = (contexto.get("corpo_hidrico_proximo") or {})
    if corpo.get("distancia_m") is not None and corpo.get("linha_gdf") is not None:
        _plot_geometrias(ax, corpo["linha_gdf"], color="#006400", linewidth=3.0,
                         zorder=18)
        handles.append(Line2D([], [], color="#006400", linewidth=3.0,
                              label=f"Corpo hidrico mais proximo: {corpo.get('nome')} "
                                    f"({corpo['distancia_m']:.1f} m)"))

    pt_web = gpd.GeoSeries([Point(lon, lat)], crs=C.CRS_GEOGRAFICO).to_crs(CRS_WEB).iloc[0]
    _desenhar_poco(ax, pt_web, C.RAIO_SEGURANCA_M / max(0.2, math.cos(math.radians(lat))))
    handles.append(Line2D([], [], color=COR_POCO, marker="o", linestyle="",
                          markersize=8, markeredgecolor="white", label="Poco"))

    ax.set_axis_off()
    _norte(ax)
    _escala(ax, lat)
    _legenda(ax, handles)
    _cartucho(ax, {
        "Regiao hidrografica": contexto.get("regiao_hidrografica"),
        "Bacia hidrografica": contexto.get("bacia_hidrografica"),
        "Sistema aquifer": contexto.get("sistema_aquifero"),
        "Corpo hidrico proximo": (f"{corpo.get('nome')} - {corpo['distancia_m']:.1f} m"
                                  if corpo.get("distancia_m") is not None else None),
    })
    _rodape(fig, [
        bm.rotulo,
        f"Drenagem: {contexto.get('fonte_drenagem') or 'nao disponivel'}",
        "Projecao: Web Mercator (EPSG:3857); distancias em UTM SIRGAS 2000",
    ])
    return _salvar(fig, destino)


# --------------------------------------------------------------------------------------
# API de conveniencia
# --------------------------------------------------------------------------------------


def gerar_todos(destino_dir: Path, contexto: dict) -> dict[str, str]:
    """Gera as tres pranchas e devolve {nome_logico: caminho}."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    return {
        "mapa_situacao": str(mapa_situacao(destino_dir / "mapa_situacao.jpg", contexto)),
        "mapa_geologico": str(mapa_geologico(destino_dir / "mapa_geologico.jpg", contexto)),
        "mapa_hidrologico": str(mapa_hidrologico(destino_dir / "mapa_hidrologico.jpg", contexto)),
    }
