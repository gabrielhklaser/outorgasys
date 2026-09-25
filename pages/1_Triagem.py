# -*- coding: utf-8 -*-
"""Agente 1 - Triagem, Cadastro e Validacao Documental (SIOUT RS)."""

from __future__ import annotations

import streamlit as st

from outorgasys import config as C
from outorgasys.agents import agente1_triagem as a1
from outorgasys.hydro import planilha
from outorgasys.state import Processo
from outorgasys.ui import (
    aplicar_tema, barra_lateral, bloco_status, cabecalho, chip, chips,
    download_arquivo, fonte, mostrar_pendencias, passo, tabela,
)

aplicar_tema()
proc = barra_lateral()

cabecalho("Agente 1 · Triagem, Cadastro e Validacao Documental",
          "SIOUT RS · ABNT NBR 12212:2017 e NBR 12244:2006 · Portaria GM/MS n. 888/2021")

# ======================================================================================
# 1. Triagem inicial de enquadramento
# ======================================================================================

passo(1, "Triagem inicial de enquadramento")
st.markdown(
    "A primeira decisao do SIOUT RS e binaria e depende do **diametro util** do poco."
)

opcoes = {
    f'Opcao A — Poco com diametro util inferior a 4" (< 4")': "A",
    f'Opcao B — Poco tubular profundo com diametro util igual ou superior a 4" (>= 4")': "B",
}

enquadramento = proc.get("enquadramento") or {}
indice_atual = 0
if enquadramento.get("classe") == "poco_tubular_profundo":
    indice_atual = 1

escolha = st.radio(
    "Selecione o enquadramento do poco:",
    list(opcoes.keys()),
    index=indice_atual,
    horizontal=False,
)

diametro = st.number_input(
    'Diametro util do poco (polegadas)',
    min_value=0.5, max_value=48.0, step=0.25,
    value=float((proc.get("poco") or {}).get("diametro_util_pol") or
                (6.0 if indice_atual == 1 else 3.0)),
    help='Valor efetivamente usado no calculo do enquadramento (corte em 4").',
)

enf = a1.enquadrar(diametro)
# Respeita a opcao escolhida explicitamente, mas alerta divergencias.
escolhida = opcoes[escolha]
if escolhida == "A" and diametro >= C.DIAMETRO_CORTE_POL:
    st.warning(
        f'Foi selecionada a Opcao A, porem o diametro informado ({diametro:g}") e '
        f'superior ou igual a {C.DIAMETRO_CORTE_POL:g}". O enquadramento tecnico '
        "aplicado sera a Opcao B."
    )
elif escolhida == "B" and diametro < C.DIAMETRO_CORTE_POL:
    st.warning(
        f'Foi selecionada a Opcao B, porem o diametro informado ({diametro:g}") e '
        f'inferior a {C.DIAMETRO_CORTE_POL:g}". O enquadramento tecnico aplicado '
        "sera a Opcao A."
    )

if enf["definido"]:
    cor = "bloqueio" if enf["exige_ensaio_24h"] else "ok"
    st.markdown(
        f'<div class="out-panel">{chip(enf["rotulo"], cor)}<br/><br/>'
        f'{enf["descricao"]}</div>',
        unsafe_allow_html=True,
    )

proc["enquadramento"] = enf
proc.data.setdefault("poco", {})["diametro_util_pol"] = diametro

st.markdown("")

# ======================================================================================
# 2. Modelo de planilha + uploads
# ======================================================================================

passo(2, "Modelo de ensaio e envio de documentos")
st.markdown(
    "Descarregue o modelo, preencha em campo e envie os ficheiros obrigatorios."
)

col_a, col_b = st.columns([1, 1.6])

with col_a:
    st.markdown("**Modelo de planilha de ensaio de bombeamento**")
    st.caption(
        "Estrutura classica de monitoramento de rebaixamento e recuperacao em "
        "etapa unica: aba de cadastro, aba de bombeamento (t, ND, s, Q) e aba de "
        'recuperacao (t\', NA, s\').'
    )
    nome_modelo = a1.nome_modelo_planilha(proc.id)
    st.download_button(
        "⬇️ Descarregar Modelo de Planilha de Ensaio de Bombeamento (.xlsx)",
        data=a1.modelo_planilha({
            "municipio": (proc.get("imovel") or {}).get("municipio", ""),
            "diametro_util_pol": diametro,
        }),
        file_name=nome_modelo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

with col_b:
    docs = proc.get("documentos") or {}
    if enf.get("exige_ensaio_24h"):
        up = st.file_uploader(
            "1. Ensaio de Bombeamento (.xlsx/.xls/.csv)",
            type=["xlsx", "xls", "csv"],
            key="up_ensaio",
            help="Obrigatorio para pocos com diametro util >= 4\": ensaio continuo "
                 "de 24 h acompanhado do ensaio de recuperacao.",
        )
        if up is not None:
            a1.registrar_upload(proc, "ensaio_bombeamento", up)
            st.success(f"Recebido: {up.name}")
    else:
        st.info(
            "Ensaio de bombeamento de 24 h **dispensado**: poco de pequeno "
            "diametro (< 4\")."
        )
        up = st.file_uploader(
            "1. Ensaio de Bombeamento (opcional)",
            type=["xlsx", "xls", "csv"], key="up_ensaio_opc",
        )
        if up is not None:
            a1.registrar_upload(proc, "ensaio_bombeamento", up)
            st.success(f"Recebido: {up.name}")

st.markdown("")

up_posse = st.file_uploader(
    "2. Documentacao de Posse e Terra (PDF ou imagem PNG/JPG/TIFF)",
    type=["pdf", "png", "jpg", "jpeg", "tif", "tiff"],
    key="up_posse",
    help="Certidao de registro de imoveis / matricula atualizada, contrato de "
         "arrendamento/locacao/comodato, termo de concessao ou recibo do CAR "
         "(se rural).",
)
if up_posse is not None:
    a1.registrar_upload(proc, "matricula_imovel", up_posse)
    st.success(f"Recebido: {up_posse.name}")

up_lab = st.file_uploader(
    "3. Relatorio de Analise Laboratorial — Fisico-Quimica e Bacteriologica (PDF)",
    type=["pdf"], key="up_lab",
    help="Conforme os parametros de potabilidade da Portaria GM/MS n. 888/2021.",
)
if up_lab is not None:
    a1.registrar_upload(proc, "analise_laboratorial", up_lab)
    st.success(f"Recebido: {up_lab.name}")

up_fotos = st.file_uploader(
    "4. Registro Fotografico do Poco (4 fotos)",
    type=["png", "jpg", "jpeg", "tif", "tiff"],
    accept_multiple_files=True, key="up_fotos",
    help="Boca do poco, laje de protecao sanitaria, cercamento de protecao e "
         "cavalete com hidrometro instalado.",
)
if up_fotos:
    for f in up_fotos:
        a1.registrar_upload(proc, "registro_fotografico", f)
    st.success(f"{len(up_fotos)} foto(s) recebida(s).")

enviados = a1.arquivos_enviados(proc)
if enviados["registro_fotografico"] or enviados["posse"]:
    with st.expander("Ficheiros ja enviados"):
        tabela([{"tipo": k, "nome": (v or {}).get("nome") if isinstance(v, dict) else
                 ", ".join(str(x.get("nome")) for x in (v or []))}
                for k, v in enviados.items() if v])

st.markdown("")

# ======================================================================================
# 2b. Triagem e Leitura Inteligente (Docling + GabeBrain)
# ======================================================================================

st.markdown("### 🧠 Triagem Documental Inteligente (Docling + GabeBrain)")
st.caption(
    "Motor treinado segundo a metodologia do GabeBrain (skill `biblioteca-triagem`: 'uma leitura, quatro saidas'). "
    "Extrai tabelas de parametros fisico-quimicos e microbiologicos (Portaria GM/MS n. 888/2021), confere limites "
    "legais, extrai dados notariais de matricula e gera notas destiladas com citacao exata de pagina."
)

col_t1, col_t2 = st.columns([1.2, 1])
with col_t1:
    if st.button("⚡ Executar Leitura Estruturada (Docling + GabeBrain)", type="primary", width="stretch"):
        with st.spinner("A processar documentos com o motor IBM Docling e agentes GabeBrain..."):
            res_triagem = a1.triar_documentos_com_docling(proc)
            if res_triagem:
                st.success(f"{len(res_triagem)} documento(s) lido(s) e destilado(s) com sucesso!")
                st.rerun()
            else:
                st.warning("Nenhum documento PDF disponivel para processar.")

qualidade_dados = proc.get("analise_laboratorial_dados")
destilacoes = proc.get("destilacao_documental")

if qualidade_dados or destilacoes:
    if qualidade_dados and qualidade_dados.get("parametros"):
        st.markdown("#### 💧 Parametros de Potabilidade Extraidos (Portaria GM/MS n. 888/2021)")
        linhas_tab = []
        for p in qualidade_dados["parametros"]:
            status_chip = "ok" if p["status"] == "conforme" else "bloqueio"
            linhas_tab.append({
                "Parametro": p["parametro"],
                "Resultado Obtido": p["resultado"],
                "VMP (Portaria 888/2021)": f"{p['vmp']} {p.get('unidade', '')}".strip(),
                "Situacao": "CONFORME" if p["status"] == "conforme" else "INCONFORME",
                "Pagina": f"p. {p['pagina']}",
            })
        tabela(linhas_tab)

        if qualidade_dados.get("conforme_potabilidade"):
            st.success("✅ Todos os parametros laboratoriais estao em conformidade com o Padrao de Potabilidade.")
        else:
            st.error("⚠️ Foram identificadas inconformidades nos parametros laboratoriais segundo a Portaria 888/2021.")

    if destilacoes:
        with st.expander("📄 Notas Destiladas GabeBrain (Citacao exata de pagina e confianca da fonte)"):
            for doc_ch, d_info in destilacoes.items():
                st.markdown(f"**Documento: `{doc_ch}`** · Confianca da Fonte: `{d_info.get('confianca', 'A')}`")
                st.markdown(d_info.get("nota", ""))
                st.markdown("---")

st.markdown("---")

# ======================================================================================
# 3. Requerente e imovel
# ======================================================================================

passo(3, "Dados cadastrais")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Requerente**")
    req = proc.get("requerente") or {}
    req["nome"] = st.text_input("Nome / Razao social", value=req.get("nome", ""))
    c = st.columns(2)
    req["cpf_cnpj"] = c[0].text_input("CPF / CNPJ", value=req.get("cpf_cnpj", ""))
    req["rg_ie"] = c[1].text_input("RG / Inscricao estadual", value=req.get("rg_ie", ""))
    c = st.columns(2)
    req["telefone"] = c[0].text_input("Telefone", value=req.get("telefone", ""))
    req["email"] = c[1].text_input("E-mail", value=req.get("email", ""))
    proc["requerente"] = req

with col2:
    st.markdown("**Imovel**")
    imo = proc.get("imovel") or {}
    imo["denominacao"] = st.text_input("Denominacao do imovel",
                                       value=imo.get("denominacao", ""))
    imo["endereco"] = st.text_input("Endereco", value=imo.get("endereco", ""))
    c = st.columns(2)
    imo["bairro"] = c[0].text_input("Bairro / Localidade", value=imo.get("bairro", ""))
    imo["cep"] = c[1].text_input("CEP", value=imo.get("cep", ""))
    c = st.columns([2, 1])
    imo["municipio"] = c[0].text_input("Municipio", value=imo.get("municipio", ""))
    imo["uf"] = c[1].text_input("UF", value=imo.get("uf", "RS"))
    imo["area_ha"] = st.number_input("Area do terreno (ha)", min_value=0.0,
                                     value=float(imo.get("area_ha") or 0.0), step=0.1)
    proc["imovel"] = imo

st.markdown("")

# ======================================================================================
# 4. Poco, construtivo e laje
# ======================================================================================

passo(4, "Caracteristicas construtivas do poco")
poco = proc.get("poco") or {}
c = st.columns(3)
poco["nome"] = c[0].text_input("Identificacao do poco", value=poco.get("nome", ""))
poco["profundidade_total_m"] = c[1].number_input(
    "Profundidade total (m)", min_value=0.0, step=1.0,
    value=float(poco.get("profundidade_total_m") or 0.0))
poco["raio_m"] = c[2].number_input(
    "Raio do poco (m)", min_value=0.01, step=0.01,
    value=float(poco.get("raio_m") or 0.10))
proc["poco"] = poco

constr = proc.get("construtivo") or {}
c = st.columns(4)
constr["diametro_perfuracao_mm"] = c[0].number_input(
    "Diametro da perfuracao (mm)", min_value=0.0, step=10.0,
    value=float(constr.get("diametro_perfuracao_mm") or 0.0))
constr["diametro_revestimento_mm"] = c[1].number_input(
    "Diametro do revestimento (mm)", min_value=0.0, step=10.0,
    value=float(constr.get("diametro_revestimento_mm") or 0.0))
constr["profundidade_selo_m"] = c[2].number_input(
    "Profundidade do selo sanitario (m)", min_value=0.0, step=1.0,
    value=float(constr.get("profundidade_selo_m") or 0.0),
    help=f"Minimo recomendado: {C.SELO_SANITARIO_MIN_M:g} m.")
constr["tipo_aquifero"] = c[3].text_input(
    "Tipo de aquifer", value=constr.get("tipo_aquifero", ""),
    placeholder="ex.: poroso confinado")
c = st.columns(2)
constr["crivo_de_m"] = c[0].number_input("Crivo - de (m)", min_value=0.0, step=1.0,
                                         value=float(constr.get("crivo_de_m") or 0.0))
constr["crivo_ate_m"] = c[1].number_input("Crivo - ate (m)", min_value=0.0, step=1.0,
                                          value=float(constr.get("crivo_ate_m") or 0.0))
proc["construtivo"] = constr
fonte(f"Espaco anular minimo: {C.ESPACO_ANULAR_MIN_MM:g} mm entre a parede do furo e "
      f"a tubulacao de revestimento.")

st.markdown("**Laje de protecao sanitaria**")
laje = proc.get("laje") or {}
c = st.columns(3)
laje["espessura_cm"] = c[0].number_input(
    "Espessura (cm)", min_value=0.0, step=1.0,
    value=float(laje.get("espessura_cm") or 0.0),
    help=f"Minimo: {C.LAJE_ESPESSURA_MIN_CM:g} cm")
laje["area_m2"] = c[1].number_input(
    "Area (m2)", min_value=0.0, step=0.1,
    value=float(laje.get("area_m2") or 0.0),
    help=f"Minimo: {C.LAJE_AREA_MIN_M2:g} m2")
laje["rebordo_cm"] = c[2].number_input(
    "Cota do rebordo acima do terreno (cm)", min_value=0.0, step=1.0,
    value=float(laje.get("rebordo_cm") or 0.0),
    help=f"Minimo: {C.LAJE_REBORDO_MIN_CM:g} cm")
proc["laje"] = laje

st.markdown("---")

# ======================================================================================
# 5. Equipamentos
# ======================================================================================

passo(5, "Equipamentos de medicao e recalque")
col_h, col_b = st.columns(2)

with col_h:
    st.markdown("**Hidrometro**")
    h = proc.get("hidrometro") or {}
    h["fabricante"] = st.text_input("Fabricante (hidrometro)", value=h.get("fabricante", ""))
    c = st.columns(2)
    h["modelo"] = c[0].text_input("Modelo (hidrometro)", value=h.get("modelo", ""))
    h["numero_serie"] = c[1].text_input("N. de serie", value=h.get("numero_serie", ""))
    c = st.columns(2)
    h["vazao_nominal_m3h"] = c[0].number_input(
        "Vazao nominal (m3/h)", min_value=0.0, step=0.1,
        value=float(h.get("vazao_nominal_m3h") or 0.0))
    h["diametro_nominal_mm"] = c[1].number_input(
        "Diametro nominal DN (mm)", min_value=0.0, step=1.0,
        value=float(h.get("diametro_nominal_mm") or 0.0))
    h["classe_metrologica"] = st.text_input("Classe metrologica",
                                            value=h.get("classe_metrologica", ""))
    proc["hidrometro"] = h

with col_b:
    st.markdown("**Motobomba**")
    b = proc.get("motobomba") or {}
    b["fabricante"] = st.text_input("Fabricante (bomba)", value=b.get("fabricante", ""))
    c = st.columns(2)
    b["modelo"] = c[0].text_input("Modelo (bomba)", value=b.get("modelo", ""))
    b["numero_serie"] = c[1].text_input("N. de serie ", value=b.get("numero_serie", ""))
    c = st.columns(4)
    b["diametro_pol"] = c[0].number_input("Diametro (pol)", min_value=0.0, step=0.5,
                                          value=float(b.get("diametro_pol") or 0.0))
    b["potencia_hp"] = c[1].number_input("Potencia (HP/CV)", min_value=0.0, step=0.25,
                                         value=float(b.get("potencia_hp") or 0.0))
    b["num_estagios"] = c[2].number_input("N. de estagios", min_value=0, step=1,
                                          value=int(b.get("num_estagios") or 0))
    b["profundidade_instalacao_m"] = c[3].number_input(
        "Profundidade de instalacao do rotor/crivo (m)", min_value=0.0, step=1.0,
        value=float(b.get("profundidade_instalacao_m") or 0.0))
    c = st.columns(2)
    b["vazao_nominal_m3h"] = c[0].number_input(
        "Vazao nominal da bomba (m3/h)", min_value=0.0, step=0.1,
        value=float(b.get("vazao_nominal_m3h") or 0.0))
    b["altura_manometrica_mca"] = c[1].number_input(
        "Altura manometrica (m.c.a.)", min_value=0.0, step=1.0,
        value=float(b.get("altura_manometrica_mca") or 0.0))
    proc["motobomba"] = b

st.markdown("**Reservacao**")
res = proc.get("reservacao") or []
n_res = st.number_input("Quantidade de reservatorios", min_value=0, max_value=20,
                        value=len(res) or 1, step=1)
novos = []
for i in range(int(n_res)):
    c = st.columns([3, 1])
    atual = res[i] if i < len(res) else {}
    capacidade = c[0].number_input(
        f"Capacidade do reservatorio {i + 1} (L)", min_value=0.0, step=100.0,
        value=float(atual.get("capacidade_l") or 0.0), key=f"res_cap_{i}")
    local = c[1].text_input(f"Local {i + 1}", value=atual.get("local", ""),
                            key=f"res_loc_{i}")
    novos.append({"capacidade_l": capacidade, "local": local})
proc["reservacao"] = novos

st.markdown("---")

# ======================================================================================
# 6. Padrao de explotacao e finalidades
# ======================================================================================

passo(6, "Padrao de explotacao e restricoes operacionais")
pe = proc.get("padrao_explotacao") or {}
c = st.columns(2)
horas = c[0].number_input(
    "Tempo diario de bombeamento pretendido (horas/dia)",
    min_value=0.0, max_value=24.0, step=0.5,
    value=float(pe.get("horas_dia") or 0.0),
    help=f"Trava da plataforma: {C.BOMBEAMENTO_TRAVA_H_DIA:g} h/dia. "
         f"Limite absoluto do SIOUT RS: {C.BOMBEAMENTO_MAX_H_DIA:g} h/dia "
         f"(repouso minimo de {C.REPOUSO_MINIMO_H:g} h).")
dias = c[1].number_input(
    "Periodicidade semanal pretendida (dias/semana)",
    min_value=0, max_value=7, step=1,
    value=int(pe.get("dias_semana") or 0))
pe["horas_dia"] = horas
pe["dias_semana"] = dias
proc["padrao_explotacao"] = pe

if horas:
    repouso = 24.0 - horas
    if horas > C.BOMBEAMENTO_MAX_H_DIA:
        st.error(
            f"**BLOQUEIO:** com {horas:g} h/dia restam apenas {repouso:g} h de "
            f"repouso. O SIOUT RS exige repouso minimo de {C.REPOUSO_MINIMO_H:g} h/dia."
        )
    elif horas > C.BOMBEAMENTO_TRAVA_H_DIA:
        st.warning(
            f"Acima da trava de {C.BOMBEAMENTO_TRAVA_H_DIA:g} h/dia "
            f"(repouso de {repouso:g} h)."
        )
    else:
        st.success(f"Repouso diario do aquifero: {repouso:g} h "
                   f"(minimo {C.REPOUSO_MINIMO_H:g} h).")

st.markdown("---")

# ======================================================================================
# 7. Finalidades e regra de bloqueio condicional
# ======================================================================================

passo(7, "Finalidades do uso da agua")
st.markdown("**O imovel e atendido por rede publica de abastecimento de agua?**")
rede = st.radio(
    "Resposta obrigatoria",
    ["Sim", "Nao"],
    index=0 if proc.get("rede_publica") else (1 if proc.get("rede_publica") is False else None),
    horizontal=True,
    key="rede_publica",
)
proc["rede_publica"] = (rede == "Sim")

if proc["rede_publica"]:
    st.error(
        "**REGRA DE BLOQUEIO CONDICIONAL ATIVA** — o imovel e atendido por rede "
        "publica. A plataforma **proibe** a selecao de finalidades voltadas ao "
        "abastecimento humano direto, sanitarios e cozinha. A captacao somente "
        "podera ser destinada a fins industriais, limpeza geral de patio, "
        "irrigacao ou recirculacao, exigindo declaracao de separacao fisica de "
        "redes hidraulicas."
    )

disponiveis = a1.finalidades_disponiveis(proc["rede_publica"])
selecionadas = list(proc.get("finalidades") or [])

cols = st.columns(3)
escolhidas = []
for i, (chave, rotulo, permitida) in enumerate(disponiveis):
    with cols[i % 3]:
        if permitida:
            marcada = st.checkbox(rotulo, value=chave in selecionadas, key=f"fin_{chave}")
            if marcada:
                escolhidas.append(chave)
        else:
            st.checkbox(rotulo, value=False, disabled=True, key=f"fin_b_{chave}",
                        help="Bloqueada: imovel atendido por rede publica.")

# Preserva finalidades ja registradas que nao estao mais disponiveis (para exibir como
# pendencia de bloqueio em vez de apagar silenciosamente).
for f in selecionadas:
    if f not in escolhidas and f in dict((k, 1) for k, _, _ in disponiveis):
        pass
proc["finalidades"] = escolhidas

if proc["rede_publica"]:
    declarada = st.checkbox(
        "Declaro a separacao fisica integral das redes hidraulicas (sem interconexao, "
        "cross-connection ou by-pass).",
        value=bool(proc.get("declaracao_separacao_redes")),
    )
    proc["declaracao_separacao_redes"] = declarada
    up_sep = st.file_uploader(
        "Anexar comprovante da separacao de redes (PDF/imagem)",
        type=["pdf", "png", "jpg", "jpeg"], key="up_sep")
    if up_sep is not None:
        a1.registrar_upload(proc, "declaracao_separacao_redes", up_sep)
        st.success(f"Recebido: {up_sep.name}")

st.markdown("---")

# ======================================================================================
# 8. Checklist e validacao final
# ======================================================================================

passo(8, "Checklist obrigatorio e liberacao do Agente 2")
for item in a1.checklist_visual(proc):
    mapa = {"ok": "ok", "pendente": "bloqueio", "parcial": "pendente",
            "dispensado": "off"}
    st.markdown(
        f'{chip(item["item"], mapa.get(item["status"], "off"))}'
        f'<span class="out-fonte">{item["detalhe"]}</span>',
        unsafe_allow_html=True,
    )

st.markdown("")
resultado = a1.resumo_validacao(a1.validar(proc))
bloco_status(resultado)

st.markdown("")
col_salvar, col_avancar = st.columns([1, 1])
with col_salvar:
    if st.button("💾 Guardar triagem", width="stretch"):
        proc.salvar()
        st.success("Triagem guardada.")

with col_avancar:
    pode, bloqueios = a1.pode_avancar(proc)
    if st.button("➡️ Guardar e avancar para o Agente 2", type="primary",
                 width="stretch", disabled=not pode):
        proc.salvar()
        st.success("Triagem validada. A avancar para a Inteligencia Espacial...")
        st.switch_page("pages/2_Inteligencia_Espacial.py")
    if not pode:
        st.caption(f"Existem {len(bloqueios)} pendencia(s) bloqueante(s).")
