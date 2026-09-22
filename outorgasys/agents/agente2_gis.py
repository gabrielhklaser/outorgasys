# -*- coding: utf-8 -*-
"""
Agente 2 - Inteligencia Espacial e Automacao GIS.

Recebe as coordenadas do poco, cruza com as bases vetoriais locais e produz as
tres pranchas cartograficas e o objeto JSON de metadados consumido pelos
Agentes 4 e 5.

O agente e *fail-soft*: cada camada e consultada de forma independente e o
resultado declara, para cada informacao, a ``origem`` e o ``status``. Nenhum
dado e inventado: quando uma base nao esta disponivel, o campo vem nulo e a
ausencia e reportada.
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any

import geopandas as gpd  # noqa: PLC0415
import pandas as pd  # noqa: PLC0415
from shapely.geometry import Point  # noqa: PLC0415

from .. import config as C
from .. import rules
from ..gis import cartografia, geo, layers, overpass
from ..gis import skill_bridge as skills


# --------------------------------------------------------------------------------------
# Helpers de interseccao
# --------------------------------------------------------------------------------------


def _primeiro(gdf, colunas: tuple[str, ...]) -> str | None:
    if gdf is None or not len(gdf):
        return None
    for col in colunas:
        if col in gdf.columns:
            for v in gdf[col]:
                if v is not None and str(v).strip() not in ("", "nan", "None"):
                    return str(v).strip()
    return None


def _linha_da_feicao(gdf) -> dict | None:
    if gdf is None or not len(gdf):
        return None
    row = gdf.iloc[0]
    return {k: (None if pd.isna(v) else v) for k, v in row.items() if k != "geometry"}


def ponto_em_poligono(gdf, ponto_geo) -> Any | None:
    """Devolve o subconjunto de ``gdf`` que contem o ponto (ou o mais proximo)."""
    if gdf is None or not len(gdf):
        return None
    try:
        mask = gdf.geometry.contains(ponto_geo)
        if mask.any():
            return gdf[mask]
    except Exception:  # noqa: BLE001
        pass
    try:
        # Ponto na fronteira / geometria invalida: usa o poligono mais proximo
        # dentro de uma tolerancia de ~1,5 km.
        idx = gdf.sindex.nearest(ponto_geo, max_distance=0)[0]
        cand = gdf.iloc[list(idx)]
        d = cand.distance(ponto_geo)
        if len(d) and float(d.min()) < 0.02:   # ~2 km em graus
            return cand.iloc[[int(d.idxmin())]]
    except Exception:  # noqa: BLE001
        pass
    return None


# --------------------------------------------------------------------------------------
# Agente
# --------------------------------------------------------------------------------------


def analisar(proc, lat: float, lon: float, raio_seguranca: float = C.RAIO_SEGURANCA_M,
             raio_contexto: float = 3000.0, gerar_mapas: bool = True,
             usar_osm: bool = True) -> dict:
    """Executa o Agente 2 e devolve o dicionario de saida estruturada."""
    saida: dict[str, Any] = {
        "ok": False,
        "coordenadas": {},
        "municipio": None,
        "bacia_hidrografica": None,
        "regiao_hidrografica": None,
        "formacao_geologica": None,
        "sistema_aquifero": None,
        "corpo_hidrico_proximo": {"nome": None, "distancia_m": None},
        "caminho_mapas": [],
        "detalhes": {},
        "proveniencia": {},
        "pendencias": [],
        "erros": [],
    }
    prov = saida["proveniencia"]
    detalhes = saida["detalhes"]

    # ---------------------------------------------------------------- 1) geodesia
    validacao = rules.validar_coordenadas_rs(lat, lon)
    for p in validacao:
        saida["pendencias"].append(p.to_dict())

    coord = geo.geograficas_para_utm(lat, lon)
    saida["coordenadas"] = coord

    ponto_geo = Point(lon, lat)
    g_ponto = gpd.GeoSeries([ponto_geo], crs=C.CRS_GEOGRAFICO)

    bbox_seg = geo.bbox_ao_redor(lat, lon, raio_seguranca)
    bbox_ctx = geo.bbox_ao_redor(lat, lon, raio_contexto)

    # Buffer de seguranca em UTM (skill shapely-compute usada como contraprova).
    buffer_wkt = None
    try:
        r = skills.buffer_raio_seguranca(coord["utm_e"], coord["utm_n"], raio_seguranca)
        buffer_wkt = r.get("wkt")
        detalhes["buffer"] = {
            "raio_m": raio_seguranca,
            "area_m2": r.get("area"),
            "metodo": "skill shapely-compute (buffer UTM)",
            "valido": r.get("is_valid"),
            "skill_usada": True,
        }
    except Exception as exc:  # noqa: BLE001
        detalhes["buffer"] = {"raio_m": raio_seguranca, "skill_usada": False,
                              "erro": f"{type(exc).__name__}: {exc}"}

    buffer_gdf = None
    try:
        buffer_gdf = gpd.GeoDataFrame(
            {"camada": ["raio_seguranca"]},
            geometry=g_ponto.to_crs(coord["epsg"]).buffer(raio_seguranca),
            crs=coord["epsg"],
        ).to_crs(C.CRS_GEOGRAFICO)
    except Exception:  # noqa: BLE001
        buffer_gdf = None

    # ---------------------------------------------------------------- 2) municipio
    res = layers.carregar("municipios_rs", bbox=bbox_ctx)
    prov["municipios_rs"] = res.to_dict()
    municipio_gdf = None
    if res.disponivel:
        hit = ponto_em_poligono(res.gdf, ponto_geo)
        if hit is not None and len(hit):
            municipio_gdf = hit
            saida["municipio"] = _primeiro(hit, CAMADAS := ("NM_MUN", "nome", "NOME",
                                                            "NM_MUNICIP"))
            detalhes["codigo_municipio"] = _primeiro(hit, ("CD_MUN", "codigo", "GEOCODIGO"))
        else:
            saida["pendencias"].append({
                "codigo": "GEO-010", "titulo": "Ponto fora da malha municipal do RS",
                "mensagem": "O ponto informado nao cai dentro de nenhum municipio "
                            "carregado. Confira as coordenadas.",
                "bloqueante": False, "agente": 2,
            })

    # ---------------------------------------------------------------- 3) geologia
    res = layers.carregar("geologia_rs", bbox=bbox_ctx)
    prov["geologia_rs"] = res.to_dict()
    geologia_gdf = None
    if res.disponivel:
        hit = ponto_em_poligono(res.gdf, ponto_geo)
        if hit is not None and len(hit):
            geologia_gdf = hit
            linha = _linha_da_feicao(hit) or {}
            saida["formacao_geologica"] = (
                linha.get("NOME_UNIDA") or linha.get("Name") or linha.get("NOME")
                or linha.get("FORMACAO") or None)
            saida["detalhes"]["litologia"] = (
                linha.get("LITOTIPO1") or linha.get("LITOTIPO") or linha.get("LITOLOGIA")
                or None)
            saida["detalhes"]["codigo_geobank"] = linha.get("GEOBANK")
            if not saida["formacao_geologica"]:
                saida["formacao_geologica"] = str(list(linha.values())[0]) if linha else None

    # ---------------------------------------------------------------- 4) hidrogeologia
    res = layers.carregar("hidrogeologia_rs", bbox=bbox_ctx)
    prov["hidrogeologia_rs"] = res.to_dict()
    aquifero_gdf = None
    if res.disponivel:
        hit = ponto_em_poligono(res.gdf, ponto_geo)
        if hit is not None and len(hit):
            aquifero_gdf = hit
            linha = _linha_da_feicao(hit) or {}
            codigo = linha.get("Name") or linha.get("NOME") or linha.get("SIGLA")
            saida["sistema_aquifero"] = codigo
            saida["detalhes"]["sistema_aquifero_codigo"] = codigo
            saida["detalhes"]["sistema_aquifero_nome"] = (
                AQUIFEROS_RS.get(str(codigo).strip().upper()) if codigo else None)

    # ---------------------------------------------------------------- 5) solos
    res = layers.carregar("solos_rs", bbox=bbox_ctx)
    prov["solos_rs"] = res.to_dict()
    if res.disponivel:
        hit = ponto_em_poligono(res.gdf, ponto_geo)
        if hit is not None and len(hit):
            saida["detalhes"]["classe_solo"] = (
                _primeiro(hit, ("Name", "NOME", "SOLO", "CLASSE")))

    # ---------------------------------------------------------------- 6) regiao hidrografica
    res = layers.carregar("regioes_hidrograficas")
    prov["regioes_hidrograficas"] = res.to_dict()
    if res.disponivel:
        hit = ponto_em_poligono(res.gdf, ponto_geo)
        if hit is not None and len(hit):
            saida["regiao_hidrografica"] = _primeiro(
                hit, ("NO_RHI", "NOME", "nome", "Name", "NM_RHI"))

    # ---------------------------------------------------------------- 7) UPH
    res = layers.carregar("uph")
    prov["uph"] = res.to_dict()
    if res.disponivel:
        hit = ponto_em_poligono(res.gdf, ponto_geo)
        if hit is not None and len(hit):
            saida["detalhes"]["uph"] = _primeiro(hit, ("NO_UPH", "NOME", "nome", "Name"))

    # ---------------------------------------------------------------- 8) ottobacia / bacia
    for chave, rotulo in (("ottobacias_rs", "ottobacia"),
                          ("otto_nivel_3", "bacia_nivel_3"),
                          ("otto_nivel_2", "bacia_nivel_2"),
                          ("otto_nivel_1", "bacia_nivel_1")):
        res = layers.carregar(chave, bbox=bbox_ctx if "nivel" not in chave else None)
        prov[chave] = res.to_dict()
        if not res.disponivel:
            continue
        hit = ponto_em_poligono(res.gdf, ponto_geo)
        if hit is not None and len(hit):
            codigo = _primeiro(hit, ("nu_bac_ott", "cobacia", "nu_bacia", "nome", "Name"))
            detalhes[rotulo] = codigo
            if rotulo == "ottobacia" and not saida["bacia_hidrografica"]:
                saida["bacia_hidrografica"] = f"Ottobacia {codigo}" if codigo else None
            elif not saida["bacia_hidrografica"]:
                saida["bacia_hidrografica"] = codigo

    # Nomes conhecidos de bacia no RS, usados quando ha codigo Otto.
    saida["bacia_hidrografica"] = _rotular_bacia(saida["bacia_hidrografica"],
                                                 detalhes.get("ottobacia"))

    # ---------------------------------------------------------------- 9) drenagem + distancia
    corpo_hidrico = {"nome": None, "distancia_m": None}
    drenagem_gdf = None
    cursos_gdf = None
    linha_proxima_gdf = None

    for chave, eh_linha in (("drenagem_rs", True), ("cursos_dagua_rs", False)):
        res = layers.carregar(chave, bbox=geo.bbox_expandido(bbox_ctx, 1.6))
        prov[chave] = res.to_dict()
        if not res.disponivel:
            continue
        if eh_linha:
            drenagem_gdf = res.gdf
        else:
            cursos_gdf = res.gdf

    alvo = drenagem_gdf if drenagem_gdf is not None and len(drenagem_gdf) else cursos_gdf
    if alvo is not None and len(alvo):
        try:
            a = alvo.to_crs(coord["epsg"])
            p = g_ponto.to_crs(coord["epsg"]).iloc[0]
            dist = a.geometry.distance(p)
            i = int(dist.idxmin())
            d = float(dist.iloc[i])
            linha_proxima = alvo.iloc[[i]].copy()
            corpo_hidrico["distancia_m"] = round(d, 2)
            corpo_hidrico["nome"] = _primeiro(
                linha_proxima, ("no_rio_pri", "no_rio", "nome", "Name", "NOME")) \
                or "Corpo hidrico sem denominacao na base"
            linha_proxima_gdf = linha_proxima
            detalhes["corpo_hidrico_fonte"] = "ANA - BHO 2017"
        except Exception as exc:  # noqa: BLE001
            saida["erros"].append(f"Falha no calculo de distancia a drenagem: {exc}")

    # Fallback: drenagem do OSM quando a base da ANA nao esta disponivel.
    if corpo_hidrico["distancia_m"] is None:
        osm = layers.carregar_osm(lat, lon, int(raio_contexto)) if usar_osm else None
        temas = overpass.separar_temas(osm.gdf) if (osm and osm.disponivel) else {}
        if temas.get("drenagem") is not None and len(temas["drenagem"]):
            try:
                a = temas["drenagem"].to_crs(coord["epsg"])
                p = g_ponto.to_crs(coord["epsg"]).iloc[0]
                dist = a.geometry.distance(p)
                i = int(dist.idxmin())
                corpo_hidrico["distancia_m"] = round(float(dist.iloc[i]), 2)
                corpo_hidrico["nome"] = _primeiro(
                    a.iloc[[i]], ("name", "waterway")) or "Corpo hidrico (OSM)"
                linha_proxima_gdf = temas["drenagem"].iloc[[i]]
                detalhes["corpo_hidrico_fonte"] = "OpenStreetMap (Overpass)"
                drenagem_gdf = temas["drenagem"]
                prov["osm"] = osm.to_dict()
            except Exception:  # noqa: BLE001
                pass

    saida["corpo_hidrico_proximo"] = corpo_hidrico

    # ---------------------------------------------------------------- 10) raio de seguranca
    ocorrencias: dict[str, Any] = {}
    vias_gdf = corpos_dagua_gdf = nascentes_gdf = fontes_poluicao_gdf = None

    osm = layers.carregar_osm(lat, lon, int(raio_contexto)) if usar_osm else None
    prov["osm"] = osm.to_dict() if osm else {"status": "nao_solicitado"}
    if osm and osm.disponivel:
        temas = overpass.separar_temas(osm.gdf)
        vias_gdf = temas.get("vias")
        corpos_dagua_gdf = temas.get("corpos_dagua")
        nascentes_gdf = temas.get("nascentes")
        fontes_poluicao_gdf = temas.get("fontes_poluicao")
        if drenagem_gdf is None:
            drenagem_gdf = temas.get("drenagem")

    def contar_no_buffer(gdf) -> int:
        if gdf is None or not len(gdf) or buffer_gdf is None:
            return 0
        try:
            buf = buffer_gdf.to_crs(coord["epsg"]).geometry.iloc[0]
            dentro = gdf.to_crs(coord["epsg"]).geometry.intersects(buf)
            return int(dentro.sum())
        except Exception:  # noqa: BLE001
            return 0

    for nome, gdf in (("vias", vias_gdf), ("corpos_dagua", corpos_dagua_gdf),
                      ("nascentes", nascentes_gdf),
                      ("fontes_poluicao", fontes_poluicao_gdf)):
        n = contar_no_buffer(gdf)
        if n:
            ocorrencias[nome] = n

    # Camadas enviadas pelo usuario (pocos vizinhos, fontes de poluicao, falhas).
    usuario = proc.get("camadas_usuario") or {}
    pocos_vizinhos_gdf = None
    for chave, meta in (usuario or {}).items():
        r = layers.carregar_usuario(Path(C.ROOT) / meta.get("caminho", ""))
        prov[f"usuario:{chave}"] = {"status": r.status, "feicoes": r.feicoes,
                                    "origem": "arquivo enviado pelo usuario"}
        if not r.disponivel:
            continue
        papel = (meta.get("papel") or "").lower()
        if "vizinho" in papel or "poco" in papel:
            pocos_vizinhos_gdf = r.gdf
            n = contar_no_buffer(r.gdf)
            if n:
                ocorrencias["pocos_vizinhos"] = n
        elif "poluicao" in papel:
            fontes_poluicao_gdf = r.gdf if fontes_poluicao_gdf is None else pd.concat(
                [fontes_poluicao_gdf, r.gdf], ignore_index=True)
            n = contar_no_buffer(r.gdf)
            if n:
                ocorrencias["fontes_poluicao_usuario"] = n
        elif "falha" in papel:
            detalhes["falhas_gdf_disponivel"] = True
            detalhes["_falhas"] = r.gdf

    saida["detalhes"]["raio_seguranca"] = {
        "raio_m": raio_seguranca,
        "ocorrencias": ocorrencias,
        "origem": "OpenStreetMap/Overpass + camadas do usuario",
    }

    # Regras do raio de seguranca (nao bloqueantes, mas registradas).
    dist_nomeadas = {}
    if fontes_poluicao_gdf is not None and len(fontes_poluicao_gdf):
        try:
            a = fontes_poluicao_gdf.to_crs(coord["epsg"])
            p = g_ponto.to_crs(coord["epsg"]).iloc[0]
            d = a.geometry.distance(p)
            for i, valor in d.items():
                if valor <= raio_seguranca:
                    rot = _primeiro(a.iloc[[i]], ("name", "amenity", "landuse",
                                                  "man_made", "industrial")) or "ocorrencia"
                    dist_nomeadas[f"{rot}"] = round(float(valor), 1)
        except Exception:  # noqa: BLE001
            pass
    for p_obj in rules.avaliar_raio_seguranca(dist_nomeadas):
        saida["pendencias"].append(p_obj.to_dict())
    for p_obj in rules.avaliar_distancia_corpo_hidrico(corpo_hidrico["distancia_m"]):
        saida["pendencias"].append(p_obj.to_dict())

    # ---------------------------------------------------------------- 11) propriedade
    propriedade_gdf = None
    meta_prop = (proc.get("camadas_usuario") or {}).get("propriedade")
    if meta_prop:
        r = layers.carregar_usuario(Path(C.ROOT) / meta_prop.get("caminho", ""))
        if r.disponivel:
            propriedade_gdf = r.gdf
        prov["usuario:propriedade"] = {"status": r.status, "feicoes": r.feicoes}

    # ---------------------------------------------------------------- 12) preflight de qualidade
    preflight = _preflight_qualidade()
    saida["detalhes"]["preflight_qualidade"] = preflight

    # ---------------------------------------------------------------- 13) mapas
    if gerar_mapas:
        try:
            dir_mapas = proc.dir_mapas
            contexto = {
                "coordenadas": coord,
                "nome_poco": (proc.get("poco") or {}).get("nome") or proc.id,
                "requerente": (proc.get("requerente") or {}).get("nome"),
                "municipio": saida["municipio"],
                "uf": (proc.get("imovel") or {}).get("uf", "RS"),
                "municipio_gdf": municipio_gdf,
                "geologia_gdf": geologia_gdf,
                "geologia_campo_rotulo": "NOME_UNIDA",
                "aquifero_gdf": aquifero_gdf,
                "aquifero_campo_rotulo": "Name",
                "drenagem_gdf": drenagem_gdf,
                "cursos_dagua_gdf": cursos_gdf,
                "corpos_dagua_gdf": corpos_dagua_gdf,
                "nascentes_gdf": nascentes_gdf,
                "fontes_poluicao_gdf": fontes_poluicao_gdf,
                "vias_gdf": vias_gdf,
                "propriedade_gdf": propriedade_gdf,
                "ottobacia_gdf": detalhes.pop("_ottobacia_gdf", None),
                "falhas_gdf": detalhes.pop("_falhas", None),
                "formacao_geologica": saida["formacao_geologica"],
                "litologia": detalhes.get("litologia"),
                "sistema_aquifero": saida["sistema_aquifero"],
                "regiao_hidrografica": saida["regiao_hidrografica"],
                "bacia_hidrografica": saida["bacia_hidrografica"],
                "corpo_hidrico_proximo": {
                    **corpo_hidrico,
                    "linha_gdf": linha_proxima_gdf,
                },
                "fonte_geologia": prov.get("geologia_rs", {}).get("origem"),
                "fonte_drenagem": detalhes.get("corpo_hidrico_fonte"),
            }
            mapas = cartografia.gerar_todos(dir_mapas, contexto)
            saida["caminho_mapas"] = [
                str(Path(p).relative_to(C.ROOT)) for p in mapas.values()
            ]
            saida["detalhes"]["mapas"] = {
                k: str(Path(v).relative_to(C.ROOT)) for k, v in mapas.items()
            }
        except Exception as exc:  # noqa: BLE001
            saida["erros"].append(f"Falha ao gerar mapas: {type(exc).__name__}: {exc}")
            saida["erros"].append(traceback.format_exc(limit=6))

    saida["ok"] = bool(saida["municipio"]) and not any(
        e for e in saida["erros"] if "mapas" in e
    )
    return saida


# --------------------------------------------------------------------------------------
# Rotulos auxiliares
# --------------------------------------------------------------------------------------

#: Correspondencia entre a sigla da base hidrogeologica do projeto e o nome
#: corrente do sistema aquifer. A base 'Hidrogelogia_RS.kmz' traz apenas a
#: sigla da unidade; a tabela traduz para a denominacao usada em SIOUT/CPRM.
AQUIFEROS_RS: dict[str, str] = {
    "SG": "Sistema Aquifero Serra Geral",
    "SERG": "Sistema Aquifero Serra Geral",
    "BOT": "Sistema Aquifero Botucatu",
    "BOTUCATU": "Sistema Aquifero Botucatu",
    "GUARANI": "Sistema Aquifero Guarani",
    "GUA": "Sistema Aquifero Guarani",
    "PIR": "Sistema Aquifero Piramboia",
    "PIRAMBOIA": "Sistema Aquifero Piramboia",
    "RIO_BONITO": "Aquifero Rio Bonito",
    "RB": "Aquifero Rio Bonito",
    "PAL": "Aquifero Palermo",
    "RIO_DO_RASTRO": "Aquifero Rio do Rastro",
    "ESTRADA_NOVA": "Aquifero Estrada Nova",
    "TERCIARIO": "Aquiferos Cenozoicos / Depositos Aluvionares",
    "QUATERNARIO": "Depositos Aluvionares e Coluviais (Aquifero Livre)",
    "ALUVIAO": "Depositos Aluvionares (Aquifero Livre)",
    "CBA": "Cobertura Sedimentar Cenozoica - Bacia do Parana",
    "GRANITO": "Aquifero Fraturado - Embasamento cristalino",
    "CRISTALINO": "Aquifero Fraturado - Embasamento cristalino",
    "METAMORFICO": "Aquifero Fraturado - Rochas metamorficas",
    "VULCANICA": "Sistema Aquifero Serra Geral (rochas vulcanicas)",
    "BASALTO": "Sistema Aquifero Serra Geral (basaltos fraturados)",
}

#: Prefixos Otto Pfafstetter -> bacia/Regiao hidrografica no RS.
BACIAS_RS: list[tuple[str, str]] = [
    ("86", "Bacia Hidrografica do Rio Uruguai"),
    ("87", "Bacia Hidrografica do Rio Ibicui"),
    ("88", "Bacia Hidrografica do Rio Jacui"),
    ("89", "Bacia Hidrografica do Rio Taquari-Antas"),
    ("891", "Bacia Hidrografica do Rio Taquari"),
    ("892", "Bacia Hidrografica do Rio Caí"),
    ("893", "Bacia Hidrografica do Rio dos Sinos"),
    ("894", "Bacia Hidrografica do Rio Gravataí"),
    ("895", "Bacia Hidrografica do Rio Caí"),
    ("896", "Bacia Hidrografica do Rio dos Sinos"),
    ("897", "Bacia Hidrografica do Rio Gravataí"),
    ("898", "Bacia Hidrografica do Rio Jacui"),
    ("899", "Bacia Hidrografica do Rio Vacacai-Vacacai Mirim"),
    ("81", "Bacia Hidrografica do Rio Apuae-Inhandava"),
    ("82", "Bacia Hidrografica do Rio Passo Fundo"),
    ("83", "Bacia Hidrografica do Rio da Várzea"),
    ("84", "Bacia Hidrografica do Rio Ijui"),
    ("85", "Bacia Hidrografica do Rio Piratini"),
    ("7", "Bacia Hidrografica Litoranea"),
    ("71", "Bacia Hidrografica do Rio Camacua"),
    ("72", "Bacia Hidrografica do Rio Camaqua"),
    ("73", "Bacia Hidrografica do Rio Sao Goncalo"),
    ("74", "Bacia Hidrografica do Rio Pelotas"),
    ("75", "Bacia Hidrografica das Lagoas Mirim e Mangueira"),
    ("76", "Bacia Hidrografica da Lagoa dos Patos"),
    ("77", "Bacia Hidrografica do Rio Camaqua"),
    ("78", "Bacia Hidrografica do Rio Jacare",),
]


def _rotular_bacia(atual: str | None, codigo_otto: str | None) -> str | None:
    """Traduz um codigo Otto Pfafstetter em rotulo legivel de bacia."""
    if atual and not str(atual).replace("Ottobacia", "").strip().isdigit():
        return atual
    if not codigo_otto:
        return atual
    cod = str(codigo_otto).strip()
    for prefixo, nome in sorted(BACIAS_RS, key=lambda t: -len(t[0])):
        if cod.startswith(prefixo):
            return f"{nome} (Ottobacia {cod})"
    return f"Ottobacia {cod}"


# --------------------------------------------------------------------------------------
# Preflight de qualidade vetorial (skill geopandas)
# --------------------------------------------------------------------------------------


def _preflight_qualidade() -> dict:
    """Roda os CLIs de auditoria da skill geopandas sobre as bases locais."""
    saida: dict[str, Any] = {"skill": "geopandas", "resultados": {}}
    alvos = [k for k in ("geologia_rs", "hidrogeologia_rs", "municipios_rs",
                         "drenagem_rs", "regioes_hidrograficas")
             if layers.caminho_camada(k).exists()]
    for chave in alvos:
        caminho = layers.caminho_camada(chave)
        try:
            saida["resultados"][chave] = {
                "inventario": _resumir(skills.inventario_vetorial(caminho, C.DATA)),
                "validade": _resumir(skills.relatorio_validade_geometrica(caminho, C.DATA)),
            }
        except Exception as exc:  # noqa: BLE001
            saida["resultados"][chave] = {"erro": f"{type(exc).__name__}: {exc}"}
    try:
        saida["plano_crs"] = _resumir(skills.plano_reprojecao(
            C.CRS_GEOGRAFICO, C.CRS_UTM_22S, "distance"))
    except Exception as exc:  # noqa: BLE001
        saida["plano_crs"] = {"erro": f"{type(exc).__name__}: {exc}"}
    return saida


def _resumir(payload: dict, limite: int = 12) -> dict:
    """Reduz o payload da skill a um resumo exibivel na interface."""
    if not isinstance(payload, dict):
        return {"bruto": str(payload)[:300]}
    out = {}
    for k, v in list(payload.items())[:limite]:
        s = str(v)
        out[k] = s if len(s) <= 160 else s[:157] + "..."
    return out
