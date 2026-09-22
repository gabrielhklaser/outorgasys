#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
outorgasys :: construcao da base de dados vetoriais (Agente 2 / Inteligencia Espacial)

Baixa e normaliza todas as camadas vetoriais usadas pela plataforma:

  FONTE GOOGLE DRIVE (fornecida pelo usuario)
    * Geologico Rio Grande do Sul.kmz   -> geologia_rs
    * Hidrogelogia_RS.kmz               -> hidrogeologia_rs
    * Mapa de solos.kmz                 -> solos_rs

  FONTES OFICIAIS ABERTAS
    * IBGE  - malha municipal 2022 (RS)            -> municipios_rs
    * IBGE  - malha estadual 2022 (RS)             -> uf_rs
    * ANA   - BHO 2017 trechos de drenagem         -> drenagem_rs
    * ANA   - BHO 2017 cursos d'agua               -> cursos_dagua_rs
    * ANA   - BHO 2017 areas de contribuicao       -> ottobacias_rs
    * ANA   - Ottobacias nivel 1..4                -> otto_nivel_1..4
    * ANA   - 12 Regioes Hidrograficas CNRH (RHI)  -> regioes_hidrograficas
    * ANA   - Unidades de Planejamento Hidrico     -> uph
    * OSM   - malha viaria + drenagem (Overpass)   -> data/cache/osm/<hash>.geojson

Uso:
    python scripts/fetch_data.py                 # baixa tudo que falta
    python scripts/fetch_data.py --force         # relega tudo
    python scripts/fetch_data.py --only drive,bho
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path
from typing import Iterable

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
VET = ROOT / "data" / "vetoriais"
CACHE = ROOT / "data" / "cache" / "osm"
MANIFEST = VET / "MANIFEST.json"

# --------------------------------------------------------------------------------------
# Areas de interesse
# --------------------------------------------------------------------------------------

# Caixa envolvente do Rio Grande do Sul (WGS84), com margem de ~0.5 grau.
RS_BBOX = (-58.2, -34.3, -49.2, -26.5)  # minx, miny, maxx, maxy

# Ponto de demonstracao (Campo Bom/RS) usado para pre-aquecer o cache OSM.
DEMO_POINTS = [
    ("campo_bom", -29.6842, -51.0531),
    ("novo_hamburgo", -29.6780, -51.1300),
    ("sao_leopoldo", -29.7600, -51.1470),
]

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# --------------------------------------------------------------------------------------
# Fontes - Google Drive (arquivos do usuario)
# --------------------------------------------------------------------------------------

DRIVE_FILES = {
    "geologia_rs.kmz": "1cdaB_TRgHB-HkpwrLgRm-ws0kexr2iWi",
    "hidrogeologia_rs.kmz": "16ioGmmc-ZlyON6ad8MTyquGhSwTy3NhJ",
    "solos_rs.kmz": "1Bro0Af_eRarEVoEn6EpnzxzHPTJVXQMY",
}

DRIVE_URL = "https://drive.usercontent.google.com/download"
DRIVE_URL_ALT = "https://docs.google.com/uc?export=download"

# --------------------------------------------------------------------------------------
# Fontes oficiais abertas
# --------------------------------------------------------------------------------------

IBGE_MUN = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip"
)
IBGE_UF = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2022/Brasil/BR/BR_UF_2022.zip"
)

ANA = "https://metadados.snirh.gov.br"
BHO_BASE = f"{ANA}/files/0c698205-6b59-48dc-8b5e-a58a5dfcc989"
RHI_REC = "fe192ba0-45a9-4215-90a5-3fba6abea174"

HTTP_SOURCES = {
    "bho_trecho_drenagem.gpkg": f"{BHO_BASE}/geoft_bho_2017_trecho_drenagem.gpkg",
    "bho_curso_dagua.gpkg": f"{BHO_BASE}/geoft_bho_2017_curso_dagua.gpkg",
    "bho_area_drenagem.gpkg": f"{BHO_BASE}/geoft_bho_2017_area_drenagem.gpkg",
    "bho_otto_nivel_1.gpkg": f"{BHO_BASE}/geoft_bho_ach_otto_nivel_01.gpkg",
    "bho_otto_nivel_2.gpkg": f"{BHO_BASE}/geoft_bho_ach_otto_nivel_02.gpkg",
    "bho_otto_nivel_3.gpkg": f"{BHO_BASE}/geoft_bho_ach_otto_nivel_03.gpkg",
    "bho_otto_nivel_4.gpkg": f"{BHO_BASE}/geoft_bho_ach_otto_nivel_04.gpkg",
    "snirh_rhi.zip": f"{ANA}/geonetwork/srv/api/records/{RHI_REC}/attachments/SNIRH_RHI.zip",
    "snirh_uph.zip": f"{ANA}/geonetwork/srv/api/records/{RHI_REC}/attachments/SNIRH_UPH.zip",
}

# Espelhos alternativos para o mesmo produto (portais antigo/novo da ANA e INDE).
ANA_MIRROR = "https://metadados.ana.gov.br"
INDE = "https://metadados.inde.gov.br"

HTTP_SOURCE_MIRRORS: dict[str, list[str]] = {
    f"{BHO_BASE}/geoft_bho_2017_trecho_drenagem.gpkg": [
        f"{INDE}/files/b228d007-6d68-46e5-b30d-a1e191b2b21f/geoft_bho_2017_trecho_drenagem.gpkg",
        f"{ANA_MIRROR}/files/0c698205-6b59-48dc-8b5e-a58a5dfcc989/geoft_bho_2017_trecho_drenagem.gpkg",
    ],
    f"{BHO_BASE}/geoft_bho_2017_curso_dagua.gpkg": [
        f"{INDE}/files/b228d007-6d68-46e5-b30d-a1e191b2b21f/geoft_bho_2017_curso_dagua.gpkg",
        f"{ANA_MIRROR}/files/0c698205-6b59-48dc-8b5e-a58a5dfcc989/geoft_bho_2017_curso_dagua.gpkg",
    ],
    f"{BHO_BASE}/geoft_bho_2017_area_drenagem.gpkg": [
        f"{INDE}/files/b228d007-6d68-46e5-b30d-a1e191b2b21f/geoft_bho_2017_area_drenagem.gpkg",
        f"{ANA_MIRROR}/files/0c698205-6b59-48dc-8b5e-a58a5dfcc989/geoft_bho_2017_area_drenagem.gpkg",
    ],
}

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# --------------------------------------------------------------------------------------
# Utilitarios
# --------------------------------------------------------------------------------------


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def ensure_dirs() -> None:
    for p in (RAW, VET, CACHE):
        p.mkdir(parents=True, exist_ok=True)


def _curl_download(url: str, dest: Path, timeout: int = 900) -> bool:
    """Fallback via curl -resolve conservador.

    Servidores institucionais (ANA/SNIRH) as vezes rejeitam o padrao de TLS ou os
    cabecalhos do ``requests``; o curl do runner costuma negociar melhor.
    """
    import shutil
    import subprocess

    if not shutil.which("curl"):
        return False
    tmp = dest.with_suffix(dest.suffix + ".part")
    cmd = [
        "curl", "-fL", "--retry", "3", "--retry-delay", "5",
        "--connect-timeout", "45", "--max-time", str(timeout),
        "-A", UA,
        "-H", "Accept: */*",
        "-H", "Accept-Language: pt-BR,pt;q=0.9,en;q=0.8",
        "-o", str(tmp), url,
    ]
    log("  tentando via curl ...")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    except Exception as exc:  # noqa: BLE001
        log(f"  curl falhou: {exc}")
        return False
    if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 1024:
        tmp.replace(dest)
        log(f"  OK via curl: {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
        return True
    log(f"  curl rc={r.returncode}: {(r.stderr or '').strip()[:300]}")
    tmp.unlink(missing_ok=True)
    return False


def http_download(url: str, dest: Path, tries: int = 3, **params) -> bool:
    """Download com retomada simples e barra de progresso textual.

    Tenta ``requests``; em caso de falha, cai para ``curl`` e, por fim, para os
    espelhos alternativos declarados em ``HTTP_SOURCE_MIRRORS``.
    """
    if dest.exists() and dest.stat().st_size > 1024:
        log(f"  ja existe: {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
        return True

    candidatos = [url, *HTTP_SOURCE_MIRRORS.get(url, [])]

    for idx, target in enumerate(candidatos):
        sufixo = "" if idx == 0 else f" (espelho {idx})"
        for attempt in range(1, tries + 1):
            tmp = dest.with_suffix(dest.suffix + ".part")
            try:
                log(f"  GET{sufixo} {target[:110]}"
                    f"{'...' if len(target) > 110 else ''} (tentativa {attempt})")
                with requests.get(
                    target,
                    stream=True,
                    timeout=(45, 900),
                    headers={
                        "User-Agent": UA,
                        "Accept": "*/*",
                        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                    },
                    params=params,
                    allow_redirects=True,
                ) as r:
                    r.raise_for_status()
                    ctype = r.headers.get("Content-Type", "")
                    if "text/html" in ctype and not target.endswith(".html"):
                        corpo = r.text[:300]
                        log(f"  resposta HTML inesperada: {corpo!r}")
                        raise RuntimeError("resposta HTML em vez do arquivo")
                    total = int(r.headers.get("Content-Length", 0))
                    got = 0
                    with open(tmp, "wb") as fh:
                        for chunk in r.iter_content(chunk_size=1 << 20):
                            if not chunk:
                                continue
                            fh.write(chunk)
                            got += len(chunk)
                            if total:
                                print(
                                    f"\r    {got/1e6:8.1f} / {total/1e6:8.1f} MB",
                                    end="",
                                    flush=True,
                                )
                    print(flush=True)
                if tmp.stat().st_size <= 1024:
                    raise RuntimeError("arquivo vazio")
                tmp.replace(dest)
                log(f"  OK {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
                return True
            except Exception as exc:  # noqa: BLE001
                log(f"  FALHOU: {type(exc).__name__}: {str(exc)[:220]}")
                tmp.unlink(missing_ok=True)
                time.sleep(3 * attempt)
        if _curl_download(target, dest):
            return True

    log(f"  !! todos os candidatos falharam para {Path(url).name}")
    return False


def drive_download(file_id: str, dest: Path) -> bool:
    """Download de arquivo grande do Google Drive, contornando a pagina de confirmacao."""
    if dest.exists() and dest.stat().st_size > 1024:
        log(f"  ja existe: {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
        return True

    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    for base in (DRIVE_URL, DRIVE_URL_ALT):
        try:
            r = s.get(base, params={"id": file_id, "export": "download", "confirm": "t"},
                      stream=True, timeout=(30, 300))
            r.raise_for_status()

            # Detecta a pagina HTML de confirmacao e extrai o token real.
            ctype = r.headers.get("Content-Type", "")
            if "text/html" in ctype:
                html = r.text
                token = None
                for marker in ('confirm=t&uuid=', 'confirm='):
                    idx = html.find(marker)
                    if idx != -1:
                        frag = html[idx: idx + 120]
                        tok = frag.split("&")[0].split('"')[0]
                        tok = tok.replace("confirm=", "")
                        if tok:
                            token = tok
                            break
                log(f"  pagina de confirmacao do Drive, token={'sim' if token else 'nao'}")
                if not token:
                    continue
                r = s.get(base, params={"id": file_id, "export": "download", "confirm": token},
                          stream=True, timeout=(30, 300))
                r.raise_for_status()
                if "text/html" in r.headers.get("Content-Type", ""):
                    continue

            tmp = dest.with_suffix(dest.suffix + ".part")
            total = int(r.headers.get("Content-Length", 0))
            got = 0
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    got += len(chunk)
                    if total:
                        print(f"\r    {got/1e6:8.1f} / {total/1e6:8.1f} MB", end="", flush=True)
            print(flush=True)
            tmp.replace(dest)
            log(f"  OK {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
            return True
        except Exception as exc:  # noqa: BLE001
            log(f"  FALHOU via {base}: {type(exc).__name__}: {exc}")
    return False


def unzip(archive: Path, dest_dir: Path) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(dest_dir)
    return [dest_dir / n for n in zipfile.ZipFile(archive).namelist()]


def find_first(root: Path, patterns: Iterable[str]) -> Path | None:
    pats = [p.lower() for p in patterns]
    for p in sorted(root.rglob("*")):
        if p.is_file() and any(p.name.lower() == q or p.name.lower().endswith(q) for q in pats):
            return p
    return None


# --------------------------------------------------------------------------------------
# Conversoes
# --------------------------------------------------------------------------------------


def import_geospatial() -> tuple:
    """Importa geopandas de forma tolerante (nem todo ambiente tem o stack completo)."""
    import geopandas as gpd  # noqa: PLC0415
    from pyogrio import list_layers  # noqa: PLC0415

    return gpd, list_layers


def listar_camadas_vetoriais(path: Path) -> list[dict]:
    """Enumera todas as camadas (folders, no caso de KML) de uma fonte vetorial."""
    from pyogrio import list_layers  # noqa: PLC0415

    saida = []
    for nome, tipo in list_layers(path):
        saida.append({"camada": nome, "tipo_geometrico": tipo})
    return saida


def read_any(path: Path, bbox=None, layer=None, **kw):
    """Le qualquer fonte vetorial suportada pelo GDAL, com fallback de driver."""
    import geopandas as gpd  # noqa: PLC0415

    attempts: list[dict] = []
    if layer is not None:
        attempts.append({"layer": layer, **kw})
    attempts.append({**kw})
    if path.suffix.lower() == ".kml":
        # Tenta LIBKML (melhor) e depois KML classico.
        attempts = [
            {**a, "driver": d}
            for d in ("LIBKML", "KML")
            for a in ({"layer": layer, **kw} if layer else {**kw},)
        ]
    last = None
    for kwargs in attempts:
        try:
            gdf = gpd.read_file(path, bbox=bbox, **kwargs)
            if len(gdf):
                return gdf
        except Exception as exc:  # noqa: BLE001
            last = exc
    if last:
        raise last
    return gpd.GeoDataFrame()


def read_all_layers(path: Path, drivers=("LIBKML", "KML")) -> tuple[object, list[dict]]:
    """Le TODAS as camadas de um KML/GPKG e devolve a uniao das feicoes.

    KMLs de mapas tematicos normalmente organizam as unidades dentro de <Folder>.
    O GDAL expoe cada Folder como uma camada: ler apenas a primeira costuma
    devolver somente um placemark de legenda. Aqui varremos todas as camadas,
    guardamos o inventario para auditoria e concatenamos as que tem geometria
    utilisavel (poligonos primeiro, depois linhas e pontos como ultimo recurso).
    """
    import geopandas as gpd  # noqa: PLC0415
    import pandas as pd  # noqa: PLC0415

    inventario: list[dict] = []
    coletados: dict[str, list] = {"poligono": [], "linha": [], "ponto": []}

    try:
        bruto = listar_camadas_vetoriais(path)
    except Exception as exc:  # noqa: BLE001
        log(f"  nao foi possivel listar camadas: {exc}")
        bruto = [{"camada": None, "tipo_geometrico": None}]

    nomes = [c["camada"] for c in bruto] or [None]
    drivers = drivers if path.suffix.lower() == ".kml" else (None,)

    for nome in nomes:
        for drv in drivers:
            kwargs = {"layer": nome} if nome is not None else {}
            if drv:
                kwargs["driver"] = drv
            try:
                g = gpd.read_file(path, **kwargs)
            except Exception as exc:  # noqa: BLE001
                inventario.append({"camada": nome, "driver": drv,
                                   "erro": f"{type(exc).__name__}: {exc}"})
                continue
            if not len(g):
                inventario.append({"camada": nome, "driver": drv, "feicoes": 0})
                continue
            tipos = set(g.geom_type.dropna().astype(str))
            if tipos & {"Polygon", "MultiPolygon"}:
                classe = "poligono"
            elif tipos & {"LineString", "MultiLineString"}:
                classe = "linha"
            else:
                classe = "ponto"
            coletados[classe].append(g)
            inventario.append({
                "camada": nome, "driver": drv, "feicoes": int(len(g)),
                "tipos": sorted(tipos), "colunas": [c for c in g.columns if c != "geometry"][:20],
            })
            break  # driver funcionou para esta camada

    for classe in ("poligono", "linha", "ponto"):
        if coletados[classe]:
            gdf = gpd.GeoDataFrame(
                pd.concat(coletados[classe], ignore_index=True),
                geometry="geometry",
                crs=coletados[classe][0].crs,
            )
            return gdf, inventario

    return gpd.GeoDataFrame(), inventario


def kmz_to_gpkg(kmz: Path, out: Path, simplify_m: float | None = None) -> dict:
    """Converte KMZ/KML em GeoPackage EPSG:4674, unificando todas as camadas.

    Usa o driver GDAL quando disponivel e cai para um parser KML proprio quando nao.
    """
    import geopandas as gpd  # noqa: PLC0415

    work = RAW / ("kmz_" + kmz.stem)
    kml_path: Path | None = None
    if kmz.suffix.lower() == ".kmz":
        files = unzip(kmz, work)
        kml_path = find_first(work, ("doc.kml", ".kml"))
        if kml_path is None:
            raise RuntimeError(f"KMZ sem doc.kml: {kmz}")
    else:
        kml_path = kmz

    gdf, inventario = read_all_layers(kml_path)
    log(f"  camadas KML encontradas: {len(inventario)}")
    for item in inventario[:15]:
        log(f"    - {item.get('camada')!r} drv={item.get('driver')} "
            f"n={item.get('feicoes', item.get('erro', '?'))}")
    if not len(gdf):
        raise RuntimeError(f"nenhuma feicao utilizavel em {kmz.name}")

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    gdf = gdf.to_crs("EPSG:4674")

    # Remove colunas puramente de estilo do KML e normaliza nomes.
    drop = [c for c in gdf.columns if c.lower() in
            {"styleurl", "snippet", "icon", "tessellate", "altitudemode", "extrude",
             "visibility", "description", "begin", "end", "gx_media_links"}]
    gdf = gdf.drop(columns=[c for c in drop if c in gdf.columns])

    if simplify_m:
        gm = gdf.to_crs("EPSG:31982").geometry.simplify(simplify_m, preserve_topology=True)
        gdf = gdf.set_geometry(gm.to_crs("EPSG:4674"))

    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    gdf = gdf.reset_index(drop=True)
    gdf.to_file(out, driver="GPKG", index=False)

    return {
        "arquivo": str(out.relative_to(ROOT)),
        "feicoes": int(len(gdf)),
        "colunas": [c for c in gdf.columns if c != "geometry"][:25],
        "crs": "EPSG:4674",
        "camadas_kml": inventario[:40],
    }


def filter_to_rs(src: Path, out: Path, layer: str | None = None) -> dict:
    """Recorta uma fonte nacional para a caixa envolvente do RS."""
    gdf = read_any(src, bbox=RS_BBOX, layer=layer)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674")
    gdf = gdf.to_crs("EPSG:4674")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].reset_index(drop=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(out, driver="GPKG", index=False)
    return {
        "arquivo": str(out.relative_to(ROOT)),
        "feicoes": int(len(gdf)),
        "colunas": [c for c in gdf.columns if c != "geometry"][:25],
        "crs": "EPSG:4674",
    }


def ibge_municipios(mun_zip: Path, out: Path) -> dict:
    d = RAW / "ibge_mun"
    unzip(mun_zip, d)
    shp = find_first(d, (".shp",))
    if shp is None:
        shp = find_first(d, (".gpkg",))
    if shp is None:
        raise RuntimeError("shapefile do IBGE nao encontrado")
    import geopandas as gpd  # noqa: PLC0415

    gdf = gpd.read_file(shp, bbox=RS_BBOX)
    gdf = gdf.to_crs("EPSG:4674")
    # RS = codigo de UF 43
    uf_cols = [c for c in gdf.columns if c.upper() in ("CD_UF", "CDUF", "UF", "SIGLA_UF",
                                                       "SIGLA", "NM_UF")]
    if uf_cols:
        c = uf_cols[0]
        vals = gdf[c].astype(str)
        gdf = gdf[vals.str.startswith("43") | vals.str.upper().eq("RS")]
    gdf = gdf.reset_index(drop=True)
    gdf.to_file(out, driver="GPKG", index=False)
    return {
        "arquivo": str(out.relative_to(ROOT)),
        "feicoes": int(len(gdf)),
        "colunas": [c for c in gdf.columns if c != "geometry"][:25],
        "crs": "EPSG:4674",
    }


def ibge_uf(uf_zip: Path, out: Path) -> dict:
    d = RAW / "ibge_uf"
    unzip(uf_zip, d)
    shp = find_first(d, (".shp",)) or find_first(d, (".gpkg",))
    import geopandas as gpd  # noqa: PLC0415

    gdf = gpd.read_file(shp, bbox=RS_BBOX)
    gdf = gdf.to_crs("EPSG:4674")
    gdf = gdf[gdf.geometry.notna()].reset_index(drop=True)
    gdf.to_file(out, driver="GPKG", index=False)
    return {
        "arquivo": str(out.relative_to(ROOT)),
        "feicoes": int(len(gdf)),
        "colunas": [c for c in gdf.columns if c != "geometry"][:25],
        "crs": "EPSG:4674",
    }


def overpass_fetch(lat: float, lon: float, radius_m: int = 3000) -> dict | None:
    """Busca malha viaria, drenagem e possiveis fontes de poluicao no OSM/Overpass."""
    q = f"""
    [out:json][timeout:120];
    (
      way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service)$"](around:{radius_m},{lat},{lon});
      way["waterway"~"^(river|stream|canal|drain|creek)$"](around:{radius_m},{lat},{lon});
      way["natural"="water"](around:{radius_m},{lat},{lon});
      node["natural"="spring"](around:{radius_m},{lat},{lon});
      node["amenity"~"^(fuel|wastewater_plant|landfill|recycling)$"](around:{radius_m},{lat},{lon});
      way["landuse"~"^(landfill|industrial|quarry|landfill)$"](around:{radius_m},{lat},{lon});
      way["man_made"="storage_tank"](around:{radius_m},{lat},{lon});
    );
    out body geom;
    """
    data = None
    for ep in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(ep, data={"data": q}, timeout=180,
                              headers={"User-Agent": "outorgasys/1.0 (outorga aguas subterraneas RS)"})
            r.raise_for_status()
            data = r.json()
            break
        except Exception as exc:  # noqa: BLE001
            log(f"  Overpass {ep} falhou: {type(exc).__name__}: {exc}")
    if data is None:
        return None
    return data


def overpass_to_geojson(data: dict) -> dict:
    """Converte a resposta do Overpass em um GeoJSON FeatureCollection."""
    feats = []
    for el in data.get("elements", []):
        geom = el.get("geometry")
        if el.get("type") == "node":
            geom = [{"lat": el["lat"], "lon": el["lon"]}]
        if not geom:
            continue
        tags = dict(el.get("tags", {}))
        if el.get("type") == "node":
            coords = [[geom[0]["lon"], geom[0]["lat"]]]
            geometry = {"type": "Point", "coordinates": coords[0]}
        else:
            coords = [[p["lon"], p["lat"]] for p in geom if p]
            if len(coords) < 2:
                continue
            closed = coords[0] == coords[-1] and len(coords) > 3
            if closed and ("landuse" in tags or "natural" in tags or "man_made" in tags):
                geometry = {"type": "Polygon", "coordinates": [coords]}
            else:
                geometry = {"type": "LineString", "coordinates": coords}
        feats.append({
            "type": "Feature",
            "properties": {**tags, "osm_id": el.get("id"), "osm_type": el.get("type")},
            "geometry": geometry,
        })
    return {"type": "FeatureCollection", "features": feats}


def warm_osm_cache() -> dict:
    log("[OSM] pre-aquecendo cache Overpass para os pontos de demonstracao")
    out = {}
    for name, lat, lon in DEMO_POINTS:
        key = hashlib.sha1(f"{lat:.4f},{lon:.4f}".encode()).hexdigest()[:12]
        dest = CACHE / f"osm_{name}_{key}.geojson"
        if dest.exists():
            log(f"  cache ja existe: {dest.name}")
            out[name] = str(dest.relative_to(ROOT))
            continue
        data = overpass_fetch(lat, lon, 3000)
        if data is None:
            log(f"  sem dados OSM para {name}")
            continue
        fc = overpass_to_geojson(data)
        dest.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        log(f"  {dest.name}: {len(fc['features'])} feicoes")
        out[name] = str(dest.relative_to(ROOT))
        time.sleep(2)
    return out


# --------------------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------------------


def step(name: str, fn, manifest: dict) -> None:
    log(f"=== {name} ===")
    try:
        info = fn()
        manifest["camadas"][name] = {"status": "ok", **info}
        log(f"  -> ok ({info.get('feicoes', '?')} feicoes)")
    except Exception as exc:  # noqa: BLE001
        manifest["camadas"][name] = {
            "status": "falhou",
            "erro": f"{type(exc).__name__}: {exc}",
        }
        log(f"  -> FALHOU: {type(exc).__name__}: {exc}")


def ler_pedido_build() -> dict:
    """Le ``data/.build-request.json`` (gatilho por commit, usado no Actions)."""
    p = ROOT / "data" / ".build-request.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--skip-osm", action="store_true")
    args = ap.parse_args()

    pedido = ler_pedido_build()
    if pedido:
        args.force = args.force or bool(pedido.get("force"))
        args.only = args.only or str(pedido.get("only") or "")
        args.skip_osm = args.skip_osm or bool(pedido.get("skip_osm"))
        log(f"pedido de build: force={args.force} only={args.only!r}")

    ensure_dirs()
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    manifest: dict = {"gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"), "camadas": {}}
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            manifest["camadas"] = manifest.get("camadas", {})
        except Exception:  # noqa: BLE001
            pass
    manifest["gerado_em"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    def wanted(key: str) -> bool:
        return (not only or key in only) and (
            args.force or manifest["camadas"].get(key, {}).get("status") != "ok"
        )

    # KMZ -> GPKG
    kmz_targets = {
        "geologia_rs": ("geologia_rs.kmz", 60.0),
        "hidrogeologia_rs": ("hidrogeologia_rs.kmz", 60.0),
        "solos_rs": ("solos_rs.kmz", 120.0),
    }

    # ---------------- Google Drive ----------------
    # Sempre garantimos os KMZ de origem: cada execucao do Actions comeca com
    # data/raw vazio (a pasta nao e versionada), entao basta que UMA camada
    # derivada precise ser reconstruida para exigir o download novamente.
    precisa_drive = wanted("drive") or any(
        wanted(k) or not (VET / f"{k}.gpkg").exists() for k in kmz_targets
    )
    if precisa_drive:
        log("=== Google Drive (fontes do usuario) ===")
        for fname, fid in DRIVE_FILES.items():
            dest = RAW / fname
            if not drive_download(fid, dest):
                log(f"  !! nao foi possivel baixar {fname}")

    for key, (fname, simp) in kmz_targets.items():
        if not wanted(key):
            continue
        src = RAW / fname
        if not src.exists():
            manifest["camadas"][key] = {"status": "falhou", "erro": "KMZ de origem ausente"}
            continue
        step(key, lambda s=src, k=key, t=simp: kmz_to_gpkg(s, VET / f"{k}.gpkg", t), manifest)

    # ---------------- IBGE ----------------
    if wanted("municipios_rs"):
        z = RAW / "BR_Municipios_2022.zip"
        if http_download(IBGE_MUN, z):
            step("municipios_rs", lambda: ibge_municipios(z, VET / "municipios_rs.gpkg"), manifest)

    if wanted("uf_rs"):
        z = RAW / "BR_UF_2022.zip"
        if http_download(IBGE_UF, z):
            step("uf_rs", lambda: ibge_uf(z, VET / "uf_rs.gpkg"), manifest)

    # ---------------- ANA / BHO ----------------
    bho_targets = {
        "drenagem_rs": ("bho_trecho_drenagem.gpkg", None),
        "cursos_dagua_rs": ("bho_curso_dagua.gpkg", None),
        "ottobacias_rs": ("bho_area_drenagem.gpkg", None),
        "otto_nivel_1": ("bho_otto_nivel_1.gpkg", None),
        "otto_nivel_2": ("bho_otto_nivel_2.gpkg", None),
        "otto_nivel_3": ("bho_otto_nivel_3.gpkg", None),
        "otto_nivel_4": ("bho_otto_nivel_4.gpkg", None),
    }
    for key, (fname, _layer) in bho_targets.items():
        if not wanted(key):
            continue
        src = RAW / fname
        if not src.exists() and not http_download(HTTP_SOURCES[fname], src):
            manifest["camadas"][key] = {"status": "falhou", "erro": "download ANA falhou"}
            continue
        step(key, lambda s=src, k=key: filter_to_rs(s, VET / f"{k}.gpkg"), manifest)

    for key, fname in (("regioes_hidrograficas", "snirh_rhi.zip"),
                       ("uph", "snirh_uph.zip")):
        if not wanted(key):
            continue
        z = RAW / fname
        if not z.exists() and not http_download(HTTP_SOURCES[fname], z):
            manifest["camadas"][key] = {"status": "falhou", "erro": "download ANA falhou"}
            continue
        d = RAW / ("ana_" + key)
        shp = None
        try:
            unzip(z, d)
            shp = find_first(d, (".shp",)) or find_first(d, (".gpkg",))
        except Exception as exc:  # noqa: BLE001
            log(f"  erro ao descompactar {fname}: {exc}")
        if shp is None:
            manifest["camadas"][key] = {"status": "falhou", "erro": "shapefile nao encontrado"}
            continue
        step(key, lambda s=shp, k=key: filter_to_rs(s, VET / f"{k}.gpkg"), manifest)

    # ---------------- OSM ----------------
    if not args.skip_osm and (not only or "osm" in only):
        try:
            info = warm_osm_cache()
            manifest["camadas"]["osm_cache"] = {"status": "ok", "arquivos": info}
        except Exception as exc:  # noqa: BLE001
            manifest["camadas"]["osm_cache"] = {
                "status": "falhou",
                "erro": f"{type(exc).__name__}: {exc}",
            }

    # ---------------- Manifesto ----------------
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    log("\n===== RESUMO =====")
    for k, v in sorted(manifest["camadas"].items()):
        st = v.get("status")
        extra = v.get("feicoes", "")
        print(f"  {k:28s} {st:8s} {extra}")
    ok = sum(1 for v in manifest["camadas"].values() if v.get("status") == "ok")
    print(f"\n{ok}/{len(manifest['camadas'])} camadas ok -> {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
