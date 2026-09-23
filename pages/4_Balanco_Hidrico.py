# -*- coding: utf-8 -*-
"""Agente 4 - Balanco Hidrico, Restricoes e Engenharia de Equipamentos (SIOUT RS)."""

from __future__ import annotations

import datetime
import json
import traceback

import streamlit as st

from outorgasys import config as C
from outorgasys.agents import agente4_balanco as a4
from outorgasys.ui import (
    aplicar_tema, barra_lateral, cabecalho, chip, fonte, mostrar_pendencias,
    passo, tabela,
)

aplicar_tema()
proc = barra_lateral()

cabecalho("Agente 4 · Balanco Hidrico, Restricoes e Engenharia de Equipamentos",
          "Quadro de Vazao da Intervencao SIOUT RS · bomba, hidrometro e reservacao")

# ======================================================================================
# 1. Premissas do balanco
# ======================================================================================

passo(1, "Premissas do balanco hidrico")

hidro = proc.get("hidrogeologia") or {}
p = hidro.get("parametros") or {}
if not p:
    st.warning(
        "Nenhum resultado hidrogeologico disponivel. Execute o Agente 3 antes: "
        "o balanco depende de Q_estavel e Q_ot."
    )

c = st.columns(4)
c[0].metric("Q_estavel (m3/h)", f"{p['q_estavel_m3h']:.3f}"
            if p.get("q_estavel_m3h") else "-")
c[1].metric("Q_ot (m3/h)", f"{p['Q_ot_m3h']:.3f}" if p.get("Q_ot_m3h") else "-")
c[2].metric("ND (m)", f"{p['nd_m']:.2f}" if p.get("nd_m") is not None else "-")
c[3].metric("T (m2/h)", f"{p['T_m2h']:.3f}" if p.get("T_m2h") else "-")

pe = proc.get("padrao_explotacao") or {}
col1, col2, col3 = st.columns(3)
ano = col1.number_input("Ano de referencia", min_value=2000, max_value=2100,
                        value=datetime.date.today().year, step=1)
horas = col2.number_input(
    "Horas de bombeamento por dia", min_value=0.0, max_value=24.0, step=0.5,
    value=float(pe.get("horas_dia") or 0.0),
    help=f"Limite SIOUT RS: {C.BOMBEAMENTO_MAX_H_DIA:g} h/dia "
         f"(repouso minimo de {C.REPOUSO_MINIMO_H:g} h).")
dias_sem = col3.number_input(
    "Dias de operacao por semana", min_value=0, max_value=7, step=1,
    value=int(pe.get("dias_semana") or 0))

preferencia = st.radio(
    "Criterio de adocao da vazao",
    ["auto", "q_estavel", "q_ot"],
    format_func=lambda v: {
        "auto": "Automatico (menor valor entre Q_ot e Q_estavel — recomendado)",
        "q_estavel": "Adotar Q_estavel (decisao expressa do responsavel tecnico)",
        "q_ot": "Adotar Q_ot (decisao expressa do responsavel tecnico)",
    }[v],
    horizontal=False,
)

if st.button("🧮 Calcular balanco hidrico e auditar equipamentos", type="primary",
             width="stretch"):
    proc.data.setdefault("padrao_explotacao", {}).update({
        "horas_dia": horas, "dias_semana": dias_sem})
    with st.spinner("A montar o quadro de vazoes e a auditar os equipamentos..."):
        try:
            saida = a4.executar(proc, ano=int(ano), preferencia_vazao=preferencia)
            proc["balanco"] = saida
            if saida.get("ok"):
                proc.concluir_agente(4)
                proc.log(4, "Balanco hidrico e auditoria de equipamentos concluidos.")
            proc.salvar()
            st.success("Balanco concluido." if saida.get("ok")
                       else "Balanco concluido com pendencias.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Falha no Agente 4: {type(exc).__name__}: {exc}")
            with st.expander("Detalhes tecnicos"):
                st.code(traceback.format_exc())
            proc.log(4, f"Falha: {type(exc).__name__}: {exc}", nivel="erro")

bal = proc.get("balanco") or {}

if not bal:
    st.info("Calcule o balanco para ver o quadro de vazoes e as auditorias.")
    st.stop()

if bal.get("erros"):
    with st.expander("Erros", expanded=True):
        for e in bal["erros"]:
            st.error(str(e))
for a in (bal.get("avisos") or []):
    st.warning(a)

st.markdown("---")

# ======================================================================================
# 2. Vazao adotada
# ======================================================================================

passo(2, "Vazao adotada")
esc = bal.get("vazao_adotada") or {}
c = st.columns(3)
c[0].metric("Vazao adotada (m3/h)", f"{esc['vazao']:.3f}" if esc.get("vazao") else "-")
c[1].metric("Origem", esc.get("origem") or "-")
c[2].metric("Repouso diario (h)", f"{bal.get('repouso_diario_h'):g}"
            if bal.get("repouso_diario_h") is not None else "-")
if esc.get("justificativa"):
    st.markdown(f'<div class="out-panel">{esc["justificativa"]}</div>',
                unsafe_allow_html=True)
if bal.get("repouso_atende"):
    st.success(f"Repouso diario de {bal.get('repouso_diario_h'):g} h atende ao "
               f"minimo de {C.REPOUSO_MINIMO_H:g} h.")

st.markdown("---")

# ======================================================================================
# 3. Quadro de Vazao da Intervencao
# ======================================================================================

passo(3, "Quadro de Vazao da Intervencao (SIOUT RS)")
quadro = bal.get("quadro") or {}
if quadro:
    c = st.columns(4)
    c[0].metric("Vazao diaria maxima (m3/dia)",
                f"{quadro.get('vazao_diaria_max_m3_dia'):.3f}")
    c[1].metric("Vazao media diaria (m3/dia)",
                f"{quadro.get('vazao_media_diaria_m3_dia'):.3f}")
    c[2].metric("Volume anual (m3)", f"{quadro.get('volume_anual_m3'):,.2f}"
                .replace(",", "X").replace(".", ",").replace("X", "."))
    c[3].metric("Ano de referencia", quadro.get("ano_referencia"))

    linhas = quadro.get("linhas") or []
    tabela([{"Mes": l["mes"], "Dias/Mes": l["dias_mes"],
             "Dias de operacao": l["dias_operacao"],
             "Horas/Dia": l["horas_dia"], "Vazao (m3/h)": l["vazao_m3h"],
             "Volume (m3/mes)": l["volume_m3_mes"]} for l in linhas], altura=430)

    try:
        import pandas as pd

        st.download_button(
            "⬇️ Descarregar Quadro de Vazao (.csv)",
            data=pd.DataFrame(linhas).to_csv(index=False, sep=";", decimal=",")
            .encode("utf-8-sig"),
            file_name=f"quadro_vazao_{proc.id}.csv", mime="text/csv",
            width="stretch",
        )
    except Exception:  # noqa: BLE001
        pass
    fonte("Dias de operacao por mes = dias do mes x (dias por semana / 7). "
          "Volume mensal = dias de operacao x horas/dia x vazao adotada.")

st.markdown("---")

# ======================================================================================
# 4. Auditoria dos equipamentos
# ======================================================================================

passo(4, "Auditoria de equipamentos")
eq = bal.get("equipamentos") or {}
if eq:
    aba1, aba2, aba3 = st.tabs(["Motobomba", "Hidrometro", "Reservacao"])

    with aba1:
        b = eq.get("motobomba") or {}
        faixa = b.get("faixa_vazao_recomendada_m3h") or [None, None]
        subm = b.get("submergencia_m")
        c = st.columns(4)
        c[0].metric("Vazao nominal declarada (m3/h)",
                    f"{b['vazao_nominal_m3h']:.2f}"
                    if b.get("vazao_nominal_m3h") else "-")
        c[1].metric("Faixa recomendada (m3/h)",
                    f"{faixa[0]:.2f} – {faixa[1]:.2f}"
                    if faixa[0] is not None else "-")
        c[2].metric("Submergencia (m)", f"{subm:.2f}" if subm is not None else "-")
        c[3].metric("Submergencia recomendada (m)",
                    f"{C.SUBMERGENCIA_MIN_M:g} – {C.SUBMERGENCIA_MAX_M:g}")
        if subm is not None:
            if subm < C.SUBMERGENCIA_MIN_M:
                st.error(
                    f"Submergencia de {subm:.2f} m abaixo do minimo de "
                    f"{C.SUBMERGENCIA_MIN_M:g} m: risco de cavitação e de "
                    "entrada de ar no rotor."
                )
            elif subm > C.SUBMERGENCIA_MAX_M:
                st.warning(
                    f"Submergencia de {subm:.2f} m acima do maximo recomendado "
                    f"de {C.SUBMERGENCIA_MAX_M:g} m."
                )
            else:
                st.success("Submergencia dentro da faixa recomendada.")
        fonte("A bomba deve operar na faixa de 0,8 a 1,1 vezes a vazao otima do "
              "poco, com o rotor instalado entre 6 e 10 m abaixo do nivel "
              "dinamico para evitar cavitação.")

    with aba2:
        h = eq.get("hidrometro") or {}
        c = st.columns(4)
        c[0].metric("Vazao nominal (m3/h)", f"{h['vazao_nominal_m3h']:.2f}"
                    if h.get("vazao_nominal_m3h") else "-")
        c[1].metric("Diametro nominal DN (mm)", f"{h['diametro_nominal_mm']:.0f}"
                    if h.get("diametro_nominal_mm") else "-")
        c[2].metric("Velocidade media (m/s)", f"{h['velocidade_media_m_s']:.3f}"
                    if h.get("velocidade_media_m_s") else "-")
        c[3].metric("Vazao adotada (m3/h)", f"{esc.get('vazao'):.3f}"
                    if esc.get("vazao") else "-")
        fonte("O hidrometro deve ter vazao nominal compativel com a vazao de "
              "explotacao e classe metrologica adequada ao diametro nominal, de "
              "modo a operar dentro da faixa de medicao com erro admissivel.")

    with aba3:
        r = eq.get("reservacao") or {}
        c = st.columns(3)
        c[0].metric("Capacidade total instalada (L)",
                    f"{r.get('capacidade_total_l', 0):,.0f}"
                    .replace(",", "X").replace(".", ",").replace("X", "."))
        c[1].metric("Capacidade total (m3)", f"{r.get('capacidade_total_m3', 0):.3f}")
        c[2].metric("Volume por ciclo (m3)",
                    f"{(esc.get('vazao') or 0) * (horas or 0) / max(1, (dias_sem or 1)):.3f}"
                    if esc.get("vazao") else "-")
        if r.get("itens"):
            tabela([{"Reservatorio": i + 1, "Capacidade (L)": x.get("capacidade_l"),
                     "Local": x.get("local")} for i, x in enumerate(r["itens"])])
        fonte("A capacidade de reservacao deve ser superior ao volume bombeado "
              "por ciclo, para evitar o short-cycling (acionamentos curtos e "
              "repetidos) que reduz a vida util do conjunto.")
else:
    st.info("Auditoria de equipamentos indisponivel.")

# ======================================================================================
# 5. Pendencias
# ======================================================================================

st.markdown("---")
mostrar_pendencias(bal.get("pendencias", []), "Pendencias do balanco hidrico")
if eq:
    mostrar_pendencias(eq.get("pendencias", []), "Pendencias de equipamentos")

st.markdown("")
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("💾 Guardar", width="stretch"):
        proc.salvar()
        st.success("Guardado.")
with col2:
    if st.button("➡️ Avancar para o Agente 5", type="primary", width="stretch"):
        proc.salvar()
        st.switch_page("pages/5_Relatorio_Final.py")

with st.expander("Objeto JSON de saida do Agente 4"):
    st.code(json.dumps({"vazao_adotada": esc,
                        "repouso_diario_h": bal.get("repouso_diario_h"),
                        "volume_anual_m3": (quadro or {}).get("volume_anual_m3")},
                       ensure_ascii=False, indent=2, default=str), language="json")
