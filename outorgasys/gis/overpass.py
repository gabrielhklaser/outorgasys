# -*- coding: utf-8 -*-
"""Cliente minimo para a API Overpass (OpenStreetMap), com degradacao graciosa."""

from __future__ import annotations

import time
from typing import Any

import requests

ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

TIMEOUT_S = 90

# Consulta alinhada as necessidades do Agente 2:
#   * malha viaria                      -> Mapa 1 (vias de acesso e entorno)
#   * hidrografia (rios/arroyos/canais) -> Mapa 3 (corpos d'agua no raio de 500 m)
#   * nascentes                         -> Mapa 3
#   * fontes potenciais de poluicao     -> cruzamento do buffer de seguranca
QUERY = """
[out:json][timeout:{timeout}];
(
  way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified|residential|living_street|service)$"](around:{radius},{lat},{lon});
  way["waterway"~"^(river|riverbank|stream|canal|drain)$"](around:{radius},{lat},{lon});
  way["natural"="water"](around:{radius},{lat},{lon});
  node["natural"="spring"](around:{radius},{lat},{lon});
  node["amenity"~"^(fuel|wastewater_plant|recycling)$"](around:{radius},{lat},{lon});
  way["amenity"~"^(fuel|wastewater_plant)$"](around:{radius},{lat},{lon});
  way["landuse"~"^(landfill|industrial|quarry|brownfield)$"](around:{radius},{lat},{lon});
  way["man_made"="storage_tank"](around:{radius},{lat},{lon});
  way["industrial"~"^(oil|chemical|refinery)$"](around:{radius},{lat},{lon});
);
out body geom;
"""


def _to_geojson(data: dict) -> dict:
    feats: list[dict] = []
    for el in data.get("elements", []):
        tags = dict(el.get("tags", {}))
        geom = el.get("geometry")
        if el.get("type") == "node":
            if "lat" not in el or "lon" not in el:
                continue
            geometry: dict[str, Any] = {"type": "Point", "coordinates": [el["lon"], el["lat"]]}
        else:
            if not geom:
                continue
            coords = [[p["lon"], p["lat"]] for p in geom if p and "lon" in p and "lat" in p]
            if len(coords) < 2:
                continue
            fechado = coords[0] == coords[-1] and len(coords) > 3
            if fechado and any(k in tags for k in ("landuse", "natural", "man_made", "amenity")):
                geometry = {"type": "Polygon", "coordinates": [coords]}
            else:
                geometry = {"type": "LineString", "coordinates": coords}
        feats.append({
            "type": "Feature",
            "properties": {**tags, "osm_id": el.get("id"), "osm_type": el.get("type")},
            "geometry": geometry,
        })
    return {"type": "FeatureCollection", "features": feats}


def buscar(lat: float, lon: float, raio_m: int = 3000, timeout: int = TIMEOUT_S) -> dict | None:
    """Consulta a Overpass. Devolve GeoJSON FeatureCollection ou ``None`` se indisponivel."""
    q = QUERY.format(radius=int(raio_m), lat=lat, lon=lon, timeout=timeout - 5)
    ultimo_erro: Exception | None = None
    for ep in ENDPOINTS:
        for tentativa in (1, 2):
            try:
                r = requests.post(
                    ep,
                    data={"data": q},
                    timeout=timeout,
                    headers={"User-Agent": "outorgasys/1.0 (outorga de aguas subterraneas - RS)"},
                )
                r.raise_for_status()
                return _to_geojson(r.json())
            except Exception as exc:  # noqa: BLE001
                ultimo_erro = exc
                time.sleep(1.5 * tentativa)
    return None


def separar_temas(gdf) -> dict[str, Any]:
    """Separa a camada OSM nos temas usados pelo Agente 2."""
    out: dict[str, Any] = {"vias": None, "drenagem": None, "corpos_dagua": None,
                           "nascentes": None, "fontes_poluicao": None}
    if gdf is None or not len(gdf):
        return out

    def tem(col: str) -> bool:
        return col in gdf.columns

    mascara_vias = tem("highway") & gdf["highway"].notna()
    if mascara_vias.any():
        out["vias"] = gdf[mascara_vias].copy()

    mascara_drenagem = tem("waterway") & gdf["waterway"].notna()
    if mascara_drenagem.any():
        out["drenagem"] = gdf[mascara_drenagem].copy()

    if tem("natural"):
        m_agua = gdf["natural"].eq("water")
        if m_agua.any():
            out["corpos_dagua"] = gdf[m_agua].copy()
        m_nasc = gdf["natural"].eq("spring")
        if m_nasc.any():
            out["nascentes"] = gdf[m_nasc].copy()

    topicos = []
    for col in ("amenity", "landuse", "man_made", "industrial"):
        if not tem(col):
            continue
        series = gdf[col]
        m = series.notna()
        if col == "amenity":
            m &= series.isin({"fuel", "wastewater_plant", "recycling"})
        elif col == "landuse":
            m &= series.isin({"landfill", "industrial", "quarry", "brownfield"})
        elif col == "man_made":
            m &= series.eq("storage_tank")
        else:
            m &= series.notna()
        if m.any():
            topicos.append(gdf[m])
    if topicos:
        import geopandas as gpd  # noqa: PLC0415

        out["fontes_poluicao"] = gpd.GeoDataFrame(
            __import__("pandas").concat(topicos, ignore_index=True),
            geometry="geometry", crs=gdf.crs,
        )
    return out
