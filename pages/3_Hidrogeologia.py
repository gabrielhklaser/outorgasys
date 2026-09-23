# -*- coding: utf-8 -*-
"""Agente 3 - Processamento Hidrogeologico: Theis / Cooper-Jacob / Jacob-Lohman."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

from outorgasys import config as C
from outorgasys.agents import agente1_triagem as a1
from outorgasys.agents import agente3_hidro as a3
from outorgasys.hydro import planilha, sintetico
from outorgasys.ui import (
    aplicar_tema, barra_lateral, cabecalho, download_arquivo, fonte,
    mostrar_imagem, passo, tabela,
)

aplicar_tema()
proc = barra_lateral()

cabecalho("Agente 3 · Processamento Hidrogeologico e Graficos de Alta Resolucao",
          "Theis / Cooper-Jacob / Jacob-Lohman · rebaixamento e recuperacao")

# ======================================================================================
# 0. Modelo de planilha
# ======================================================================================

with st.expander("⬇️ Modelo de planilha de ensaio de bombeamento (.xlsx)", expanded=False):
    st.caption(
        "Estrutura em etapa unica: aba de cadastro (NE, ND, crivos, identificacao), "
        "aba de bombeamento (t, ND, s = ND − NE, Q) e aba de recuperacao "
        "(t′, NA, s′ = NA − NE)."
    )
    st.download_button(
        "Descarregar modelo (.xlsx)",
        data=planilha.gerar_modelo({
            "municipio": (proc.get("imovel") or {}).get("municipio", ""),
            "nome_poco": (proc.get("poco") or {}).get("nome", ""),
            "profundidade_total_m": (proc.get("poco") or {}).get("profundidade_total_m", ""),
            "nivel_estatico_m": (proc.get("poco") or {}).get("nivel_estatico_m", ""),
            "diametro_util_pol": (proc.get("poco") or {}).get("diametro_util_pol", ""),
        }),
        file_name=a1.nome_modelo_planilha(proc.id),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

# ======================================================================================
# 1. Fonte dos dados do ensaio
# ======================================================================================

passo(1, "Leitura do ensaio de bombeamento e de recuperacao")

docs = proc.get("documentos") or {}
salvo_ensaio = ((docs.get("ensaio_bombeamento") or {}) or {}).get("caminho")
ja_processado = bool((proc.get("ensaio") or {}).get("bombeamento") is not None
                     or (proc.get("hidrogeologia") or {}).get("ok"))

opcoes = ["Arquivo enviado no Agente 1", "Enviar um arquivo agora",
          "Gerar conjunto sintetico de exemplo"]
indice = 0 if salvo_ensaio else (2 if not ja_processado else 1)
fonte_dados = st.radio("Origem dos dados do ensaio", opcoes, index=indice,
                       horizontal=True)

arquivo: Path | None = None

if fonte_dados == opcoes[0]:
    if not salvo_ensaio:
        st.warning("Nenhum arquivo de ensaio foi enviado no Agente 1.")
    else:
        arquivo = C.caminho_absoluto(salvo_ensaio)
        st.success(f"Arquivo do processo: {docs['ensaio_bombeamento'].get('nome')}")

elif fonte_dados == opcoes[1]:
    up = st.file_uploader("Planilha de ensaio (.xlsx/.xls/.csv)",
                          type=["xlsx", "xls", "csv"], key="up_ensaio_a3")
    if up is not None:
        dest = proc.dir_arquivos / up.name
        dest.write_bytes(up.getbuffer())
        a1.registrar_upload(proc, "ensaio_bombeamento", up)
        arquivo = dest
        st.success(f"Recebido: {up.name}")

else:
    st.caption(
        "Gera um ensaio sintetico pela solucao direta de Cooper-Jacob e "
        "Theis/Jacob-Lohman, de modo que o processamento deve recuperar a "
        "transmissividade informada. Serve para validar a plataforma ponta a ponta."
    )
    c = st.columns(4)
    q_in = c[0].number_input("Vazao de bombeamento Q (m3/h)", min_value=0.5,
                             value=12.0, step=0.5)
    ne_in = c[1].number_input("Nivel estatico NE (m)", min_value=0.0, value=8.0,
                              step=0.5)
    t_in = c[2].number_input("Transmissividade T (m2/h)", min_value=0.01,
                             value=6.0, step=0.5)
    s_in = c[3].number_input("Armazenamento S (-)", min_value=1e-7, value=1.0e-3,
                             step=1e-4, format="%.2e")
    c = st.columns(2)
    raio_in = c[0].number_input("Raio do poco (m)", min_value=0.01, value=0.0762,
                                step=0.01, format="%.4f")
    dur_in = c[1].number_input("Duracao do ensaio (h)", min_value=1.0, value=24.0,
                               step=1.0)
    if st.button("🧪 Gerar e anexar ensaio sintetico", width="stretch"):
        ens = sintetico.gerar(q=q_in, T=t_in, S=s_in, raio=raio_in, ne=ne_in,
                              duracao_h=dur_in)
        dest = proc.dir_arquivos / f"ensaio_sintetico_{proc.id}.xlsx"
        sintetico.salvar_xlsx(ens, dest)
        proc.data.setdefault("poco", {})["raio_m"] = raio_in
        a1.registrar_upload_manual(
            proc, "ensaio_bombeamento", dest, dest.name,
            {"sintetico": True, "parametros_geracao": ens["parametros_geracao"]})
        proc["ensaio"] = a3.processar_planilha(dest)
        proc.salvar()
        st.success("Ensaio sintetico gerado, anexado e lido.")
        st.rerun()
    arquivo = None

# Leitura efetiva
if arquivo is not None:
    try:
        proc["ensaio"] = a3.processar_planilha(arquivo)
        proc.salvar()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Falha ao interpretar o arquivo: {type(exc).__name__}: {exc}")
        with st.expander("Detalhes"):
            st.code(traceback.format_exc())

ensaio = proc.get("ensaio") or {}
bom = ensaio.get("bombeamento")
rec = ensaio.get("recuperacao")
tem_serie = bom is not None and len(bom) > 0

if not tem_serie:
    st.info(
        "Nenhum ensaio interpretado ainda. Envie um arquivo ou gere o conjunto "
        "sintetico de exemplo."
    )
    st.stop()

avisos = list(ensaio.get("avisos") or [])
erros = list(ensaio.get("erros") or [])
for a in avisos:
    st.warning(a)
for e in erros:
    st.error(e)

st.markdown("")

# ======================================================================================
# 2. Serie lida
# ======================================================================================

passo(2, "Serie do ensaio interpretada")
cad = ensaio.get("cadastro") or {}
c = st.columns(4)
c[0].metric("Leituras de bombeamento", len(bom))
c[1].metric("Leituras de recuperacao", len(rec) if rec is not None else 0)
c[2].metric("NE (m)", f"{float(cad['nivel_estatico_m']):.2f}"
            if cad.get("nivel_estatico_m") not in (None, "") else "-")
c[3].metric("Duracao (h)",
            f"{max(float(v) for v in bom['t_min'].dropna()) / 60:.1f}"
            if bom["t_min"].notna().any() else "-")

aba1, aba2 = st.tabs(["Bombeamento (t, ND, s, Q)", "Recuperacao (t', NA, s')"])
with aba1:
    tabela(bom.head(400).to_dict("records"), altura=280)
with aba2:
    if rec is not None and len(rec):
        tabela(rec.head(400).to_dict("records"), altura=280)
    else:
        st.info("Sem leituras de recuperacao interpretadas.")

st.markdown("---")

# ======================================================================================
# 3. Processamento
# ======================================================================================

passo(3, "Memoria de calculo")
col_manual, col_btn = st.columns([1, 1])
with col_manual:
    usar_q_manual = st.checkbox(
        "Informar a vazao estabilizada manualmente",
        value=bool((proc.get("hidrogeologia") or {}).get("q_manual_usada")),
        help="Use quando a coluna Q nao estiver preenchida na planilha.")
    q_manual = None
    if usar_q_manual:
        q_manual = st.number_input("Q_estavel (m3/h)", min_value=0.01, value=12.0,
                                   step=0.1)

with col_btn:
    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
    if st.button("⚙️ Processar ensaio (Theis / Cooper-Jacob / Jacob-Lohman)",
                 type="primary", width="stretch"):
        with st.spinner("A ajustar as retas e a calcular T, q(t) e Q_ot..."):
            try:
                saida = a3.calcular(proc, usar_q_manual=usar_q_manual,
                                    q_manual=q_manual, gerar_graficos=True)
                saida["q_manual_usada"] = bool(usar_q_manual and q_manual)
                proc["hidrogeologia"] = saida
                if saida.get("ok"):
                    proc.concluir_agente(3)
                    proc.log(3, "Ensaio processado e graficos gerados.")
                proc.salvar()
                st.success("Processamento concluido." if saida.get("ok")
                           else "Processamento concluido com ressalvas.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha no Agente 3: {type(exc).__name__}: {exc}")
                with st.expander("Detalhes tecnicos"):
                    st.code(traceback.format_exc())
                proc.log(3, f"Falha: {type(exc).__name__}: {exc}", nivel="erro")

hidro = proc.get("hidrogeologia") or {}
if not hidro:
    st.info("Processe o ensaio para ver os parametros e os graficos.")
    st.stop()

if hidro.get("erros"):
    with st.expander("Erros do processamento", expanded=True):
        for e in hidro["erros"]:
            st.error(str(e))
for a in (hidro.get("avisos") or []):
    st.warning(str(a))

p = hidro.get("parametros") or {}
m = hidro.get("memoria") or {}

c = st.columns(4)
c[0].metric("NE (m)", f"{p['ne_m']:.2f}" if p.get("ne_m") is not None else "-")
c[1].metric("ND final (m)", f"{p['nd_m']:.2f}" if p.get("nd_m") is not None else "-")
c[2].metric("s_max (m)", f"{p['s_max_m']:.3f}" if p.get("s_max_m") is not None else "-")
c[3].metric("Q_estavel (m3/h)",
            f"{p['q_estavel_m3h']:.3f}" if p.get("q_estavel_m3h") else "-")

c = st.columns(4)
c[0].metric("Δs' (m/ciclo)", f"{p['delta_s_linha_m']:.4f}"
            if p.get("delta_s_linha_m") else "-")
c[1].metric("T (m2/h)", f"{p['T_m2h']:.4f}" if p.get("T_m2h") else "-")
c[2].metric("T (m2/s)", f"{p['T_m2s']:.3e}" if p.get("T_m2s") else "-")
c[3].metric("q = Q/s (m3/h/m)", f"{p['q_capacidade_especifica_m3h_m']:.4f}"
            if p.get("q_capacidade_especifica_m3h_m") else "-")

c = st.columns(4)
c[0].metric("q(t) = 0,8·T (m3/h/m)", f"{p['q_longo_prazo_m3h_m']:.4f}"
            if p.get("q_longo_prazo_m3h_m") else "-")
c[1].metric("Q_ot (m3/h)", f"{p['Q_ot_m3h']:.3f}" if p.get("Q_ot_m3h") else "-")
c[2].metric("Contraprova Jacob-Lohman (m3/h)", f"{p['Q_jacob_lohman_m3h']:.3f}"
            if p.get("Q_jacob_lohman_m3h") else "-")
c[3].metric("Vazao adotada (m3/h)",
            f"{min(p['Q_ot_m3h'], p['q_estavel_m3h']):.3f}"
            if p.get("Q_ot_m3h") and p.get("q_estavel_m3h") else "-")

if p.get("T_m2h") and p.get("q_estavel_m3h") and p.get("delta_s_linha_m"):
    st.markdown(
        f'<div class="out-panel">'
        f'<b>T = 0,183 · Q_estavel / Δs\'</b> = 0,183 × '
        f'{p["q_estavel_m3h"]:.3f} / {p["delta_s_linha_m"]:.4f} = '
        f'<b>{p["T_m2h"]:.4f} m²/h</b> ({p.get("T_m2s", 0):.3e} m²/s).<br/>'
        f'<b>q(t) = 0,8 · T</b> = {p.get("q_longo_prazo_m3h_m", 0):.4f} m³/h/m'
        f' &nbsp;·&nbsp; <b>Q_ot = q(t) · s_max</b> = {p.get("Q_ot_m3h", 0):.3f} m³/h.'
        f'</div>',
        unsafe_allow_html=True,
    )
    fonte("A vazao de exploracao adotada e o minimo entre Q_ot e Q_estavel, o que "
          "garante que o poco nunca opere acima da vazao efetivamente testada.")

st.markdown("**Tabela de parametros hidraulicos e resultados do ensaio**")
tabela(a3.tabela_memoria(hidro))

reta = m.get("reta_recuperacao") or {}
if reta:
    with st.expander("Ajuste da reta de recuperacao (Jacob-Lohman)"):
        tabela([{"Propriedade": k, "Valor": v} for k, v in reta.items()])
est = m.get("vazao_estabilizada") or {}
if est:
    with st.expander("Identificacao da vazao estabilizada"):
        tabela([{"Propriedade": k, "Valor": v} for k, v in est.items()])

st.markdown("---")

# ======================================================================================
# 4. Graficos
# ======================================================================================

passo(4, "Graficos de alta resolucao")
g = hidro.get("graficos") or {}
aba1, aba2, aba3 = st.tabs([
    "Grafico 1 · Rebaixamento x Tempo (semilog)",
    "Grafico 2 · Recuperacao (s' x log10 t/t')",
    "Painel consolidado",
])
with aba1:
    st.caption(
        "Eixo horizontal em escala semilogaritmica. Eixo vertical esquerdo: "
        "profundidade absoluta em metros, invertido de 0 a 150 m, com NE e ND "
        "marcados. Eixo vertical direito: rebaixamento s em metros, com a linha "
        "de tendencia da fase de bombeamento."
    )
    if g.get("rebaixamento"):
        mostrar_imagem(g["rebaixamento"], "Curva de Rebaixamento x Tempo")
        download_arquivo(g["rebaixamento"], "⬇️ Descarregar grafico (PNG)")
    else:
        st.warning("Grafico de rebaixamento nao gerado.")
with aba2:
    st.caption(
        "Rebaixamento residual s' contra log10(t/t'), com t = t_total + t' e t' "
        "o tempo decorrido desde o desligamento. A equacao da reta e o valor de "
        "Δs' por ciclo logaritmico sao exibidos no proprio grafico."
    )
    if g.get("recuperacao"):
        mostrar_imagem(g["recuperacao"], "Recuperacao dos Niveis")
        download_arquivo(g["recuperacao"], "⬇️ Descarregar grafico (PNG)")
    else:
        st.warning("Grafico de recuperacao nao gerado.")
with aba3:
    if g.get("painel"):
        mostrar_imagem(g["painel"], "Painel consolidado dos dois graficos")
        download_arquivo(g["painel"], "⬇️ Descarregar painel (PNG)")
    else:
        st.info("Painel nao gerado.")

st.markdown("")
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("💾 Guardar", width="stretch"):
        proc.salvar()
        st.success("Guardado.")
with col2:
    if st.button("➡️ Avancar para o Agente 4", type="primary", width="stretch"):
        proc.salvar()
        st.switch_page("pages/4_Balanco_Hidrico.py")

with st.expander("Objeto JSON de saida do Agente 3"):
    st.code(json.dumps({"parametros": p, "graficos": g,
                        "avisos": hidro.get("avisos")},
                       ensure_ascii=False, indent=2, default=str), language="json")
