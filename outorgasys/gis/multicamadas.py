# -*- coding: utf-8 -*-
"""
Modulo de Integracao de Mapas Multicamadas (Skill gis-multicamadas).

Gera o mapa interativo HTML standalone com controle de camadas (LayerControl),
alternancia de imagens de satelite e bases analiticas, buffer de raio de seguranca,
geologia, hidrogeologia, solos, drenagem e medicao metrica.
"""

from __future__ import annotations

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
        script_path = C.ROOT / "skills" / "gis_multicamadas" / "scripts" / "multicamadas_map.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Script multicamadas_map.py nao encontrado em {script_path}")

    parent_dir = str(script_path.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    spec = importlib.util.spec_from_file_location("multicamadas_map", str(script_path))
    mm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mm)

    mapa = mm.criar_mapa_multicamadas(
        lat=lat,
        lon=lon,
        zoom_inicial=15,
        raio_seguranca_m=raio_seguranca_m,
        camadas_vetoriais=camadas,
        dados_poco=dados_poco,
        titulo=titulo,
    )

    dest = Path(destino_html)
    return mm.salvar_mapa_html(mapa, dest)
