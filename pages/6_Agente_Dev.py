# -*- coding: utf-8 -*-
"""Agente 6 - Triagem de Defeitos e Engenharia de Correcoes."""

from __future__ import annotations

import json
import traceback

import streamlit as st

from outorgasys import config as C
from outorgasys.agents import agente6_dev as a6
from outorgasys.ui import (
    aplicar_tema, barra_lateral, cabecalho, chip, download_arquivo, fonte,
    passo, tabela,
)

aplicar_tema()
proc = barra_lateral()

cabecalho("Agente 6 · Triagem de Defeitos e Engenharia de Correcoes",
          "Coleta, classifica e propoe correcoes para todos os defeitos do fluxo")

st.markdown(
    '<div class="out-panel">O Agente 6 recolhe os erros, avisos, pendencias e '
    "degradacoes registrados pelos Agentes 1 a 5, cruza-os com o estado do "
    "ambiente (skills vendorizadas, pacotes Python e bases vetoriais) e devolve "
    "um plano de correcao priorizado. <b>Nada e executado fora do processo</b>: "
    "nenhuma issue e aberta e nenhum commit e enviado sem decisao do operador."
    "</div>",
    unsafe_allow_html=True,
)

# ======================================================================================
# 1. Execucao da triagem
# ======================================================================================

passo(1, "Execucao da triagem")

col1, col2 = st.columns([1, 2])
with col1:
    if st.button("🩺 Executar triagem de defeitos", type="primary",
                 width="stretch"):
        with st.spinner("A recolher pendencias, diagnosticar o ambiente e montar "
                        "o plano de correcao..."):
            try:
                saida = a6.executar(proc, salvar=True)
                proc.salvar()
                if saida.get("erro"):
                    st.error(f"Falha na triagem: {saida['erro']}")
                else:
                    st.success(
                        f"Triagem concluida: {saida['resumo'].get('total', 0)} "
                        f"achado(s), {saida['resumo'].get('bloqueantes', 0)} "
                        "bloqueante(s).")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha no Agente 6: {type(exc).__name__}: {exc}")
                with st.expander("Detalhes tecnicos"):
                    st.code(traceback.format_exc())
                proc.log(6, f"Falha: {type(exc).__name__}: {exc}", nivel="erro")

# A triagem tambem e executada em memoria para exibir o estado corrente.
try:
    achados = a6.plano_correcao(a6.coletar(proc))
    resumo = a6.resumo(achados)
except Exception as exc:  # noqa: BLE001
    st.error(f"Falha ao recolher os achados: {type(exc).__name__}: {exc}")
    st.stop()

with col2:
    c = st.columns(4)
    c[0].metric("Achados", resumo.get("total", 0))
    c[1].metric("Bloqueantes", resumo.get("bloqueantes", 0))
    c[2].metric("Criticos", (resumo.get("por_severidade") or {}).get("critico", 0))
    c[3].metric("Agentes afetados", len(resumo.get("por_agente") or {}))

if not achados:
    st.success(
        "Nenhum defeito identificado neste processo nem no ambiente. O fluxo esta "
        "limpo."
    )
else:
    st.markdown(f"Existem **{resumo['total']}** achado(s), dos quais "
                f"**{resumo['bloqueantes']}** bloqueia(m) a emissao do laudo.")

st.markdown("---")

# ======================================================================================
# 2. Distribuicao
# ======================================================================================

passo(2, "Distribuicao dos achados")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**Por severidade**")
    tabela([{"Severidade": k, "Quantidade": v}
            for k, v in sorted((resumo.get("por_severidade") or {}).items(),
                               key=lambda t: a6.SEVERIDADES.get(t[0], 9))])
with c2:
    st.markdown("**Por agente**")
    tabela([{"Agente": (C.AGENTES.get(int(k), (f"Agente {k}", ""))[0]
                        if k.isdigit() else "Ambiente"),
             "Quantidade": v}
            for k, v in sorted((resumo.get("por_agente") or {}).items())])
with c3:
    st.markdown("**Por categoria**")
    tabela([{"Categoria": k, "Quantidade": v}
            for k, v in sorted((resumo.get("por_categoria") or {}).items(),
                               key=lambda t: -t[1])])

st.markdown("---")

# ======================================================================================
# 3. Plano de correcao
# ======================================================================================

passo(3, "Plano de correcao priorizado")

filtro_sev = st.multiselect(
    "Filtrar por severidade", list(a6.SEVERIDADES),
    default=[s for s in a6.SEVERIDADES if s != "info"],
)
filtro_ag = st.multiselect("Filtrar por agente",
                           sorted(resumo.get("por_agente") or {}), default=None)
filtro_txt = st.text_input("Filtrar por texto (titulo, detalhe ou categoria)", "")

filtrados = []
for a in achados:
    if filtro_sev and a["severidade"] not in filtro_sev:
        continue
    if filtro_ag and str(a.get("agente")) not in [str(x) for x in filtro_ag]:
        continue
    if filtro_txt and filtro_txt.lower() not in json.dumps(
            a, ensure_ascii=False, default=str).lower():
        continue
    filtrados.append(a)

st.caption(f"Exibindo {len(filtrados)} de {len(achados)} achado(s).")

COR = {"critico": "bloqueio", "alto": "pendente", "medio": "info",
       "baixo": "off", "info": "off"}

for a in filtrados:
    with st.expander(
        f"{a['id']} · [{a['severidade'].upper()}] {a['titulo']}",
        expanded=(a["severidade"] == "critico"),
    ):
        rot_agente = f"Agente {a['agente']}" if a.get("agente") else "Ambiente"
        st.markdown(
            f'{chip(a["categoria_rotulo"], COR.get(a["severidade"], "info"))}'
            f'{chip(rot_agente, "off")}'
            f'<span class="out-fonte">origem: {a.get("origem")}</span>',
            unsafe_allow_html=True,
        )
        if a.get("detalhe"):
            st.markdown(f"**Detalhe:** {a['detalhe']}")
        if a.get("sugestao"):
            st.markdown(f"**Sugestao:** {a['sugestao']}")
        passos = a.get("correcao") or []
        if passos:
            st.markdown("**Passos de correcao:**")
            for i, p in enumerate(passos, 1):
                st.markdown(f"{i}. {p}")
        with st.popover("📋 Corpo de issue (Markdown)"):
            st.code(a6.corpo_issue(a), language="markdown")

st.markdown("---")

# ======================================================================================
# 4. Registro manual e relatorio
# ======================================================================================

passo(4, "Registro manual e exportacao")

with st.expander("➕ Registrar um defeito manualmente"):
    c = st.columns(2)
    t_titulo = st.text_input("Titulo")
    t_detalhe = st.text_area("Detalhe", height=100)
    c = st.columns(3)
    t_cat = c[0].selectbox("Categoria", list(a6.CATEGORIAS))
    t_sev = c[1].selectbox("Severidade", list(a6.SEVERIDADES))
    t_ag = c[2].selectbox("Agente responsavel",
                          ["(ambiente)"] + [str(n) for n in C.AGENTES])
    t_sugestao = st.text_input("Sugestao")
    if st.button("Registrar defeito", width="stretch"):
        if not t_titulo.strip():
            st.warning("Informe um titulo.")
        else:
            a6.registrar(
                proc, t_titulo.strip(), t_detalhe.strip(), categoria=t_cat,
                severidade=t_sev,
                agente=None if t_ag == "(ambiente)" else int(t_ag),
                sugestao=t_sugestao.strip())
            proc.salvar()
            st.success("Defeito registrado.")
            st.rerun()

rel = proc.get("relatorio_dev") or {}
caminho_md = rel.get("arquivo") or (
    f"out/defeitos_{proc.id}.md"
    if (C.SAIDA / f"defeitos_{proc.id}.md").exists() else None)

col_a, col_b = st.columns([1, 1])
with col_a:
    if st.button("🧾 (Re)gerar relatorio de defeitos", width="stretch"):
        saida = a6.executar(proc, salvar=True)
        proc.salvar()
        st.success(f"Relatorio gravado em out/defeitos_{proc.id}.md")
        st.rerun()
with col_b:
    download_arquivo(caminho_md, "⬇️ Descarregar relatorio (Markdown)",
                     f"defeitos_{proc.id}.md", "text/markdown")

fonte("Os artefatos do Agente 6 ficam em `out/`. A abertura de issues e o envio "
      "de commits sao decisoes do operador — o agente apenas prepara o corpo.")

st.markdown("")
if st.button("🏠 Voltar ao orquestrador", width="stretch"):
    st.switch_page("app.py")
