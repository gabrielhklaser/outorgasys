# -*- coding: utf-8 -*-
"""Agente 2 - Inteligencia Espacial, Interseccao Vetorial e Cartografia Automatizada."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from outorgasys import config as C
from outorgasys.agents import agente2_gis as a2
from outorgasys.gis import geo, layers
from outorgasys.gis import skill_bridge as skills
from outorgasys.state import Processo
from outorgasys.ui import (
    aplicar_tema, barra_lateral, cabecalho, chip, chips, fonte,
    mostrar_imagem, mostrar_pendencias, passo, tabela,
)

aplicar_tema()
proc = barra_lateral()

cabecalho("Agente 2 · Inteligencia Espacial e Automacao GIS",
          "SIRGAS 2000 (EPSG:4674) · UTM 22S (EPSG:31982) · raio de seguranca de 500 m")

# ======================================================================================
# 1. Ingestao e validacao das coordenadas
# ======================================================================================

passo(1, "Ingestao e validacao das coordenadas")
st.caption("Informe as coordenadas estritamente em graus decimais.")

coord_atual = (proc.get("geoespacial") or {}).get("coordenadas") or {}
c = st.columns(4)
lat = c[0].number_input("Latitude (graus decimais)", value=float(coord_atual.get("lat") or -29.6842),
                        format="%.6f", min_value=-90.0, max_value=90.0)
lon = c[1].number_input("Longitude (graus decimais)", value=float(coord_atual.get("lon") or -51.0531),
                        format="%.6f", min_value=-180.0, max_value=180.0)
raio_seg = c[2].number_input("Raio de seguranca (m)", min_value=50.0, max_value=2000.0,
                             value=float(C.RAIO_SEGURANCA_M), step=50.0)
raio_ctx = c[3].number_input("Raio de contexto do mapa (m)", min_value=500.0,
                             max_value=10000.0, value=3000.0, step=500.0)

usar_osm = st.checkbox("Consultar OpenStreetMap (Overpass) para vias, drenagem fina, "
                       "nascentes e fontes de poluicao", value=True,
                       help="Usa cache local quando disponivel; degrada graciosamente "
                            "se nao houver rede.")
gerar_mapas = st.checkbox("Gerar as tres pranchas cartograficas (300 DPI)", value=True)

coord = geo.geograficas_para_utm(lat, lon)
c = st.columns(4)
c[0].metric("Fuso UTM", f"{coord['fuso']}")
c[1].metric("E (m)", f"{coord['utm_e']:,.1f}".replace(",", "."))
c[2].metric("N (m)", f"{coord['utm_n']:,.1f}".replace(",", "."))
c[3].metric("EPSG", coord["epsg"].replace("EPSG:", ""))

if proc.get("imovel", {}).get("municipio") and not (proc.get("geoespacial") or {}).get("municipio"):
    pass

st.markdown("")

# ======================================================================================
# 1b. Camadas do usuario
# ======================================================================================

with st.expander("Camadas vetoriais do utilizador (opcional — KML/KMZ/GPKG/GeoJSON/SHP)"):
    st.caption(
        "Envie o limite da propriedade, pocos vizinhos cadastrados, fontes de "
        "poluicao mapeadas ou falhas/fraturas estruturais."
    )
    papeis = {
        "camada_propriedade": "Limite da propriedade / terreno",
        "camada_pocos_vizinhos": "Pocos vizinhos cadastrados",
        "camada_poluicao": "Fontes potenciais de poluicao",
        "camada_falhas": "Falhas / fraturas estruturais",
    }
    for chave, rotulo in papeis.items():
        up = st.file_uploader(rotulo, type=["kml", "kmz", "gpkg", "geojson", "json", "zip"],
                              key=f"up_{chave}")
        if up is not None:
            reg = proc.data.setdefault("camadas_usuario", {}).get(chave)
            dest = proc.dir_arquivos / up.name
            dest.write_bytes(up.getbuffer())
            proc.data.setdefault("camadas_usuario", {})[chave] = {
                "nome": up.name,
                "caminho": C.caminho_relativo(dest),
                "papel": rotulo,
            }
            st.success(f"Camada registrada: {up.name}")
    existentes = proc.get("camadas_usuario") or {}
    if existentes:
        tabela([{"chave": k, "arquivo": (v or {}).get("nome"),
                 "papel": (v or {}).get("papel")} for k, v in existentes.items()])

st.markdown("---")

# ======================================================================================
# 2. Execucao do cruzamento espacial
# ======================================================================================

passo(2, "Cruzamento espacial com as bases vetoriais")

if st.button("🔎 Executar cruzamento espacial", type="primary", width="stretch"):
    with st.spinner("A cruzar bases vetoriais e a gerar as pranchas cartograficas..."):
        try:
            saida = a2.analisar(proc, lat, lon, raio_seguranca=raio_seg,
                                raio_contexto=raio_ctx, gerar_mapas=gerar_mapas,
                                usar_osm=usar_osm)
            proc["geoespacial"] = saida
            if saida.get("municipio") and not (proc.get("imovel") or {}).get("municipio"):
                proc.data.setdefault("imovel", {})["municipio"] = saida["municipio"]
            proc.concluir_agente(2)
            proc.log(2, f"Cruzamento espacial concluido para {lat}, {lon}.")
            proc.salvar()
            st.success("Cruzamento concluido.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            import traceback
            st.error(f"Falha no Agente 2: {type(exc).__name__}: {exc}")
            with st.expander("Detalhes tecnicos"):
                st.code(traceback.format_exc())
            proc.log(2, f"Falha: {type(exc).__name__}: {exc}", nivel="erro")

geo_out = proc.get("geoespacial") or {}

# ======================================================================================
# 3. Resultado
# ======================================================================================

if not geo_out:
    st.info("Execute o cruzamento espacial para ver os resultados.")
    st.stop()

st.markdown("### Contexto fisico identificado")

c = st.columns(2)
with c[0]:
    st.markdown("**Localizacao**")
    d = geo_out.get("detalhes") or {}
    tabela([
        {"Item": "Municipio", "Valor": geo_out.get("municipio") or "-"},
        {"Item": "Codigo IBGE", "Valor": d.get("codigo_municipio") or "-"},
        {"Item": "Regiao hidrografica", "Valor": geo_out.get("regiao_hidrografica") or "-"},
        {"Item": "Bacia hidrografica", "Valor": geo_out.get("bacia_hidrografica") or "-"},
        {"Item": "UPH", "Valor": d.get("uph") or "-"},
        {"Item": "Ottobacia", "Valor": d.get("ottobacia") or "-"},
    ])
with c[1]:
    st.markdown("**Geologia e hidrogeologia**")
    tabela([
        {"Item": "Formacao geologica", "Valor": geo_out.get("formacao_geologica") or "-"},
        {"Item": "Litologia predominante", "Valor": d.get("litologia") or "-"},
        {"Item": "Codigo GEOBANK", "Valor": d.get("codigo_geobank") or "-"},
        {"Item": "Sistema aquifer (sigla)", "Valor": d.get("sistema_aquifero_codigo") or "-"},
        {"Item": "Sistema aquifer (nome)", "Valor": d.get("sistema_aquifero_nome")
         or geo_out.get("sistema_aquifero") or "-"},
        {"Item": "Classe de solo", "Valor": d.get("classe_solo") or "-"},
    ])

cb = geo_out.get("corpo_hidrico_proximo") or {}
c = st.columns(3)
c[0].metric("Corpo hidrico mais proximo", cb.get("nome") or "-")
c[1].metric("Distancia (m)", f"{cb['distancia_m']:,.1f}".replace(",", ".")
            if cb.get("distancia_m") is not None else "-")
c[2].metric("Fonte da distancia", (geo_out.get("detalhes") or {}).get("corpo_hidrico_fonte") or "-")

classif = (geo_out.get("detalhes") or {}).get("classificacao_bacia")
if classif:
    st.warning(
        "**Origem da bacia/regiao hidrografica:** tabela de referencia curada "
        f"(metodo: {classif.get('metodo')}; correspondencia: "
        f"'{classif.get('correspondencia')}'). As camadas poligonais de ottobacias "
        "da ANA nao estavam disponiveis neste ambiente — a classificacao nao foi "
        "obtida por interseccao vetorial."
    )

st.markdown("### Raio de seguranca")
rs = (geo_out.get("detalhes") or {}).get("raio_seguranca") or {}
buf = (geo_out.get("detalhes") or {}).get("buffer") or {}
ocorr = rs.get("ocorrencias") or {}
c = st.columns(3)
c[0].metric("Raio analisado (m)", f"{rs.get('raio_m', raio_seg):,.0f}".replace(",", "."))
c[1].metric("Area do buffer (m2)", f"{buf.get('area_m2'):,.0f}".replace(",", ".")
            if buf.get("area_m2") else "-")
c[2].metric("Ocorrencias detectadas", len(ocorr))
if buf.get("skill_usada"):
    fonte("Buffer gerado pela skill vendoredizada `shapely-compute` (geometria valida: "
          f"{buf.get('valido')}).")
if ocorr:
    tabela([{"Ocorrencia": k, "Feicoes no raio": v} for k, v in ocorr.items()])
else:
    st.caption("Nenhuma ocorrencia identificada nas bases consultadas.")

mostrar_pendencias(geo_out.get("pendencias", []), "Pendencias espaciais")

st.markdown("---")

# ======================================================================================
# 4. Pranchas cartograficas
# ======================================================================================

passo(3, "Pranchas cartograficas e mapa interativo multicamadas")
mapas = geo_out.get("caminho_mapas") or []
mapa_html_rel = geo_out.get("mapa_interativo_html") or (geo_out.get("detalhes", {}).get("mapas", {}).get("interativo"))

if mapas or mapa_html_rel:
    nomes_abas = ["Mapa 1 · Localizacao e Situacao",
                  "Mapa 2 · Geologico Local",
                  "Mapa 3 · Hidrografico e Hidrogeologico"]
    if mapa_html_rel:
        nomes_abas.append("🌐 Mapa Interativo Multicamadas")

    abas = st.tabs(nomes_abas)
    rotulos = ["Mapa de Localizacao e Situacao",
               "Mapa Geologico Local",
               "Mapa Hidrografico e Hidrogeologico Local"]

    for i, (caminho, rotulo) in enumerate(zip(mapas, rotulos)):
        with abas[i]:
            mostrar_imagem(caminho, rotulo)
            p = Path(caminho)
            if not p.is_absolute():
                p = C.caminho_absoluto(p)
            if p.exists():
                with open(p, "rb") as fh:
                    st.download_button("⬇️ Descarregar prancha", data=fh.read(),
                                       file_name=p.name, mime="image/jpeg",
                                       key=f"dl_prancha_{i}", width="stretch")

    if mapa_html_rel and len(abas) > len(mapas):
        with abas[-1]:
            st.markdown("#### 🗺️ Navegador Espacial em Camadas Distintas (Folium / Leaflet)")
            st.caption(
                "Controle de camadas (canto superior direito): alterne entre Satelite Esri, "
                "OpenStreetMap e CartoDB, e ative/desative geologia, hidrogeologia, solos e drenagem. "
                "Use a regua metrica (canto inferior esquerdo) para aferir distancias reais ao poco."
            )
            p_html = Path(mapa_html_rel)
            if not p_html.is_absolute():
                p_html = C.caminho_absoluto(p_html)
            if p_html.exists():
                html_code = p_html.read_text(encoding="utf-8", errors="replace")
                import streamlit.components.v1 as components
                components.html(html_code, height=620, scrolling=True)

                st.download_button(
                    "⬇️ Descarregar Mapa Interativo (HTML Standalone)",
                    data=html_code,
                    file_name="mapa_interativo_outorgasys.html",
                    mime="text/html",
                    width="stretch",
                    key="dl_mapa_html",
                )
            else:
                st.warning("Arquivo HTML do mapa interativo nao encontrado em disco.")

    st.caption("Todas as pranchas contem titulo padronizado, coordenadas do poco, "
               "norte geografico, escala grafica metrica e legenda.")
else:
    st.info("Nenhuma prancha gerada. Reexecute o cruzamento com a opcao de mapas ativa.")
    if geo_out.get("erros"):
        with st.expander("Erros do Agente 2"):
            st.code("\n".join(str(e) for e in geo_out["erros"]))

st.markdown("---")

# ======================================================================================
# 5. Proveniencia e qualidade
# ======================================================================================

passo(4, "Proveniencia das bases e auditoria de qualidade")
prov = geo_out.get("proveniencia") or {}
if prov:
    tabela([{"Camada": k,
             "Status": (v or {}).get("status"),
             "Origem": (v or {}).get("origem"),
             "Feicoes": (v or {}).get("feicoes"),
             "Mensagem": (v or {}).get("mensagem")}
            for k, v in sorted(prov.items())])

pre = (geo_out.get("detalhes") or {}).get("preflight_qualidade") or {}
if pre:
    with st.expander("Preflight de qualidade vetorial (skill geopandas)"):
        st.json(pre)

st.markdown("")
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("💾 Guardar", width="stretch"):
        proc.salvar()
        st.success("Guardado.")
with col2:
    if st.button("➡️ Avancar para o Agente 3", type="primary", width="stretch"):
        proc.salvar()
        st.switch_page("pages/3_Hidrogeologia.py")

with st.expander("Objeto JSON de saida (metadados para os Agentes 4 e 5)"):
    resumido = {
        "coordenadas": geo_out.get("coordenadas"),
        "municipio": geo_out.get("municipio"),
        "bacia_hidrografica": geo_out.get("bacia_hidrografica"),
        "regiao_hidrografica": geo_out.get("regiao_hidrografica"),
        "formacao_geologica": geo_out.get("formacao_geologica"),
        "sistema_aquifero": geo_out.get("sistema_aquifero"),
        "corpo_hidrico_proximo": geo_out.get("corpo_hidrico_proximo"),
        "caminho_mapas": geo_out.get("caminho_mapas"),
    }
    st.code(json.dumps(resumido, ensure_ascii=False, indent=2), language="json")
