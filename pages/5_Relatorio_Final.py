# -*- coding: utf-8 -*-
"""Agente 5 - Emissao do Relatorio Tecnico Final e da Minuta SIOUT."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

import streamlit as st

from outorgasys import config as C
from outorgasys.agents import agente5_relatorio as a5
from outorgasys.report import laudo, pdf as pdf_mod
from outorgasys.ui import (
    aplicar_tema, barra_lateral, cabecalho, chip, download_arquivo, fonte,
    mostrar_imagem, mostrar_pendencias, passo, tabela,
)

aplicar_tema()
proc = barra_lateral()

cabecalho("Agente 5 · Relatorio Tecnico Final e Minuta SIOUT",
          "Laudo + Memorial Descritivo · parecer conclusivo · ART / CEGM-CREA-RS 08/2022")

# ======================================================================================
# 1. Responsavel tecnico
# ======================================================================================

passo(1, "Responsavel tecnico e ART")

rt = proc.get("responsavel_tecnico") or {}
c = st.columns(3)
rt["nome"] = c[0].text_input("Nome do responsavel tecnico", value=rt.get("nome", ""))
rt["titulo"] = c[1].selectbox(
    "Titulo profissional",
    ["Geologo", "Engenheiro de Minas", "Engenheiro Civil", "Engenheiro Ambiental",
     "Geografo", "Outro"],
    index=["Geologo", "Engenheiro de Minas", "Engenheiro Civil",
           "Engenheiro Ambiental", "Geografo", "Outro"].index(rt.get("titulo"))
    if rt.get("titulo") in ("Geologo", "Engenheiro de Minas", "Engenheiro Civil",
                            "Engenheiro Ambiental", "Geografo", "Outro") else 0)
rt["registro"] = c[2].text_input("Registro profissional", value=rt.get("registro", ""),
                                 placeholder="CREA-RS 0000000000")
cc = st.columns(3)
rt["empresa"] = cc[0].text_input("Empresa / consultoria", value=rt.get("empresa", ""))
rt["email"] = cc[1].text_input("E-mail", value=rt.get("email", ""))
rt["telefone"] = cc[2].text_input("Telefone", value=rt.get("telefone", ""))
art = st.text_input("Numero da ART / TRT (Anotacao de Responsabilidade Tecnica)",
                    value=proc.get("art") or "",
                    placeholder="ex.: ART RS2024 0000000")
proc["responsavel_tecnico"] = rt
proc["art"] = art

if not (rt.get("nome") and rt.get("registro")):
    st.caption(
        "Sem o nome e o registro do responsavel tecnico o laudo e emitido com o "
        "bloco de assinatura em branco, o que impede a protocolizacao."
    )

st.markdown("")

# ======================================================================================
# 2. Completude das secoes
# ======================================================================================

passo(2, "Completude das sete secoes obrigatorias")

SECOES = [
    ("1", "Identificacao e Localizacao", bool((proc.get("geoespacial") or {}).get("coordenadas"))),
    ("2", "Caracterizacao Construtiva e Geologica", bool(proc.get("construtivo"))),
    ("3", "Parametros Hidraulicos e Graficos",
     bool((proc.get("hidrogeologia") or {}).get("graficos"))),
    ("4", "Dados dos Equipamentos", bool(proc.get("hidrometro") and proc.get("motobomba"))),
    ("5", "Memorial do Sistema e Fluxograma", bool(proc.get("reservacao"))),
    ("6", "Quadro de Vazao da Intervencao (SIOUT)",
     bool((proc.get("balanco") or {}).get("quadro"))),
    ("7", "Parecer Conclusivo",
     bool((proc.get("padrao_explotacao") or {}).get("horas_dia"))),
]

colunas = st.columns(4)
for i, (num, nome, ok) in enumerate(SECOES):
    with colunas[i % 4]:
        st.markdown(
            f'<div class="out-panel" style="min-height:76px">'
            f'<div class="out-step">SECAO {num}</div>'
            f'<div style="font-size:0.82rem;font-weight:600">{nome}</div>'
            f'<div style="margin-top:4px">{chip("completa" if ok else "incompleta", "ok" if ok else "bloqueio")}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

faltantes = [n for n, _, ok in SECOES if not ok]
if faltantes:
    st.warning(
        "As secoes " + ", ".join(faltantes) +
        " serao emitidas com a declaracao expressa de dado nao informado, conforme "
        "exigencia de rastreabilidade do laudo."
    )

st.markdown("")

# ======================================================================================
# 3. Emissao
# ======================================================================================

passo(3, "Emissao dos documentos")
gerar_pdf = st.checkbox("Gerar tambem o PDF assinavel (reportlab)", value=True)

if st.button("📄 Emitir laudo tecnico, memorial e minuta SIOUT", type="primary",
             width="stretch"):
    with st.spinner("A montar o laudo, a gerar o PDF e a minuta..."):
        try:
            saida = a5.gerar(proc, resp_tecnico=rt, art=art or None,
                             gerar_pdf=gerar_pdf)
            proc.salvar()
            if saida.get("ok"):
                st.success("Documentos emitidos.")
            else:
                st.error("Emissao concluida com erros.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Falha no Agente 5: {type(exc).__name__}: {exc}")
            with st.expander("Detalhes tecnicos"):
                st.code(traceback.format_exc())
            proc.log(5, f"Falha: {type(exc).__name__}: {exc}", nivel="erro")

rel = proc.get("relatorio") or {}

if not rel:
    st.info("Emita os documentos para prever e descarregar os arquivos.")
    st.stop()

if rel.get("erros"):
    with st.expander("Erros da emissao", expanded=True):
        for e in rel["erros"]:
            st.error(str(e))

st.markdown("---")

# ======================================================================================
# 4. Descargas
# ======================================================================================

passo(4, "Arquivos gerados")
c = st.columns(3)
with c[0]:
    download_arquivo(rel.get("pdf"), "⬇️ Laudo Tecnico (PDF)",
                     f"laudo_tecnico_{proc.id}.pdf", "application/pdf")
with c[1]:
    download_arquivo(rel.get("markdown"), "⬇️ Laudo + Memorial (Markdown)",
                     f"laudo_tecnico_{proc.id}.md", "text/markdown")
with c[2]:
    download_arquivo(rel.get("minuta"), "⬇️ Minuta SIOUT (Markdown)",
                     f"minuta_siout_{proc.id}.md", "text/markdown")

st.markdown("---")

# ======================================================================================
# 5. Pre-visualizacao
# ======================================================================================

passo(5, "Pre-visualizacao e conferencia")

aba_laudo, aba_minuta, aba_anexos = st.tabs(
    ["Laudo (Markdown)", "Minuta SIOUT", "Anexos graficos"])

with aba_laudo:
    caminho = rel.get("markdown")
    if caminho:
        p = Path(caminho)
        if not p.is_absolute():
            p = C.ROOT / p
        texto = p.read_text(encoding="utf-8")
        st.markdown(texto)
    else:
        st.info("Markdown nao gerado.")

with aba_minuta:
    caminho = rel.get("minuta")
    if caminho:
        p = Path(caminho)
        if not p.is_absolute():
            p = C.ROOT / p
        st.markdown(p.read_text(encoding="utf-8"))
    else:
        st.info("Minuta nao gerada.")

with aba_anexos:
    g = (proc.get("hidrogeologia") or {}).get("graficos") or {}
    mapas = (proc.get("geoespacial") or {}).get("caminho_mapas") or []
    if g:
        st.markdown("**Graficos do ensaio (Agente 3)**")
        cols = st.columns(2)
        with cols[0]:
            mostrar_imagem(g.get("rebaixamento"), "Rebaixamento x Tempo")
        with cols[1]:
            mostrar_imagem(g.get("recuperacao"), "Recuperacao s' x log t/t'")
    if mapas:
        st.markdown("**Pranchas cartograficas (Agente 2)**")
        cols = st.columns(3)
        for i, m in enumerate(mapas):
            with cols[i % 3]:
                mostrar_imagem(m)
    if not g and not mapas:
        st.info("Nenhum anexo grafico disponivel.")

st.markdown("")
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("💾 Guardar", width="stretch"):
        proc.salvar()
        st.success("Guardado.")
with col2:
    if st.button("➡️ Avancar para o Agente 6", type="primary", width="stretch"):
        proc.salvar()
        st.switch_page("pages/6_Agente_Dev.py")

st.markdown("---")
st.markdown("**Parecer conclusivo**")
parecer = (rel.get("estrutura") or {}).get("parecer") or {}
if parecer:
    st.markdown(
        f'<div class="out-panel">'
        f'{chip(parecer.get("parecer") or "-", "ok" if (parecer.get("favoravel")) else "bloqueio")}'
        f'<br/><br/>{parecer.get("texto") or ""}</div>',
        unsafe_allow_html=True,
    )
    if parecer.get("exigencias"):
        st.markdown("**Exigencias:**")
        for e in parecer["exigencias"]:
            st.markdown(f"- {e}")
    if parecer.get("ressalvas"):
        st.markdown("**Ressalvas:**")
        for r in parecer["ressalvas"]:
            st.markdown(f"- {r}")

fonte("O laudo e emitido em formato editavel (Markdown) e em PDF, para assinatura "
      "do Geologo ou Engenheiro de Minas com registro no CEGM/CREA-RS, conforme a "
      "norma CEGM/CREA-RS n. 08/2022.")
