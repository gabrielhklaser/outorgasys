# -*- coding: utf-8 -*-
"""Mapa interativo: atributos de camadas e nome do poco nao viram HTML.

O GeoJsonTooltip do Folium monta uma tabela por innerHTML e o mapa e exibido
num iframe com scripts e acesso same-origin (ver docstring de ``st.iframe``).
Valor ou nome de coluna com ``<img onerror=...>`` executaria no app.
"""

from __future__ import annotations

import re

import geopandas as gpd
from shapely.geometry import LineString, Polygon

from outorgasys.gis import multicamadas

IMG = '<img src=x onerror="alert(1)">'
SCRIPT = "<script>alert(2)</script>"
LAT, LON = -29.6842, -51.0531


def _chega_como_tag(html: str) -> bool:
    """O payload esta no HTML como tag, em texto puro ou com escape JSON?

    O Folium embute dados de formas diferentes: ora com ``<``, ora com
    ``\\u003c``, que o JavaScript decodifica antes de usar innerHTML.
    """
    return bool(re.search(r"(<|\\u003c)(img src=x|script>alert\(2\))", html))


def _aparece_escapado(html: str) -> bool:
    """O mesmo texto esta presente, mas como entidade (``&lt;`` ou ``\\u0026lt;``)."""
    return bool(re.search(r"(&|\\u0026)lt;img src=x", html))


def _gera(tmp_path, **kw) -> str:
    destino = tmp_path / "mapa.html"
    multicamadas.gerar_mapa_multicamadas(LAT, LON, destino, **kw)
    return destino.read_text(encoding="utf-8")


def _linha(**atributos) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        atributos, geometry=[LineString([(LON - 0.001, LAT), (LON + 0.001, LAT)])],
        crs="EPSG:4326")


def test_valor_de_atributo_da_camada_e_escapado(tmp_path):
    html = _gera(tmp_path, camadas={"drenagem": _linha(nome=[IMG], TIPO=[SCRIPT])})
    assert not _chega_como_tag(html)
    assert _aparece_escapado(html)


def test_nome_do_poco_e_escapado_no_popup_e_na_dica(tmp_path):
    html = _gera(tmp_path, dados_poco={"nome": IMG, "profundidade_total_m": SCRIPT})
    assert not _chega_como_tag(html)
    assert _aparece_escapado(html)


def test_nome_de_coluna_da_propriedade_e_escapado(tmp_path):
    # a camada "propriedade" usa os nomes das colunas como rotulo do tooltip
    prop = gpd.GeoDataFrame(
        {IMG: ["lote 1"]},
        geometry=[Polygon([(LON - .001, LAT - .001), (LON + .001, LAT - .001),
                           (LON + .001, LAT + .001), (LON - .001, LAT + .001)])],
        crs="EPSG:4326")
    html = _gera(tmp_path, camadas={"propriedade": prop})
    assert not _chega_como_tag(html)
    assert "lote 1" in html


def test_camada_dada_como_caminho_tambem_e_escapada(tmp_path):
    arquivo = tmp_path / "dren.geojson"
    _linha(nome=[IMG]).to_file(arquivo, driver="GeoJSON")
    html = _gera(tmp_path, camadas={"drenagem": str(arquivo)})
    assert not _chega_como_tag(html)


def test_texto_comum_continua_legivel(tmp_path):
    html = _gera(tmp_path, camadas={"drenagem": _linha(nome=["Rio dos Sinos"])},
                 dados_poco={"nome": "Poco PT-01"})
    assert "Rio dos Sinos" in html
    assert "Poco PT-01" in html
