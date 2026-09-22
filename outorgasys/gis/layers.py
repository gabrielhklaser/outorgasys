# -*- coding: utf-8 -*-
"""
Registro e carga das camadas vetoriais (skill geopandas + fallback controlado).

Cada camada e descrita por uma :class:`Camada`. O carregamento devolve sempre um
:class:`CamadaResult`, nunca lanca excecao para camada ausente: o Agente 2
registra a origem e o status de cada camada e o relatorio final declara
explicitamente quais bases foram usadas e quais nao estavam disponiveis.
"""

from __future__ import annotations

import functools
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .. import config as C


# --------------------------------------------------------------------------------------
# Modelo de camada
# --------------------------------------------------------------------------------------


@dataclass
class Camada:
    chave: str
    rotulo: str
    arquivo: str
    geoms: str                 # ponto | linha | poligono | misto
    fonte: str
    url_fonte: str = ""
    papel: str = ""
    obrigatoria: bool = False
    campos_rotulo: tuple[str, ...] = ()


@dataclass
class CamadaResult:
    chave: str
    gdf: Any | None = None
    status: str = "ausente"    # ok | vazia | ausente | erro
    origem: str = ""
    arquivo: str = ""
    mensagem: str = ""
    feicoes: int = 0

    @property
    def disponivel(self) -> bool:
        return self.status == "ok" and self.gdf is not None and len(self.gdf)

    def to_dict(self) -> dict:
        return {
            "chave": self.chave,
            "status": self.status,
            "origem": self.origem,
            "arquivo": self.arquivo,
            "feicoes": self.feicoes,
            "mensagem": self.mensagem,
        }


# --------------------------------------------------------------------------------------
# Registro
# --------------------------------------------------------------------------------------

CAMADAS: dict[str, Camada] = {
    c.chave: c for c in [
        Camada("uf_rs", "Limite estadual do RS", "uf_rs.gpkg", "poligono",
               "IBGE - Malha de Unidades da Federacao 2022",
               "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/",
               "Validacao do ponto dentro do estado",
               campos_rotulo=("NM_UF", "SIGLA_UF", "nome", "sigla", "UF")),

        Camada("municipios_rs", "Malha municipal do RS", "municipios_rs.gpkg", "poligono",
               "IBGE - Malha Municipal 2022",
               "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/",
               "Identificacao do municipio e validacao de consistencia",
               obrigatoria=True,
               campos_rotulo=("NM_MUN", "nome", "municipio", "NOME", "NM_MUNICIP")),

        Camada("geologia_rs", "Geologia do RS", "geologia_rs.gpkg", "poligono",
               "Google Drive do projeto - 'Geologico Rio Grande do Sul.kmz'",
               "https://drive.google.com/drive/folders/1Id6ynvlyUKTWyw_UJ3zE5vs_qlh2t_ai",
               "Formacao geologica e litologia predominante",
               obrigatoria=True,
               campos_rotulo=("Name", "name", "NOME", "LITOLOGIA", "litologia",
                              "FORMACAO", "formacao", "DESCRICAO", "descricao")),

        Camada("hidrogeologia_rs", "Hidrogeologia do RS", "hidrogeologia_rs.gpkg", "poligono",
               "Google Drive do projeto - 'Hidrogelogia_RS.kmz'",
               "https://drive.google.com/drive/folders/1Id6ynvlyUKTWyw_UJ3zE5vs_qlh2t_ai",
               "Sistema aquifer e dominio hidrogeologico",
               obrigatoria=True,
               campos_rotulo=("Name", "name", "NOME", "SISTEMA", "sistema",
                              "AQUIFERO", "aquifero", "DESCRICAO", "descricao")),

        Camada("solos_rs", "Solos do RS", "solos_rs.gpkg", "poligono",
               "Google Drive do projeto - 'Mapa de solos.kmz'",
               "https://drive.google.com/drive/folders/1Id6ynvlyUKTWyw_UJ3zE5vs_qlh2t_ai",
               "Classe de solo (contexto de vulnerabilidade a contaminacao)",
               campos_rotulo=("Name", "name", "NOME", "SOLO", "solo",
                              "CLASSE", "classe", "DESCRICAO", "descricao")),

        Camada("drenagem_rs", "Rede de drenagem (BHO 2017)", "drenagem_rs.gpkg", "linha",
               "ANA - Base Hidrografica Ottocodificada 2017 (trechos de drenagem)",
               "https://metadados.snirh.gov.br/geonetwork/srv/api/records/0c698205-6b59-48dc-8b5e-a58a5dfcc989",
               "Distancia euclidiana ao corpo hidrico mais proximo",
               obrigatoria=True,
               campos_rotulo=("no_rio_pri", "no_rio", "nu_bacia", "nome", "Name", "NOME")),

        Camada("cursos_dagua_rs", "Cursos d'agua (BHO 2017)", "cursos_dagua_rs.gpkg", "linha",
               "ANA - Base Hidrografica Ottocodificada 2017 (cursos d'agua)",
               "https://metadados.snirh.gov.br/geonetwork/srv/api/records/0c698205-6b59-48dc-8b5e-a58a5dfcc989",
               "Rotulagem do corpo hidrico de referencia",
               campos_rotulo=("no_rio_pri", "no_rio", "nome", "Name", "NOME")),

        Camada("ottobacias_rs", "Ottobacias - areas de contribuicao", "ottobacias_rs.gpkg",
               "poligono",
               "ANA - BHO 2017 (areas de contribuicao hidrografica)",
               "https://metadados.snirh.gov.br/geonetwork/srv/api/records/0c698205-6b59-48dc-8b5e-a58a5dfcc989",
               "Bacia hidrografica de detalhe (ottobacia)",
               campos_rotulo=("nu_bac_ott", "cobacia", "nu_bacia", "nome", "Name")),

        Camada("otto_nivel_1", "Ottobacias nivel 1", "otto_nivel_1.gpkg", "poligono",
               "ANA - BHO 2017 Otto nivel 1", "", "Agregacao de bacia nivel 1",
               campos_rotulo=("nu_bac_ott", "cobacia", "nome", "Name")),
        Camada("otto_nivel_2", "Ottobacias nivel 2", "otto_nivel_2.gpkg", "poligono",
               "ANA - BHO 2017 Otto nivel 2", "", "Agregacao de bacia nivel 2",
               campos_rotulo=("nu_bac_ott", "cobacia", "nome", "Name")),
        Camada("otto_nivel_3", "Ottobacias nivel 3", "otto_nivel_3.gpkg", "poligono",
               "ANA - BHO 2017 Otto nivel 3", "", "Agregacao de bacia nivel 3",
               campos_rotulo=("nu_bac_ott", "cobacia", "nome", "Name")),

        Camada("regioes_hidrograficas", "Regioes Hidrograficas (CNRH)", "regioes_hidrograficas.gpkg",
               "poligono",
               "ANA/SNIRH - 12 Regioes Hidrograficas definidas pelo CNRH",
               "https://metadados.snirh.gov.br/geonetwork/srv/api/records/fe192ba0-45a9-4215-90a5-3fba6abea174",
               "Regiao hidrografica (ex.: Regiao Hidrografica do Guaiba)",
               obrigatoria=True,
               campos_rotulo=("NO_RHI", "NOME", "nome", "Name", "SG_RHI")),

        Camada("uph", "Unidades de Planejamento Hidrico (UPH)", "uph.gpkg", "poligono",
               "ANA/SNIRH - Unidades de Planejamento Hidrico",
               "https://metadados.snirh.gov.br/geonetwork/srv/api/records/fe192ba0-45a9-4215-90a5-3fba6abea174",
               "Unidade de planejamento hidrico",
               campos_rotulo=("NO_UPH", "NOME", "nome", "Name", "SG_UPH")),
    ]
}


def caminho_camada(chave: str) -> Path:
    return C.VETORIAIS / CAMADAS[chave].arquivo


# --------------------------------------------------------------------------------------
# Cache de leitura (evita reler GPKG estaduais a cada rerun do Streamlit)
# --------------------------------------------------------------------------------------

_CACHE: dict[str, tuple[float, CamadaResult]] = {}
CACHE_TTL_S = 300.0


def _cache_key(chave: str, bbox: tuple | None, extra: str) -> str:
    return hashlib.sha1(
        f"{chave}|{bbox}|{extra}|{C.CRS_GEOGRAFICO}".encode()
    ).hexdigest()


def limpar_cache() -> None:
    _CACHE.clear()


# --------------------------------------------------------------------------------------
# Leitura
# --------------------------------------------------------------------------------------


def carregar(chave: str, bbox: tuple[float, float, float, float] | None = None,
             usar_cache: bool = True) -> CamadaResult:
    """Le uma camada vetorial do GeoPackage, opcionalmente recortada por bbox.

    Nunca lanca para camada ausente: devolve ``status='ausente'``.
    """
    cam = CAMADAS.get(chave)
    if cam is None:
        return CamadaResult(chave, status="erro", mensagem="camada nao registrada")

    arq = caminho_camada(chave)
    ck = _cache_key(chave, bbox, str(arq))
    if usar_cache:
        hit = _CACHE.get(ck)
        if hit and (time.time() - hit[0]) < CACHE_TTL_S:
            return hit[1]

    if not arq.exists():
        res = CamadaResult(
            chave, status="ausente", origem=cam.fonte,
            mensagem=f"arquivo {cam.arquivo} nao encontrado em data/vetoriais. "
                     "Execute o workflow 'build-vetorial-data' no GitHub Actions.",
        )
        _CACHE[ck] = (time.time(), res)
        return res

    try:
        import geopandas as gpd  # noqa: PLC0415

        gdf = gpd.read_file(arq, bbox=bbox) if bbox else gpd.read_file(arq)
        if gdf.crs is None:
            gdf = gdf.set_crs(C.CRS_GEOGRAFICO)
        else:
            gdf = gdf.to_crs(C.CRS_GEOGRAFICO)
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].reset_index(drop=True)
        if not len(gdf):
            res = CamadaResult(chave, gdf=gdf, status="vazia", origem=cam.fonte,
                               arquivo=cam.arquivo,
                               mensagem=f"{cam.arquivo} sem feicoes na area consultada")
        else:
            res = CamadaResult(chave, gdf=gdf, status="ok", origem=cam.fonte,
                               arquivo=cam.arquivo, feicoes=len(gdf))
    except Exception as exc:  # noqa: BLE001
        res = CamadaResult(chave, status="erro", origem=cam.fonte, arquivo=cam.arquivo,
                           mensagem=f"{type(exc).__name__}: {exc}")

    if usar_cache:
        _CACHE[ck] = (time.time(), res)
    return res


def inventario_bases() -> list[dict]:
    """Inventario de saude de todas as camadas registradas."""
    out = []
    for chave, cam in sorted(CAMADAS.items()):
        arq = caminho_camada(chave)
        linha = {
            "chave": chave,
            "rotulo": cam.rotulo,
            "arquivo": cam.arquivo,
            "fonte": cam.fonte,
            "papel": cam.papel,
            "obrigatoria": cam.obrigatoria,
            "existe": arq.exists(),
            "tamanho_mb": round(arq.stat().st_size / 1e6, 2) if arq.exists() else None,
            "feicoes": None,
            "crs": None,
            "status": "ausente" if not arq.exists() else "ok",
        }
        if arq.exists():
            try:
                import geopandas as gpd  # noqa: PLC0415
                from pyogrio import read_info  # noqa: PLC0415

                info = read_info(arq)
                linha["feicoes"] = info.get("features")
                linha["crs"] = info.get("crs")
                linha["campos"] = list(info.get("fields", []))[:20]
            except Exception as exc:  # noqa: BLE001
                linha["status"] = f"erro: {type(exc).__name__}"
        out.append(linha)
    return out


def ler_manifesto() -> dict:
    p = C.VETORIAIS / "MANIFEST.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def rotulo_feicao(row, cam: Camada) -> str:
    """Extrai o melhor rotulo textual disponivel de uma feicao."""
    for campo in cam.campos_rotulo:
        if campo in row and row[campo] not in (None, ""):
            return str(row[campo]).strip()
    # Primeiro campo nao geometrico com conteudo textual curto.
    for campo, valor in row.items():
        if campo == "geometry" or valor in (None, ""):
            continue
        s = str(valor)
        if 2 <= len(s) <= 90:
            return s.strip()
    return "-"


# --------------------------------------------------------------------------------------
# Camadas do usuario / OSM
# --------------------------------------------------------------------------------------


def carregar_usuario(caminho: Path) -> CamadaResult:
    """Carrega um arquivo vetorial enviado pelo usuario (KML/KMZ/GPKG/GeoJSON/SHP)."""
    chave = "usuario_" + hashlib.sha1(str(caminho).encode()).hexdigest()[:8]
    p = Path(caminho)
    if not p.exists():
        return CamadaResult(chave, status="ausente", mensagem="arquivo nao encontrado")
    try:
        import geopandas as gpd  # noqa: PLC0415
        import zipfile

        alvo: Any = p
        if p.suffix.lower() == ".kmz":
            with zipfile.ZipFile(p) as zf:
                nome = next((n for n in zf.namelist() if n.lower().endswith(".kml")), None)
                if not nome:
                    return CamadaResult(chave, status="erro", mensagem="KMZ sem .kml interno")
                tmp = C.DATA / "tmp"
                tmp.mkdir(parents=True, exist_ok=True)
                zf.extract(nome, tmp)
                alvo = tmp / nome
        gdf = gpd.read_file(alvo)
        if gdf.crs is None:
            gdf = gdf.set_crs(C.CRS_GEOGRAFICO)
        else:
            gdf = gdf.to_crs(C.CRS_GEOGRAFICO)
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].reset_index(drop=True)
        if not len(gdf):
            return CamadaResult(chave, gdf=gdf, status="vazia", origem="usuario")
        return CamadaResult(chave, gdf=gdf, status="ok", origem="usuario",
                            arquivo=p.name, feicoes=len(gdf))
    except Exception as exc:  # noqa: BLE001
        return CamadaResult(chave, status="erro", mensagem=f"{type(exc).__name__}: {exc}")


def osm_cache_path(lat: float, lon: float, raio_m: int) -> Path:
    key = hashlib.sha1(f"{lat:.4f},{lon:.4f},{raio_m}".encode()).hexdigest()[:12]
    C.CACHE_OSM.mkdir(parents=True, exist_ok=True)
    return C.CACHE_OSM / f"osm_{key}.geojson"


def carregar_osm(lat: float, lon: float, raio_m: int = 3000,
                 forcar: bool = False) -> CamadaResult:
    """Camada OSM/Overpass com cache em disco e degradacao graciosa.

    Devolve status 'ausente' quando nao ha rede nem cache pre-aquecido - o
    Agente 2 sinaliza isso no relatorio em vez de desenhar dados falsos.
    """
    dest = osm_cache_path(lat, lon, raio_m)
    if dest.exists() and not forcar:
        try:
            import geopandas as gpd  # noqa: PLC0415

            gdf = gpd.read_file(dest)
            if len(gdf):
                return CamadaResult("osm", gdf=gdf, status="ok",
                                    origem="OpenStreetMap (Overpass) - cache local",
                                    arquivo=dest.name, feicoes=len(gdf))
        except Exception:  # noqa: BLE001
            pass

    try:
        from ..gis import overpass  # noqa: PLC0415

        fc = overpass.buscar(lat, lon, raio_m)
        if fc is None:
            return CamadaResult("osm", status="ausente",
                                origem="OpenStreetMap (Overpass)",
                                mensagem="Overpass indisponivel e sem cache local")
        dest.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        import geopandas as gpd  # noqa: PLC0415

        gdf = gpd.read_file(dest)
        return CamadaResult("osm", gdf=gdf, status="ok",
                            origem="OpenStreetMap (Overpass) - consulta ao vivo",
                            arquivo=dest.name, feicoes=len(gdf))
    except Exception as exc:  # noqa: BLE001
        return CamadaResult("osm", status="ausente",
                            origem="OpenStreetMap (Overpass)",
                            mensagem=f"indisponivel: {type(exc).__name__}")
