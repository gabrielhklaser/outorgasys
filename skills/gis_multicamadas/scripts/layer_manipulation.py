# -*- coding: utf-8 -*-
"""
Manipulacao e preparacao de camadas espaciais vetoriais (GIS Multicamadas).

Fornece:
- Validacao e reparo de geometrias (make_valid, buffer(0))
- Reprojecao e harmonizacao de CRS (SIRGAS 2000 EPSG:4674, UTM 22S EPSG:31982, Web Mercator EPSG:3857)
- Filtragem e recorte espacial por bounding box ou raio de seguranca (buffer circular)
- Padronizacao de atributos e limpeza de geometrias nulas/vazias
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
from shapely.validation import make_valid

CRS_SIRGAS_GEO = "EPSG:4674"
CRS_SIRGAS_UTM22S = "EPSG:31982"
CRS_WEB_MERCATOR = "EPSG:3857"
CRS_WGS84_GEO = "EPSG:4326"


def carregar_e_reparar(caminho: str | Path, crs_alvo: str = CRS_SIRGAS_GEO) -> gpd.GeoDataFrame:
    """Carrega arquivo vetorial (GPKG, SHP, GeoJSON, KML) e repara geometrias invalidas."""
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo vetorial nao encontrado: {p}")

    gdf = gpd.read_file(p)
    if gdf.empty:
        return gdf

    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_SIRGAS_GEO)

    # Limpa geometrias nulas ou vazias
    gdf = gdf[~gdf.geometry.isna() & ~gdf.geometry.is_empty].copy()

    # Reparação topológica
    invalid_mask = ~gdf.geometry.is_valid
    if invalid_mask.any():
        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].apply(
            lambda geom: make_valid(geom) if geom is not None else None
        )

    if crs_alvo and gdf.crs != crs_alvo:
        gdf = gdf.to_crs(crs_alvo)

    return gdf


def recortar_por_raio(gdf: gpd.GeoDataFrame, ponto_lat: float, ponto_lon: float,
                      raio_metros: float, crs_utm: str = CRS_SIRGAS_UTM22S) -> gpd.GeoDataFrame:
    """Recorta um GeoDataFrame dentro de um raio circular em metros ao redor do ponto."""
    if gdf.empty:
        return gdf

    pt_geo = gpd.GeoSeries([Point(ponto_lon, ponto_lat)], crs=CRS_SIRGAS_GEO)
    pt_utm = pt_geo.to_crs(crs_utm).iloc[0]
    buffer_utm = pt_utm.buffer(raio_metros)
    buffer_geo = gpd.GeoSeries([buffer_utm], crs=crs_utm).to_crs(gdf.crs).iloc[0]

    # Interseção espacial
    recortado = gdf[gdf.geometry.intersects(buffer_geo)].copy()
    return recortado


def sanitizar_atributos_para_geojson(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Garante que todos os atributos sejam compativeis com GeoJSON/Folium."""
    copia = gdf.copy()
    for col in copia.columns:
        if col == "geometry":
            continue
        if pd.api.types.is_datetime64_any_dtype(copia[col]):
            copia[col] = copia[col].astype(str)
        elif copia[col].dtype == object:
            copia[col] = copia[col].apply(
                lambda v: str(v) if v is not None and not pd.isna(v) else ""
            )
    return copia
