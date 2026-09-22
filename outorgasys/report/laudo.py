# -*- coding: utf-8 -*-
"""
Laudo Tecnico de Caracterizacao Hidrogeologica + Memorial Descritivo (Agente 5).

Gera um documento tecnico coeso e formal, em Markdown editavel e em PDF, pronto
para assinatura por profissional habilitado (Geologo ou Engenheiro de Minas,
conforme a norma CEGM/CREA-RS n. 08/2022) e upload no SIOUT RS.
"""

from __future__ import annotations

import base64
import datetime as dt
from pathlib import Path
from typing import Any, Iterable

from .. import config as C


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def _v(d: dict | None, *caminho, padrao="-") -> Any:
    cur = d or {}
    for k in caminho:
        if not isinstance(cur, dict):
            return padrao
        cur = cur.get(k)
    if cur in (None, "", [], {}):
        return padrao
    return cur


def _n(v: Any, casas: int = 2, un: str = "", padrao: str = "-") -> str:
    if v is None or v == "":
        return padrao
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    s = f"{f:,.{casas}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} {un}".strip() if un else s


def _sn(v: Any) -> str:
    return "Sim" if v else ("Nao" if v is False else "-")


def _fmt_moeda_br(v: float) -> str:
    return _n(v, 2)


def _rotulos_finalidades(chaves: Iterable[str]) -> str:
    nomes = [C.FINALIDADES.get(k, (k, False))[0] for k in (chaves or [])]
    return ", ".join(nomes) if nomes else "-"


def _tabela_md(linhas: list[dict], colunas: list[tuple[str, str]]) -> str:
    if not linhas:
        return "_Sem dados disponiveis._"
    cab = "| " + " | ".join(rot for _, rot in colunas) + " |"
    sep = "|" + "|".join("---" for _ in colunas) + "|"
    corpo = []
    for ln in linhas:
        corpo.append("| " + " | ".join(str(ln.get(ch, "-")) for ch, _ in colunas) + " |")
    return "\n".join([cab, sep, *corpo])


# --------------------------------------------------------------------------------------
# Montagem das secoes
# --------------------------------------------------------------------------------------


def montar_estrutura(proc, resp_tecnico: dict | None = None,
                     art: str | None = None) -> dict:
    """Devolve a estrutura completa do laudo em dados puros (sem formatacao)."""
    resp_tecnico = resp_tecnico or {}
    enf = proc.get("enquadramento") or {}
    geo = proc.get("geoespacial") or {}
    coord = geo.get("coordenadas") or {}
    hid = proc.get("hidraulica") or {}
    hp = hid.get("parametros") or {}
    bal = proc.get("balanco") or {}
    req = proc.get("requerente") or {}
    imo = proc.get("imovel") or {}
    poco = proc.get("poco") or {}
    constr = proc.get("construtivo") or {}
    laje = proc.get("laje") or {}
    pe = proc.get("padrao_explotacao") or {}
    hidro = proc.get("hidrometro") or {}
    bomba = proc.get("motobomba") or {}
    reserv = proc.get("reservacao") or []
    det = geo.get("detalhes") or {}

    capacidade_total_l = sum(float(x.get("capacidade_l") or 0) for x in (reserv or [])
                             if str(x.get("capacidade_l") or "").strip())

    estrutura: dict[str, Any] = {
        "cabecalho": {
            "titulo": "LAUDO TECNICO DE CARACTERIZACAO HIDROGEOLOGICA",
            "subtitulo": "MEMORIAL DESCRITIVO PARA OUTORGA DE AGUA SUBTERRANEA - SIOUT/RS",
            "processo": proc.id,
            "data_emissao": dt.date.today().strftime("%d/%m/%Y"),
            "versao_sistema": C.VERSAO,
        },

        # ---- 1 ---------------------------------------------------------------------
        "identificacao": {
            "requerente": {
                "Nome / Razao social": _v(req, "nome"),
                "CPF / CNPJ": _v(req, "cpf_cnpj"),
                "RG / Inscricao estadual": _v(req, "rg_ie"),
                "Telefone": _v(req, "telefone"),
                "E-mail": _v(req, "email"),
            },
            "imovel": {
                "Denominacao": _v(imo, "denominacao"),
                "Endereco": _v(imo, "endereco"),
                "Bairro / Localidade": _v(imo, "bairro"),
                "Municipio / UF": f"{_v(imo, 'municipio')} / {_v(imo, 'uf', padrao='RS')}",
                "CEP": _v(imo, "cep"),
                "Coordenadas (SIRGAS 2000)": (
                    f"{coord.get('lat')}, {coord.get('lon')}"
                    if coord.get("lat") is not None else "-"),
                "Coordenadas UTM": (
                    f"E {_n(coord.get('utm_e'), 1)} m / N {_n(coord.get('utm_n'), 1)} m "
                    f"- fuso {coord.get('fuso', '-')} ({coord.get('epsg', '-')})"
                    if coord.get("utm_e") is not None else "-"),
                "Bacia hidrografica": _v(geo, "bacia_hidrografica"),
                "Regiao hidrografica": _v(geo, "regiao_hidrografica"),
                "Area do terreno (ha)": _v(imo, "area_ha"),
            },
            "documentacao_posse": [
                {"documento": C.DOCS_POSSE.get(k, k), "situacao": "Anexado"}
                for k in C.DOCS_POSSE if (proc.get("documentos") or {}).get(k)
            ],
        },

        # ---- 2 ---------------------------------------------------------------------
        "caracterizacao": {
            "poco": {
                "Tipo de poco": _v(enf, "rotulo"),
                "Classe SIOUT": _v(enf, "classe"),
                "Diametro util (pol)": _n(_v(poco, "diametro_util_pol", padrao=None), 2),
                "Profundidade total (m)": _n(poco.get("profundidade_total_m"), 2),
                "Diametro da perfuracao (mm)": _n(constr.get("diametro_perfuracao_mm"), 0),
                "Diametro do revestimento (mm)": _n(constr.get("diametro_revestimento_mm"), 0),
                "Espaco anular (mm)": _n(
                    ((float(constr["diametro_perfuracao_mm"]) - float(constr["diametro_revestimento_mm"])) / 2)
                    if constr.get("diametro_perfuracao_mm") and constr.get("diametro_revestimento_mm")
                    else None, 1),
                "Profundidade do selo sanitario (m)": _n(constr.get("profundidade_selo_m"), 2),
                "Posicao do crivo (m)": (
                    f"{_n(constr.get('crivo_de_m'), 2)} a {_n(constr.get('crivo_ate_m'), 2)}"
                    if constr.get("crivo_de_m") or constr.get("crivo_ate_m") else "-"),
                "Formacao geologica": _v(geo, "formacao_geologica"),
                "Litologia predominante": _v(det, "litologia"),
                "Classe de solo": _v(det, "classe_solo"),
                "Sistema aquifer": _v(geo, "sistema_aquifero")
                + (f" ({det['sistema_aquifero_nome']})" if det.get("sistema_aquifero_nome") else ""),
                "Tipo de aquifer": _v(constr, "tipo_aquifero"),
            },
            "laje_sanitaria": {
                "Espessura (cm)": _n(laje.get("espessura_cm"), 1),
                "Area (m2)": _n(laje.get("area_m2"), 2),
                "Cota do rebordo (cm)": _n(laje.get("rebordo_cm"), 1),
            },
            "corpo_hidrico": {
                "Corpo hidrico mais proximo": _v(geo, "corpo_hidrico_proximo", "nome"),
                "Distancia (m)": _n(_v(geo, "corpo_hidrico_proximo", "distancia_m",
                                       padrao=None), 1),
            },
            "raio_seguranca": det.get("raio_seguranca") or {},
        },

        # ---- 3 ---------------------------------------------------------------------
        "hidraulica": {
            "exige_ensaio": enf.get("exige_ensaio_24h"),
            "parametros": hid,
            "tabela": None,   # preenchida por tabela_parametros()
        },

        # ---- 4 ---------------------------------------------------------------------
        "equipamentos": {
            "motobomba": {
                "Fabricante": _v(bomba, "fabricante"),
                "Modelo": _v(bomba, "modelo"),
                "Numero de serie": _v(bomba, "numero_serie"),
                "Diametro (pol)": _n(bomba.get("diametro_pol"), 2),
                "Potencia (HP/CV)": _n(bomba.get("potencia_hp"), 2),
                "Numero de estagios": _n(bomba.get("num_estagios"), 0),
                "Profundidade de instalacao (m)": _n(bomba.get("profundidade_instalacao_m"), 2),
                "Vazao nominal (m3/h)": _n(bomba.get("vazao_nominal_m3h"), 2),
                "Altura manometrica (m.c.a.)": _n(bomba.get("altura_manometrica_mca"), 1),
            },
            "hidrometro": {
                "Fabricante": _v(hidro, "fabricante"),
                "Modelo": _v(hidro, "modelo"),
                "Numero de serie": _v(hidro, "numero_serie"),
                "Diametro nominal (DN)": _n(hidro.get("diametro_nominal_mm"), 0),
                "Vazao nominal (m3/h)": _n(hidro.get("vazao_nominal_m3h"), 2),
                "Classe metrologica": _v(hidro, "classe_metrologica"),
            },
            "reservacao": {
                "Quantidade de reservatorios": len([x for x in (reserv or [])
                                                    if x.get("capacidade_l")]),
                "Capacidade total (L)": _n(capacidade_total_l, 0),
                "Capacidade total (m3)": _n(capacidade_total_l / 1000 if capacidade_total_l else None, 3),
                "Detalhamento": [
                    {"reservatorio": f"Reservatorio {i}",
                     "capacidade_l": _n(x.get("capacidade_l"), 0, "L"),
                     "local": _v(x, "local")}
                    for i, x in enumerate([r for r in (reserv or []) if r.get("capacidade_l")], 1)
                ],
            },
            "auditoria": (bal.get("equipamentos") or {}),
        },

        # ---- 5 ---------------------------------------------------------------------
        "memorial": {
            "etapas": [
                {"etapa": "1. Captacao",
                 "descricao": (
                     f"Agua subterranea captada no poco tubular "
                     f"{_v(poco, 'nome')}, perfurado na {_v(geo, 'formacao_geologica')}, "
                     f"sistema aquifer {_v(geo, 'sistema_aquifero')}, a "
                     f"{_n(poco.get('profundidade_total_m'), 1, 'm')} de profundidade.")},
                {"etapa": "2. Automacao / recalque",
                 "descricao": (
                     f"Motobomba submersa {_v(bomba, 'fabricante')} {_v(bomba, 'modelo')}, "
                     f"{_n(bomba.get('potencia_hp'), 1, 'HP/CV')}, instalada a "
                     f"{_n(bomba.get('profundidade_instalacao_m'), 1, 'm')}, com "
                     f"{_n(bomba.get('num_estagios'), 0)} estagio(s). Partida por "
                     "quadro de comando com protecao termica e nivel.")},
                {"etapa": "3. Medicao",
                 "descricao": (
                     f"Hidrometro {_v(hidro, 'fabricante')} {_v(hidro, 'modelo')}, "
                     f"DN {_n(hidro.get('diametro_nominal_mm'), 0, 'mm')}, vazao nominal "
                     f"{_n(hidro.get('vazao_nominal_m3h'), 2, 'm3/h')}, instalado em "
                     "cavalete na saida do poco.")},
                {"etapa": "4. Reservacao superior",
                 "descricao": (
                     f"Reservacao total de {_n(capacidade_total_l, 0, 'L')} distribuida em "
                     f"{len([x for x in (reserv or []) if x.get('capacidade_l')])} "
                     "reservatorio(s), instalada em cota superior aos pontos de consumo.")},
                {"etapa": "5. Rede de distribuicao",
                 "descricao": (
                     "Rede interna de distribuicao por gravidade a partir da reservacao "
                     "superior, atendendo exclusivamente as finalidades declaradas.")},
            ],
            "fluxograma_ascii": (
                "  [ POCO TUBULAR ]\n"
                "        |\n"
                "        v\n"
                "  [ MOTOBOMBA SUBMERSA ] ---- [ QUADRO DE COMANDO / PROTECAO ]\n"
                "        |\n"
                "        v\n"
                "  [ CAVALETE + HIDROMETRO ]\n"
                "        |\n"
                "        v\n"
                "  [ RESERVATORIO SUPERIOR (caixa d'agua) ]\n"
                "        |\n"
                "        v\n"
                "  [ REDE DE DISTRIBUICAO INTERNA / EXTERNA ]\n"
                "        |\n"
                "        v\n"
                "  [ PONTOS DE CONSUMO (finalidades declaradas) ]"
            ),
        },

        # ---- 6 ---------------------------------------------------------------------
        "quadro_vazao": bal.get("quadro") or {},
        "regime": {
            "Horas por dia": _n(pe.get("horas_dia"), 2, "h/dia"),
            "Dias por semana": _n(pe.get("dias_semana"), 0, "dias/semana"),
            "Vazao adotada": _n(_v(bal, "vazao_adotada", "vazao", padrao=None), 3, "m3/h"),
            "Origem da vazao": _v(bal, "vazao_adotada", "origem"),
            "Justificativa": _v(bal, "vazao_adotada", "justificativa"),
            "Repouso diario": _n(bal.get("repouso_diario_h"), 2, "h"),
            "Repouso minimo exigido": f"{C.REPOUSO_MINIMO_H:g} h/dia (SIOUT RS)",
        },

        # ---- 7 ---------------------------------------------------------------------
        "parecer": {
            "finalidades": _rotulos_finalidades(proc.get("finalidades") or []),
            "rede_publica": _sn(proc.get("rede_publica")),
            "separacao_redes": _sn(proc.get("declaracao_separacao_redes")),
            "repouso_atende": bal.get("repouso_atende"),
            "conclusoes": [],   # preenchidas por montar_parecer()
            "recomendacoes": [],
        },

        "assinatura": {
            "responsavel_tecnico": _v(resp_tecnico, "nome"),
            "titulo": _v(resp_tecnico, "titulo"),
            "registro": _v(resp_tecnico, "registro"),
            "art": art or _v(resp_tecnico, "art"),
            "local_data": f"____________________, {dt.date.today().strftime('%d/%m/%Y')}",
            "nota_normativa": (
                "Conforme a norma CEGM/CREA-RS n. 08/2022, o presente laudo deve ser "
                "assinado por profissional habilitado (Geologo ou Engenheiro de Minas) "
                "com a respectiva Anotacao de Responsabilidade Tecnica (ART)."),
        },

        "anexos": {
            "mapas": geo.get("caminho_mapas") or [],
            "graficos": (hid.get("graficos") or {}),
            "proveniencia": geo.get("proveniencia") or {},
        },
    }

    estrutura["hidraulica"]["tabela"] = tabela_parametros(proc)
    estrutura["parecer"] = montar_parecer(proc, estrutura)
    return estrutura


def tabela_parametros(proc) -> list[dict]:
    """Tabela de parametros hidraulicos (secao 3 do relatorio)."""
    from ..agents import agente3_hidro

    hid = proc.get("hidraulica") or {}
    if not hid:
        return []
    return agente3_hidro.tabela_memoria(hid)


def montar_parecer(proc, estrutura: dict) -> dict:
    """Redige as conclusoes e recomendacoes automaticas do parecer."""
    parecer = estrutura.get("parecer") or {}
    conclusoes: list[str] = []
    recomendacoes: list[str] = []

    enf = proc.get("enquadramento") or {}
    geo = proc.get("geoespacial") or {}
    hid = proc.get("hidraulica") or {}
    hp = hid.get("parametros") or {}
    bal = proc.get("balanco") or {}
    pe = proc.get("padrao_explotacao") or {}
    det = geo.get("detalhes") or {}

    # Conclusoes -------------------------------------------------------------------------
    conclusoes.append(
        f"O poco enquadra-se como {enf.get('rotulo', 'nao classificado')}. "
        + ("Exige ensaio de bombeamento continuo de 24 horas acompanhado do ensaio de "
           "recuperacao, o qual foi apresentado e analisado."
           if enf.get("exige_ensaio_24h") else
           "Nao exige ensaio de bombeamento de 24 horas, sendo mantidas as demais "
           "exigencias cadastrais, documentais, de equipamentos e de qualidade de agua."))

    if geo.get("municipio"):
        conclusoes.append(
            f"O ponto de captacao localiza-se no municipio de {geo['municipio']}/RS, "
            f"na {geo.get('bacia_hidrografica') or 'bacia hidrografica nao determinada'}"
            + (f", integrando a {geo['regiao_hidrografica']}."
               if geo.get("regiao_hidrografica") else "."))

    if geo.get("formacao_geologica") or geo.get("sistema_aquifero"):
        conclusoes.append(
            f"A captacao ocorre na {geo.get('formacao_geologica') or 'unidade geologica nao determinada'}"
            + (f" ({det['litologia']})" if det.get("litologia") else "")
            + (f", integrando o {geo['sistema_aquifero']}." if geo.get("sistema_aquifero") else "."))

    if hp.get("Q_ot_m3h"):
        conclusoes.append(
            f"A vazao otima de explotacao de campo calculada e de "
            f"{_n(hp['Q_ot_m3h'], 2, 'm3/h')}, obtida a partir da vazao estabilizada de "
            f"{_n(hp.get('q_estavel_m3h'), 2, 'm3/h')} e do rebaixamento maximo de "
            f"{_n(hp.get('s_max_m'), 2, 'm')}, com transmissividade de "
            f"{_n(hp.get('T_m2h'), 3, 'm2/h')} ({_n(hp.get('T_m2s'), 6, 'm2/s')}).")

    adot = (bal.get("vazao_adotada") or {})
    if adot.get("vazao"):
        conclusoes.append(
            f"Recomenda-se a vazao de explotacao de {_n(adot['vazao'], 2, 'm3/h')} "
            f"({adot.get('origem')}), resultando em volume anual estimado de "
            f"{_n((bal.get('quadro') or {}).get('volume_anual_m3'), 0, 'm3/ano')}.")

    # Repouso ------------------------------------------------------------------------------
    repouso = bal.get("repouso_diario_h")
    if repouso is not None:
        if bal.get("repouso_atende"):
            conclusoes.append(
                f"O regime operacional proposto reserva {_n(repouso, 1, 'h/dia')} de "
                f"repouso ao aquifero, atendendo ao repouso minimo de "
                f"{C.REPOUSO_MINIMO_H:g} h/dia exigido pelo SIOUT RS.")
        else:
            recomendacoes.append(
                f"REGULARIZAR: o regime proposto reserva apenas {_n(repouso, 1, 'h/dia')} "
                f"de repouso, abaixo do minimo de {C.REPOUSO_MINIMO_H:g} h/dia.")

    # Rede publica --------------------------------------------------------------------------
    if proc.get("rede_publica"):
        conclusoes.append(
            "O imovel e atendido por rede publica de abastecimento de agua. Declara-se a "
            "SEPARACAO FISICA DAS REDES HIDRAULICAS, sem qualquer interconexao, "
            "cross-connection ou by-pass entre a rede publica e a rede alimentada pelo "
            "poco, ficando a agua subterranea restrita as finalidades nao destinadas ao "
            "consumo humano direto.")
        recomendacoes.append(
            "Manter sinalizacao permanente e distinta nas duas redes (padrao de cores "
            "diferenciado) e submeter o sistema a inspecao periodica, de modo a "
            "comprovar a ausencia de interconexao.")

    # Distancia a corpo hidrico -----------------------------------------------------------------
    ch = geo.get("corpo_hidrico_proximo") or {}
    if ch.get("distancia_m") is not None:
        if ch["distancia_m"] < 50:
            recomendacoes.append(
                f"O poco dista apenas {_n(ch['distancia_m'], 1, 'm')} do corpo hidrico "
                f"'{ch.get('nome')}'. Recomenda-se estudo de conexao hidraulica "
                "rio-aquifero e monitoramento piezometrico conjunto.")
        else:
            conclusoes.append(
                f"A distancia ao corpo hidrico superficial mais proximo "
                f"('{ch.get('nome')}') e de {_n(ch['distancia_m'], 1, 'm')}, acima do "
                "limiar de 50 m que exigiria estudo de interferencia especifico.")

    # Raio de seguranca ---------------------------------------------------------------------------
    rs = det.get("raio_seguranca") or {}
    ocorr = rs.get("ocorrencias") or {}
    if ocorr:
        recomendacoes.append(
            "Dentro do raio de seguranca de "
            f"{C.RAIO_SEGURANCA_M:g} m foram identificadas as seguintes ocorrencias: "
            + ", ".join(f"{k} ({v} feicao/feicoes)" for k, v in ocorr.items())
            + ". Recomenda-se vistoria de campo para avaliacao e mitigacao das fontes "
              "potenciais de poluicao, com prioridade para postos de combustivel, "
              "estacoes de tratamento de esgoto, tanques e areas industriais.")
    else:
        conclusoes.append(
            f"Nao foram identificadas fontes potenciais de poluicao mapeadas dentro do "
            f"raio de seguranca de {C.RAIO_SEGURANCA_M:g} m nas bases consultadas; a "
            "constatacao deve ser confirmada por vistoria de campo.")

    # Pendencias nao bloqueantes --------------------------------------------------------------------
    for p in (geo.get("pendencias") or []):
        recomendacoes.append(f"[{p.get('codigo')}] {p.get('titulo')}: {p.get('mensagem')}")
    for aviso in (hid.get("avisos") or []):
        recomendacoes.append(f"[HIDRO] {aviso}")
    for aviso in (bal.get("avisos") or []):
        recomendacoes.append(f"[BALANCO] {aviso}")
    for p in ((bal.get("equipamentos") or {}).get("pendencias") or []):
        recomendacoes.append(f"[{p.get('codigo')}] {p.get('mensagem')}")

    # Recomendacoes padrao -------------------------------------------------------------------
    recomendacoes.extend([
        "Instalar e manter lacre e/ou sinalizacao no hidrometro, com leitura mensal "
        "registrada em planilha propria para fins de fiscalizacao da outorga.",
        "Manter a laje de protecao sanitaria integra, com tampa de acesso vedada e "
        "cercamento de protecao em bom estado de conservacao.",
        "Repetir a analise fisico-quimica e bacteriologica da agua em periodicidade "
        "minima semestral, conforme os parametros da Portaria GM/MS n. 888/2021.",
        "Em caso de rebaixamento anomalo, turbidez persistente ou reducao de vazao, "
        "suspender a operacao e comunicar o orgao gestor.",
    ])

    parecer["conclusoes"] = conclusoes
    parecer["recomendacoes"] = recomendacoes
    return parecer


# --------------------------------------------------------------------------------------
# Renderizacao Markdown
# --------------------------------------------------------------------------------------


def para_markdown(estrutura: dict, incluir_imagens: bool = True) -> str:
    L: list[str] = []
    cab = estrutura["cabecalho"]
    L.append(f"# {cab['titulo']}")
    L.append(f"## {cab['subtitulo']}")
    L.append("")
    L.append(f"**Processo:** {cab['processo']}  ")
    L.append(f"**Data de emissao:** {cab['data_emissao']}  ")
    L.append(f"**Sistema:** {C.NOME_SISTEMA} v{cab['versao_sistema']}")
    L.append("")

    def secao(n: int, titulo: str) -> None:
        L.append("")
        L.append(f"## {n}. {titulo}")
        L.append("")

    def dict_para_tabela(d: dict) -> None:
        L.append("| Item | Valor |")
        L.append("|---|---|")
        for k, v in d.items():
            L.append(f"| {k} | {v} |")
        L.append("")

    # 1
    secao(1, "IDENTIFICACAO DO REQUERENTE E DA PROPRIEDADE")
    L.append("### 1.1 Requerente")
    dict_para_tabela(estrutura["identificacao"]["requerente"])
    L.append("### 1.2 Imovel e localizacao")
    dict_para_tabela(estrutura["identificacao"]["imovel"])
    L.append("### 1.3 Documentacao de posse e terra")
    docs = estrutura["identificacao"]["documentacao_posse"]
    L.append(_tabela_md(docs, [("documento", "Documento"), ("situacao", "Situacao")]) if docs
             else "_Nenhum documento anexado._")
    L.append("")

    # 2
    secao(2, "CARACTERIZACAO CONSTRUTIVA E GEOLOGICA")
    L.append("### 2.1 Poco")
    dict_para_tabela(estrutura["caracterizacao"]["poco"])
    L.append("### 2.2 Laje de protecao sanitaria")
    dict_para_tabela(estrutura["caracterizacao"]["laje_sanitaria"])
    L.append(f"_Referencias: espessura minima {C.LAJE_ESPESSURA_MIN_CM:g} cm, area minima "
             f"{C.LAJE_AREA_MIN_M2:g} m2, rebordo minimo {C.LAJE_REBORDO_MIN_CM:g} cm; "
             f"espaco anular minimo {C.ESPACO_ANULAR_MIN_MM:g} mm; selo sanitario minimo "
             f"recomendado {C.SELO_SANITARIO_MIN_M:g} m._")
    L.append("")
    L.append("### 2.3 Corpo hidrico mais proximo e raio de seguranca")
    dict_para_tabela(estrutura["caracterizacao"]["corpo_hidrico"])
    rs = estrutura["caracterizacao"]["raio_seguranca"] or {}
    if rs.get("ocorrencias"):
        L.append("")
        L.append("**Ocorrencias no raio de seguranca de "
                 f"{C.RAIO_SEGURANCA_M:g} m:**")
        for k, v in rs["ocorrencias"].items():
            L.append(f"- {k}: {v} feicao(oes)")
    else:
        L.append("")
        L.append(f"_Nenhuma ocorrencia mapeada no raio de {C.RAIO_SEGURANCA_M:g} m._")
    L.append("")

    # 3
    secao(3, "PARAMETROS HIDRAULICOS E RESULTADOS DO ENSAIO")
    if not estrutura["hidraulica"]["exige_ensaio"]:
        L.append("_Poco de pequeno diametro (< 4\"): ensaio de bombeamento de 24 horas "
                 "dispensado pelo SIOUT RS._")
        L.append("")
    tabela = estrutura["hidraulica"]["tabela"]
    if tabela:
        L.append(_tabela_md(tabela, [("parametro", "Parametro"), ("valor", "Valor"),
                                     ("criterio", "Criterio / Formula")]))
    else:
        L.append("_Nenhum resultado hidraulico disponivel._")
    L.append("")
    if incluir_imagens:
        graf = (estrutura["anexos"]["graficos"] or {})
        if graf.get("painel"):
            L.append("### 3.1 Graficos do ensaio")
            L.append(f"![Graficos do ensaio]({graf['painel']})")
            L.append("")

    # 4
    secao(4, "DESCRICAO DOS EQUIPAMENTOS INSTALADOS")
    L.append("### 4.1 Motobomba submersa")
    dict_para_tabela(estrutura["equipamentos"]["motobomba"])
    L.append("### 4.2 Hidrometro")
    dict_para_tabela(estrutura["equipamentos"]["hidrometro"])
    L.append("### 4.3 Reservacao")
    res = dict(estrutura["equipamentos"]["reservacao"])
    detalhe = res.pop("Detalhamento", [])
    dict_para_tabela(res)
    if detalhe:
        L.append(_tabela_md(detalhe, [("reservatorio", "Reservatorio"),
                                      ("capacidade_l", "Capacidade"),
                                      ("local", "Local")]))
    L.append("### 4.4 Auditoria tecnica dos equipamentos")
    aud = estrutura["equipamentos"]["auditoria"] or {}
    pend = aud.get("pendencias") or []
    if pend:
        for p in pend:
            L.append(f"- **{p.get('codigo')}** - {p.get('titulo')}: {p.get('mensagem')}")
    else:
        L.append("_Nenhuma inconformidade identificada nos equipamentos declarados._")
    L.append("")

    # 5
    secao(5, "FLUXOGRAMA E MEMORIAL DO SISTEMA DE ABASTECIMENTO")
    L.append("### 5.1 Memorial descritivo do percurso da agua")
    for e in estrutura["memorial"]["etapas"]:
        L.append(f"- **{e['etapa']}** - {e['descricao']}")
    L.append("")
    L.append("### 5.2 Fluxograma esquematico em bloco")
    L.append("```")
    L.append(estrutura["memorial"]["fluxograma_ascii"])
    L.append("```")

    # 6
    secao(6, "QUADRO DE VAZAO HOMOLOGADO DO SIOUT")
    L.append("### 6.1 Regime operacional")
    dict_para_tabela(estrutura["regime"])
    q = estrutura.get("quadro_vazao") or {}
    if q.get("linhas"):
        L.append("### 6.2 Quadro de Vazao da Intervencao")
        L.append(_tabela_md(q["linhas"], [
            ("mes", "Mes"), ("dias_operacao", "Dias/Mes"), ("horas_dia", "Horas/Dia"),
            ("vazao_m3h", "Vazao (m3/h)"), ("volume_m3_mes", "Volume (m3/mes)")]))
        L.append("")
        L.append(f"**Volume anual total:** {_n(q.get('volume_anual_m3'), 0, 'm3/ano')}")
        L.append("")
        L.append(f"**Vazao diaria maxima:** {_n(q.get('vazao_diaria_max_m3_dia'), 2, 'm3/dia')}")
        L.append("")
    else:
        L.append("_Quadro de vazoes nao disponivel._")

    # 7
    secao(7, "PARECER CONCLUSIVO E RECOMENDACOES")
    L.append("### 7.1 Conclusoes")
    for c in estrutura["parecer"]["conclusoes"]:
        L.append(f"- {c}")
    L.append("")
    L.append("### 7.2 Recomendacoes")
    for r in estrutura["parecer"]["recomendacoes"]:
        L.append(f"- {r}")
    L.append("")
    L.append("### 7.3 Declaracoes")
    L.append(f"- Imovel atendido por rede publica de abastecimento: "
             f"**{estrutura['parecer']['rede_publica']}**")
    if estrutura["parecer"]["rede_publica"] == "Sim":
        L.append("- **Atestado de separacao de redes:** declara-se a separacao fisica "
                 "integral das redes hidraulicas, sem interconexao entre a rede publica "
                 "e a rede alimentada pelo poco.")
    L.append(f"- **Repouso diario minimo do aquifero:** "
             f"{_n((estrutura['regime'] or {}).get('Repouso diario'), 1, 'h')} "
             f"(minimo exigido: {C.REPOUSO_MINIMO_H:g} h/dia)")
    L.append("")

    # Assinatura
    L.append("---")
    L.append("")
    L.append("## RESPONSAVEL TECNICO")
    L.append("")
    a = estrutura["assinatura"]
    L.append(f"**{a['responsavel_tecnico']}**  ")
    L.append(f"{a['titulo']}  ")
    L.append(f"Registro: {a['registro']}  ")
    L.append(f"ART: {a['art']}  ")
    L.append("")
    L.append(f"{a['local_data']}")
    L.append("")
    L.append("_______________________________________________")
    L.append("Assinatura do Responsavel Tecnico")
    L.append("")
    L.append(f"_{a['nota_normativa']}_")
    L.append("")

    # Proveniencia
    L.append("---")
    L.append("")
    L.append("## APENDICE A - PROVENIENCIA DAS BASES GEOESPACIAIS")
    L.append("")
    prov = (estrutura["anexos"]["proveniencia"] or {})
    if prov:
        L.append("| Camada | Status | Origem | Feicoes |")
        L.append("|---|---|---|---|")
        for k in sorted(prov):
            v = prov[k] or {}
            L.append(f"| {k} | {v.get('status', '-')} | {v.get('origem', '-')} | "
                     f"{v.get('feicoes', '-')} |")
    else:
        L.append("_Nenhuma camada geoespacial processada._")

    return "\n".join(L)
