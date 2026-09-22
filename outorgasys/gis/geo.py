# -*- coding: utf-8 -*-
"""Utilidades geodesicas: SIRGAS 2000 (EPSG:4674) <-> UTM (EPSG:3198x)."""

from __future__ import annotations

from typing import Any

from .. import config as C
from ..rules import fuso_utm_rs


def _importar_pyproj():
    import pyproj  # noqa: PLC0415

    return pyproj


def epsg_utm_para_lon(lon: float) -> str:
    """Codigo EPSG do fuso UTM-SIRGAS 2000 que cobre a longitude informada."""
    return fuso_utm_rs(lon)[1]


def geograficas_para_utm(lat: float, lon: float, epsg: str | None = None) -> dict:
    """Converte graus decimais (SIRGAS 2000) para UTM metrico.

    Retorna E, N, fuso, hemisferio e o EPSG utilizado.
    """
    pyproj = _importar_pyproj()
    fuso, epsg_auto = fuso_utm_rs(lon)
    epsg = epsg or epsg_auto
    tf = pyproj.Transformer.from_crs(C.CRS_GEOGRAFICO, epsg, always_xy=True)
    e, n = tf.transform(float(lon), float(lat))
    return {
        "lat": float(lat),
        "lon": float(lon),
        "utm_e": round(float(e), 3),
        "utm_n": round(float(n), 3),
        "fuso": fuso,
        "hemisferio": "S",
        "epsg": epsg,
        "crs_geografico": C.CRS_GEOGRAFICO,
    }


def utm_para_geograficas(e: float, n: float, epsg: str = C.CRS_UTM_22S) -> dict:
    pyproj = _importar_pyproj()
    tf = pyproj.Transformer.from_crs(epsg, C.CRS_GEOGRAFICO, always_xy=True)
    lon, lat = tf.transform(float(e), float(n))
    return {"lat": round(float(lat), 7), "lon": round(float(lon), 7), "epsg": epsg}


def formatar_utm(e: float, n: float) -> str:
    return f"E {e:,.1f} m / N {n:,.1f} m".replace(",", ".")


def formatar_graus(lat: float, lon: float) -> str:
    return f"{abs(lat):.5f}°{'S' if lat < 0 else 'N'}, {abs(lon):.5f}°{'W' if lon < 0 else 'E'}"


def bbox_ao_redor(lat: float, lon: float, raio_m: float,
                  epsg: str | None = None) -> tuple[float, float, float, float]:
    """Caixa envolvente em graus decimais que contem um raio metrico."""
    u = geograficas_para_utm(lat, lon, epsg)
    minx, miny = u["utm_e"] - raio_m, u["utm_n"] - raio_m
    maxx, maxy = u["utm_e"] + raio_m, u["utm_n"] + raio_m
    a = utm_para_geograficas(minx, miny, u["epsg"])
    b = utm_para_geograficas(maxx, maxy, u["epsg"])
    return (a["lon"], a["lat"], b["lon"], b["lat"])


def bbox_expandido(bbox: tuple[float, float, float, float],
                   fator: float = 1.35) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = bbox
    dx, dy = (maxx - minx) * (fator - 1) / 2, (maxy - miny) * (fator - 1) / 2
    return (minx - dx, miny - dy, maxx + dx, maxy + dy)


def area_m2(geom_wkt: str) -> float | None:
    try:
        from shapely import wkt  # noqa: PLC0415

        return float(wkt.loads(geom_wkt).area)
    except Exception:  # noqa: BLE001
        return None


def dentro_do_rs(lat: float, lon: float) -> bool | None:
    """Teste rapido contra a caixa envolvente do estado."""
    minx, miny, maxx, maxy = C.RS_BBOX
    return bool(minx <= lon <= maxx and miny <= lat <= maxy)


def resumo_geodesico(coord: dict[str, Any]) -> str:
    if not coord:
        return "-"
    return (
        f"{formatar_graus(coord['lat'], coord['lon'])} · "
        f"UTM {coord.get('fuso', '22S')} "
        f"{formatar_utm(coord.get('utm_e', 0), coord.get('utm_n', 0))}"
    )
