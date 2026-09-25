# -*- coding: utf-8 -*-
"""
Motor de Criacao de Mapas em Camadas Distintas (GIS Multicamadas).

Gera mapas interativos com Folium/Leaflet estruturados em grupos tematicos
independentes (FeatureGroup) controlados por LayerControl:
- Mapas Base alternaveis (Satelite Esri, OpenStreetMap, CartoDB Positron, OpenTopoMap)
- Camada do Poco e Raio de Seguranca de 500 m
- Camada da Propriedade / Terreno
- Camada de Geologia Local (unidades litologicas com estilizacao e popups)
- Camada de Hidrogeologia (sistemas aquiferos)
- Camada de Pedologia / Solos
- Camada de Drenagem e Massas d'Agua (IBGE / OSM)
- Camada de Vias e Acessos
- Camada de Pocos Vizinhos e Fontes de Poluicao
- Ferramenta de Medicao Metrica (MeasureControl) e Posicao do Cursor (MousePosition)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import folium
from folium import plugins
import geopandas as gpd
from shapely.geometry import Point, mapping

try:
    from .layer_manipulation import (
        CRS_WGS84_GEO,
        carregar_e_reparar,
        recortar_por_raio,
        sanitizar_atributos_para_geojson,
    )
except ImportError:
    from layer_manipulation import (
        CRS_WGS84_GEO,
        carregar_e_reparar,
        recortar_por_raio,
        sanitizar_atributos_para_geojson,
    )


def criar_mapa_multicamadas(
    lat: float,
    lon: float,
    zoom_inicial: int = 15,
    raio_seguranca_m: float = 500.0,
    camadas_vetoriais: Optional[Dict[str, Any]] = None,
    dados_poco: Optional[Dict[str, Any]] = None,
    titulo: str = "OutorgaSys · Mapa Multicamadas Interativo",
) -> folium.Map:
    """Cria e devolve um mapa Folium completo com camadas tematicas distintas."""
    # 1. Instancia mapa base centrado nas coordenadas
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom_inicial,
        control_scale=True,
        tiles=None,  # Configurado manualmente para multiplos basemaps
    )

    # 2. Basemaps alternaveis
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="🗺️ OpenStreetMap (Padrao)",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="🛰️ Imagem de Satelite (Esri)",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
        name="⚪ CartoDB Positron (Claro)",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="OpenTopoMap",
        name="⛰️ Topografia (OpenTopoMap)",
        overlay=False,
        control=True,
    ).add_to(m)

    # 3. Grupo: Poco e Raio de Seguranca
    fg_poco = folium.FeatureGroup(name="🎯 Poco e Raio de Seguranca (500m)", show=True)

    # Buffer do raio de seguranca
    folium.Circle(
        location=[lat, lon],
        radius=raio_seguranca_m,
        color="#d32f2f",
        weight=2,
        fill=True,
        fill_color="#f44336",
        fill_opacity=0.15,
        tooltip=f"Raio de Seguranca: {raio_seguranca_m:,.0f} m",
    ).add_to(fg_poco)

    # Marcador do Poco
    dados_p = dados_poco or {}
    html_popup = f"""
    <div style="font-family: Arial, sans-serif; font-size: 12px; width: 220px;">
        <h4 style="margin: 0 0 5px 0; color: #1565c0;">💧 {dados_p.get('nome', 'Poco Tubular')}</h4>
        <hr style="margin: 4px 0;"/>
        <b>Latitude:</b> {lat:.6f}°<br/>
        <b>Longitude:</b> {lon:.6f}°<br/>
        <b>Profundidade:</b> {dados_p.get('profundidade_total_m', '-')} m<br/>
        <b>Diametro Util:</b> {dados_p.get('diametro_util_pol', '-')} pol<br/>
        <b>Nivel Estatico:</b> {dados_p.get('nivel_estatico_m', '-')} m<br/>
        <b>Vazao Pretendida:</b> {dados_p.get('vazao_m3h', '-')} m³/h<br/>
    </div>
    """
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(html_popup, max_width=300),
        tooltip=f"Poco: {dados_p.get('nome', 'Ponto de Captacao')}",
        icon=folium.Icon(color="red", icon="tint", prefix="fa"),
    ).add_to(fg_poco)
    fg_poco.add_to(m)

    cv = camadas_vetoriais or {}

    # 4. Grupo: Limite da Propriedade / Terreno
    if "propriedade" in cv and cv["propriedade"] is not None:
        gdf_prop = cv["propriedade"]
        if isinstance(gdf_prop, (str, Path)):
            gdf_prop = carregar_e_reparar(gdf_prop, crs_alvo=CRS_WGS84_GEO)
        elif hasattr(gdf_prop, "to_crs") and gdf_prop.crs != CRS_WGS84_GEO:
            gdf_prop = gdf_prop.to_crs(CRS_WGS84_GEO)

        if not gdf_prop.empty:
            fg_prop = folium.FeatureGroup(name="🏡 Limite da Propriedade", show=True)
            folium.GeoJson(
                gdf_prop,
                name="Propriedade",
                style_function=lambda x: {
                    "fillColor": "#2e7d32",
                    "color": "#1b5e20",
                    "weight": 2.5,
                    "fillOpacity": 0.25,
                    "dashArray": "5, 5",
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[c for c in gdf_prop.columns if c != "geometry"][:4],
                    aliases=[f"{c}: " for c in gdf_prop.columns if c != "geometry"][:4],
                ) if len([c for c in gdf_prop.columns if c != "geometry"]) > 0 else None,
            ).add_to(fg_prop)
            fg_prop.add_to(m)

    # 5. Grupo: Geologia Local
    if "geologia" in cv and cv["geologia"] is not None:
        gdf_geo = cv["geologia"]
        if isinstance(gdf_geo, (str, Path)):
            gdf_geo = carregar_e_reparar(gdf_geo, crs_alvo=CRS_WGS84_GEO)
        elif hasattr(gdf_geo, "to_crs") and gdf_geo.crs != CRS_WGS84_GEO:
            gdf_geo = gdf_geo.to_crs(CRS_WGS84_GEO)

        if not gdf_geo.empty:
            fg_geo = folium.FeatureGroup(name="🪨 Geologia Local (Litologias)", show=False)
            folium.GeoJson(
                sanitizar_atributos_para_geojson(gdf_geo),
                name="Geologia",
                style_function=lambda x: {
                    "fillColor": "#e8d5a3",
                    "color": "#795548",
                    "weight": 1.2,
                    "fillOpacity": 0.45,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[c for c in ["NM_UNIDADE", "SIGLA", "LITOLOGIA", "FORMACAO", "nome", "sigla"] if c in gdf_geo.columns],
                    aliases=["Unidade: ", "Sigla: ", "Litologia: ", "Formacao: ", "Nome: ", "Sigla: "][:len([c for c in ["NM_UNIDADE", "SIGLA", "LITOLOGIA", "FORMACAO", "nome", "sigla"] if c in gdf_geo.columns])],
                ) if any(c in gdf_geo.columns for c in ["NM_UNIDADE", "SIGLA", "LITOLOGIA", "FORMACAO", "nome", "sigla"]) else None,
            ).add_to(fg_geo)
            fg_geo.add_to(m)

    # 6. Grupo: Hidrogeologia / Aquiferos
    if "hidrogeologia" in cv and cv["hidrogeologia"] is not None:
        gdf_hidro = cv["hidrogeologia"]
        if isinstance(gdf_hidro, (str, Path)):
            gdf_hidro = carregar_e_reparar(gdf_hidro, crs_alvo=CRS_WGS84_GEO)
        elif hasattr(gdf_hidro, "to_crs") and gdf_hidro.crs != CRS_WGS84_GEO:
            gdf_hidro = gdf_hidro.to_crs(CRS_WGS84_GEO)

        if not gdf_hidro.empty:
            fg_hidro = folium.FeatureGroup(name="💧 Hidrogeologia (Sistemas Aquiferos)", show=False)
            folium.GeoJson(
                sanitizar_atributos_para_geojson(gdf_hidro),
                name="Hidrogeologia",
                style_function=lambda x: {
                    "fillColor": "#90caf9",
                    "color": "#1976d2",
                    "weight": 1.5,
                    "fillOpacity": 0.4,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[c for c in ["SISTEMA", "AQUIFERO", "SIGLA", "TIPO_AQUIF", "nome"] if c in gdf_hidro.columns],
                ) if any(c in gdf_hidro.columns for c in ["SISTEMA", "AQUIFERO", "SIGLA", "TIPO_AQUIF", "nome"]) else None,
            ).add_to(fg_hidro)
            fg_hidro.add_to(m)

    # 7. Grupo: Solos / Pedologia
    if "solos" in cv and cv["solos"] is not None:
        gdf_solos = cv["solos"]
        if isinstance(gdf_solos, (str, Path)):
            gdf_solos = carregar_e_reparar(gdf_solos, crs_alvo=CRS_WGS84_GEO)
        elif hasattr(gdf_solos, "to_crs") and gdf_solos.crs != CRS_WGS84_GEO:
            gdf_solos = gdf_solos.to_crs(CRS_WGS84_GEO)

        if not gdf_solos.empty:
            fg_solos = folium.FeatureGroup(name="🌱 Solos (Pedologia)", show=False)
            folium.GeoJson(
                sanitizar_atributos_para_geojson(gdf_solos),
                name="Solos",
                style_function=lambda x: {
                    "fillColor": "#d7ccc8",
                    "color": "#5d4037",
                    "weight": 1.0,
                    "fillOpacity": 0.4,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[c for c in ["CLASSE_SOLO", "SIMBOLO", "LEGENDA", "nome"] if c in gdf_solos.columns],
                ) if any(c in gdf_solos.columns for c in ["CLASSE_SOLO", "SIMBOLO", "LEGENDA", "nome"]) else None,
            ).add_to(fg_solos)
            fg_solos.add_to(m)

    # 8. Grupo: Drenagem e Hidrografia (Rios e Massas d'Agua)
    if "drenagem" in cv and cv["drenagem"] is not None:
        gdf_dren = cv["drenagem"]
        if isinstance(gdf_dren, (str, Path)):
            gdf_dren = carregar_e_reparar(gdf_dren, crs_alvo=CRS_WGS84_GEO)
        elif hasattr(gdf_dren, "to_crs") and gdf_dren.crs != CRS_WGS84_GEO:
            gdf_dren = gdf_dren.to_crs(CRS_WGS84_GEO)

        if not gdf_dren.empty:
            fg_dren = folium.FeatureGroup(name="🌊 Drenagem e Hidrografia", show=True)
            folium.GeoJson(
                sanitizar_atributos_para_geojson(gdf_dren),
                name="Drenagem",
                style_function=lambda x: {
                    "color": "#0288d1",
                    "weight": 2.2,
                    "opacity": 0.85,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=[c for c in ["nome", "NOME", "DENOMINACA", "TIPO"] if c in gdf_dren.columns],
                ) if any(c in gdf_dren.columns for c in ["nome", "NOME", "DENOMINACA", "TIPO"]) else None,
            ).add_to(fg_dren)
            fg_dren.add_to(m)

    # 9. Controles complementares
    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    plugins.Fullscreen(position="topleft").add_to(m)
    plugins.MeasureControl(position="bottomleft", primary_length_unit="meters", primary_area_unit="sqmeters").add_to(m)
    plugins.MousePosition(position="bottomright", separator=" | ", empty_string="Coord: -", prefix="Lat/Lon: ").add_to(m)

    return m


def salvar_mapa_html(mapa: folium.Map, destino: str | Path) -> Path:
    """Salva o mapa Folium em arquivo HTML standalone."""
    p = Path(destino)
    p.parent.mkdir(parents=True, exist_ok=True)
    mapa.save(str(p))
    return p
