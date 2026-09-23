# -*- coding: utf-8 -*-
"""
OutorgaSys - plataforma de automacao de processos de outorga de agua subterranea
no Rio Grande do Sul (SIOUT RS).

Esta e a pagina do ORQUESTRADOR CENTRAL: apresenta o painel de estado dos seis
agentes, o inventario das bases vetoriais e o acesso rapido a cada etapa.
"""

from __future__ import annotations

import streamlit as st

from outorgasys import config as C
from outorgasys.gis import layers
from outorgasys.gis import skill_bridge as skills
from outorgasys.ui import aplicar_tema, barra_lateral, cabecalho, chip, chips, mostrar_imagem

aplicar_tema()
proc = barra_lateral()

cabecalho("Orquestrador Central", C.TITULO_SISTEMA)

# Processo de exemplo pronto para validacao ponta a ponta.
exemplo = C.PROCESSOS / f"{C.PROCESSO_EXEMPLO}.json"
if proc.get("id") != C.PROCESSO_EXEMPLO:
    with st.container():
        c1, c2 = st.columns([3, 1])
        with c1:
            if exemplo.exists():
                st.markdown(
                    '<div class="out-panel"><b>Processo de exemplo disponivel</b><br/>'
                    "Poco tubular de 6&quot; em Campo Bom/RS, com os seis agentes "
                    "ja executados: cruzamento espacial, ensaio de 24 h, quadro de "
                    "vazao, laudo em PDF e triagem de defeitos. Use-o para validar "
                    "a plataforma ponta a ponta.</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="out-panel"><b>Gerar o processo de exemplo</b><br/>'
                    "Percorre os seis agentes sobre um poco tubular de 6&quot; em "
                    "Campo Bom/RS (-29,6842; -51,0531) e deixa o processo pronto, "
                    "com mapas, graficos, laudo em PDF e minuta SIOUT. Leva cerca "
                    "de 30 segundos. Tambem pode ser gerado por linha de comando: "
                    "<code>.venv/bin/python scripts/semente_campo_bom.py</code></div>",
                    unsafe_allow_html=True,
                )
        with c2:
            if exemplo.exists():
                if st.button("▶️ Abrir exemplo", type="primary", width="stretch"):
                    from outorgasys.state import trocar_processo

                    trocar_processo(st.session_state, C.PROCESSO_EXEMPLO)
                    st.rerun()
            else:
                if st.button("🧪 Gerar exemplo", type="primary", width="stretch"):
                    with st.spinner("A percorrer os seis agentes sobre o poco de "
                                    "Campo Bom/RS..."):
                        try:
                            from scripts.semente_campo_bom import construir

                            construir(limpar=False)
                        except Exception:  # noqa: BLE001
                            import subprocess
                            import sys as _sys

                            subprocess.run(
                                [_sys.executable,
                                 str(C.ROOT / "scripts" / "semente_campo_bom.py")],
                                cwd=str(C.ROOT), check=False)
                    st.rerun()

# --------------------------------------------------------------------------------------
# Estado do processo
# --------------------------------------------------------------------------------------

concluidos = set(proc.get("agentes_concluidos") or [])
cols = st.columns(6)
for i, (num, (nome, desc)) in enumerate(C.AGENTES.items()):
    with cols[i]:
        ok = num in concluidos
        st.markdown(
            f'<div class="out-panel" style="min-height:118px">'
            f'<div style="font-size:0.72rem;color:#888">AGENTE {num}</div>'
            f'<div style="font-weight:700;color:#1f4e79;font-size:0.86rem">'
            f'{nome.split("(")[0]}</div>'
            f'<div style="margin-top:6px">{chip("concluido" if ok else "pendente", "ok" if ok else "off")}</div>'
            f'<div class="out-step" style="margin-top:6px">{desc}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("")

col_esq, col_dir = st.columns([1.35, 1])

# --------------------------------------------------------------------------------------
# Trilha de execucao
# --------------------------------------------------------------------------------------

with col_esq:
    st.subheader("Trilha de execucao")
    etapas = [
        (1, "Triagem, cadastro e validacao documental",
         "pages/1_Triagem.py",
         "Enquadramento do poco, uploads obrigatorios, cadastro de equipamentos, "
         "padrao de explotacao e finalidades."),
        (2, "Inteligencia espacial e automatizacao GIS",
         "pages/2_Inteligencia_Espacial.py",
         "Coordenadas SIRGAS 2000 / UTM 22S, cruzamento vetorial, raio de "
         "seguranca de 500 m e as tres pranchas cartograficas a 300 DPI."),
        (3, "Processamento hidrogeologico e graficos",
         "pages/3_Hidrogeologia.py",
         "Theis / Cooper-Jacob / Jacob-Lohman sobre a planilha do ensaio de 24 h."),
        (4, "Balanco hidrico, restricoes e equipamentos",
         "pages/4_Balanco_Hidrico.py",
         "Auditoria da motobomba, hidrometro e reservacao; Quadro de Vazao da "
         "Intervencao do SIOUT RS."),
        (5, "Emissao do relatorio tecnico e minuta SIOUT",
         "pages/5_Relatorio_Final.py",
         "Laudo + Memorial Descritivo em Markdown, PDF assinavel e minuta."),
        (6, "Triagem de defeitos e engenharia de correcoes",
         "pages/6_Agente_Dev.py",
         "Coleta, classifica e propoe correcoes para todos os defeitos do fluxo."),
    ]
    for num, titulo, pagina, desc in etapas:
        ok = num in concluidos
        with st.container():
            c1, c2 = st.columns([0.14, 0.86])
            with c1:
                st.markdown(chip(f"Agente {num}", "ok" if ok else "off"),
                            unsafe_allow_html=True)
            with c2:
                st.markdown(f"**{titulo}**")
                st.caption(desc)
                if st.button("Abrir etapa", key=f"ir_{num}", width="stretch"):
                    st.switch_page(pagina)
        st.markdown("<hr style='margin:0.45rem 0;border:none;border-top:1px solid #eceff1'>",
                    unsafe_allow_html=True)

# --------------------------------------------------------------------------------------
# Inventario das bases
# --------------------------------------------------------------------------------------

with col_dir:
    st.subheader("Bases vetoriais")
    inventario = layers.inventario_bases()
    ok_n = sum(1 for c in inventario if c.get("existe"))
    st.metric("Camadas disponiveis", f"{ok_n}/{len(inventario)}")
    for c in inventario:
        estado = "ok" if c.get("existe") else ("bloqueio" if c.get("obrigatoria") else "off")
        tamanho = f" · {c['tamanho_mb']} MB" if c.get("tamanho_mb") else ""
        feicoes = f" · {c['feicoes']} feicoes" if c.get("feicoes") else ""
        st.markdown(
            f'{chip(c["chave"], estado)}<span class="out-fonte">{tamanho}{feicoes}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("Habilidades integradas")
    disp = skills.skills_disponiveis()
    for nome in ("geomaster", "geopandas", "shapely-compute"):
        st.markdown(chip(nome, "ok" if disp.get(nome) else "bloqueio"),
                    unsafe_allow_html=True)
    with st.expander("Como as skills sao usadas"):
        st.markdown(
            """
            - **shapely-compute** (`skills/shapely-compute/shapely_compute.py`)
              → buffer do raio de seguranca de 500 m, distancias euclidianas
              metricas, predicados `contains`/`within` e validacao de geometrias.
            - **geopandas** (`skills/geopandas/scripts/*.py`)
              → preflight de qualidade vetorial: `vector_inventory`,
              `geometry_validity_report`, `crs_reprojection_plan`,
              `spatial_join_audit` e `sensitive_coordinates_checklist`.
            - **geomaster** (`skills/geomaster/references/*.md`)
              → referencia normativa de geodesia, projecoes e metodos, citada
              nas escolhas de SIRGAS 2000 e UTM 22S.
            """
        )

# --------------------------------------------------------------------------------------
# Ultimos mapas / graficos
# --------------------------------------------------------------------------------------

geo = proc.get("geoespacial") or {}
mapas = geo.get("caminho_mapas") or []
if mapas:
    st.markdown("---")
    st.subheader("Ultimas pranchas geradas")
    cols = st.columns(3)
    for i, m in enumerate(mapas):
        with cols[i]:
            mostrar_imagem(m)

st.markdown("---")
st.caption(
    "OutorgaSys · Automacao de processos de outorga de agua subterranea · "
    "SIOUT RS · ABNT NBR 12212:2017 e NBR 12244:2006 · "
    "Portaria GM/MS n. 888/2021 · norma CEGM/CREA-RS n. 08/2022"
)
