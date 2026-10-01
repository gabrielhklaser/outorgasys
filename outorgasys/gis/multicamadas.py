# -*- coding: utf-8 -*-
"""
Modulo de Integracao de Mapas Multicamadas (Skill gis-multicamadas).

Gera o mapa interativo HTML standalone com controle de camadas (LayerControl),
alternancia de imagens de satelite e bases analiticas, buffer de raio de seguranca,
geologia, hidrogeologia, solos, drenagem e medicao metrica.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .. import config as C

try:
    import folium
    from folium import plugins
    _FOLIUM_AVAILABLE = True
except ImportError:
    _FOLIUM_AVAILABLE = False


def _escapar_valor(v: Any) -> Any:
    """Escapa para HTML um valor de atributo; numeros e nulos passam como estao."""
    if isinstance(v, str):
        return html.escape(v)
    if isinstance(v, (dict, list, tuple)):
        return html.escape(json.dumps(v, ensure_ascii=False, default=str))
    return v


def _escapar_camada(gdf):
    """Copia do GeoDataFrame com nomes de coluna e textos escapados para HTML.

    O Folium monta tooltip e popup por innerHTML com estes valores, e o mapa roda
    num iframe com scripts. Atributos de camadas enviadas pelo usuario ou lidas
    do OSM nao podem chegar la como markup.
    """
    import pandas as pd  # noqa: PLC0415

    geom = gdf.geometry.name
    copia = gdf.rename(columns={c: html.escape(str(c)) for c in gdf.columns if c != geom})
    for c in copia.columns:
        if c == geom:
            continue
        if copia[c].dtype == object or pd.api.types.is_string_dtype(copia[c]):
            copia[c] = copia[c].map(_escapar_valor)
    return copia


def gerar_mapa_multicamadas(
    lat: float,
    lon: float,
    destino_html: str | Path,
    raio_seguranca_m: float = C.RAIO_SEGURANCA_M,
    camadas: Optional[Dict[str, Any]] = None,
    dados_poco: Optional[Dict[str, Any]] = None,
    titulo: str = "OutorgaSys · Mapa Multicamadas Interativo",
) -> Path:
    """Gera e salva o mapa interativo multicamadas em HTML standalone."""
    if not _FOLIUM_AVAILABLE:
        raise RuntimeError("Biblioteca folium nao instalada para gerar mapa interativo.")

    import sys
    import importlib.util

    script_path = C.ROOT / "skills" / "gis-multicamadas" / "scripts" / "multicamadas_map.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Script multicamadas_map.py nao encontrado em {script_path}")

    parent_dir = str(script_path.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    spec = importlib.util.spec_from_file_location("multicamadas_map", str(script_path))
    mm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mm)

    camadas_seguras: Dict[str, Any] = {}
    for nome, camada in (camadas or {}).items():
        if isinstance(camada, (str, Path)):
            camada = mm.carregar_e_reparar(camada, crs_alvo=mm.CRS_WGS84_GEO)
        camadas_seguras[nome] = _escapar_camada(camada) if camada is not None else None
    poco_seguro = {k: _escapar_valor(v) for k, v in (dados_poco or {}).items()}

    mapa = mm.criar_mapa_multicamadas(
        lat=lat,
        lon=lon,
        zoom_inicial=15,
        raio_seguranca_m=raio_seguranca_m,
        camadas_vetoriais=camadas_seguras,
        dados_poco=poco_seguro,
        titulo=titulo,
    )

    dest = Path(destino_html)
    return mm.salvar_mapa_html(mapa, dest)
