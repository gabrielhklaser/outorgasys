# -*- coding: utf-8 -*-
"""
Agente 4 - Balanco Hidrico, Restricoes e Engenharia de Equipamentos.

Valida se a demanda solicitada e sustentavel perante a capacidade real do poco,
audita motobomba / hidrometro / reservacao e monta o Quadro de Vazao da
Intervencao exigido pelo SIOUT RS.
"""

from __future__ import annotations

import calendar
import math
from typing import Any

from .. import config as C
from .. import rules


# --------------------------------------------------------------------------------------
# Calendario de operacao
# --------------------------------------------------------------------------------------


def dias_operacao_por_mes(ano: int, dias_semana: float) -> list[float]:
    """Dias de operacao em cada mes, a partir da periodicidade semanal.

    A periodicidade informada (dias por semana) e distribuida proportionalmente
    sobre os dias uteis de cada mes do calendario informado.
    """
    fracao = max(0.0, min(1.0, float(dias_semana) / 7.0))
    out = []
    for mes in range(1, 13):
        n_dias = calendar.monthrange(ano, mes)[1]
        out.append(round(n_dias * fracao, 2))
    return out


def quadro_vazao(ano: int, horas_dia: float, dias_semana: float,
                 vazao_m3h: float) -> dict:
    """Quadro de Vazao da Intervencao (12 meses), formato SIOUT RS."""
    dias = dias_operacao_por_mes(ano, dias_semana)
    linhas = []
    total = 0.0
    for i, (nome, n_dias) in enumerate(zip(C.NOMES_MESES, dias), start=1):
        volume = n_dias * horas_dia * vazao_m3h
        total += volume
        linhas.append({
            "mes": nome,
            "mes_num": i,
            "dias_mes": C.DIAS_POR_MES[i - 1] if not calendar.isleap(ano) or i != 2 else 29,
            "dias_operacao": round(n_dias, 2),
            "horas_dia": round(float(horas_dia), 2),
            "vazao_m3h": round(float(vazao_m3h), 3),
            "volume_m3_mes": round(volume, 2),
        })
    return {
        "ano_referencia": ano,
        "linhas": linhas,
        "volume_anual_m3": round(total, 2),
        "vazao_media_diaria_m3_dia": round(total / (365 if not calendar.isleap(ano) else 366), 3),
        "vazao_diaria_max_m3_dia": round(horas_dia * vazao_m3h, 3),
        "horas_dia": horas_dia,
        "dias_semana": dias_semana,
    }


# --------------------------------------------------------------------------------------
# Auditoria de equipamentos
# --------------------------------------------------------------------------------------


def auditar_equipamentos(proc, q_estavel: float | None, q_ot: float | None,
                         nd_m: float | None, vazao_adotada: float | None,
                         horas_dia: float | None) -> dict:
    """Cruzamento da capacidade do poco com os equipamentos declarados."""
    bomba = proc.get("motobomba") or {}
    hidro = proc.get("hidrometro") or {}
    reserv = proc.get("reservacao") or []

    r_bomba = rules.avaliar_motobomba_vs_poco(bomba, q_estavel, nd_m, q_ot)
    r_hidro = rules.avaliar_hidrometro(hidro, vazao_adotada)
    r_res = rules.avaliar_reservacao(reserv, vazao_adotada, horas_dia)

    capacidade_total_l = sum(
        float(x.get("capacidade_l") or 0) for x in (reserv or [])
        if str(x.get("capacidade_l") or "").strip()
    )

    pendencias = [p.to_dict() for r in (r_bomba, r_hidro, r_res) for p in r]

    return {
        "motobomba": {
            "declarado": bomba,
            "vazao_nominal_m3h": _num(bomba.get("vazao_nominal_m3h")),
            "profundidade_instalacao_m": _num(bomba.get("profundidade_instalacao_m")),
            "submergencia_m": (_num(bomba.get("profundidade_instalacao_m")) - nd_m)
            if (_num(bomba.get("profundidade_instalacao_m")) is not None
                and nd_m is not None) else None,
            "submergencia_recomendada_m": [C.SUBMERGENCIA_MIN_M, C.SUBMERGENCIA_MAX_M],
            "faixa_vazao_recomendada_m3h": (
                [round(0.8 * (q_ot or q_estavel), 2), round(1.1 * (q_ot or q_estavel), 2)]
                if (q_ot or q_estavel) else None),
        },
        "hidrometro": {
            "declarado": hidro,
            "vazao_nominal_m3h": _num(hidro.get("vazao_nominal_m3h")),
            "diametro_nominal_mm": _num(hidro.get("diametro_nominal_mm")),
            "velocidade_media_m_s": _velocidade(hidro, vazao_adotada),
        },
        "reservacao": {
            "itens": reserv,
            "capacidade_total_l": capacidade_total_l,
            "capacidade_total_m3": round(capacidade_total_l / 1000.0, 3),
        },
        "pendencias": pendencias,
        "ok": all(not p["bloqueante"] for p in pendencias),
    }


def _num(v: Any) -> float | None:
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(str(v).replace(",", "."))
    except Exception:  # noqa: BLE001
        return None


def _velocidade(hidro: dict, vazao: float | None) -> float | None:
    dn = _num(hidro.get("diametro_nominal_mm"))
    if not dn or not vazao:
        return None
    area = math.pi * (dn / 2000.0) ** 2
    return round((vazao / 3600.0) / area, 3) if area else None


# --------------------------------------------------------------------------------------
# Vazao adotada (recomendacao tecnica)
# --------------------------------------------------------------------------------------


def escolher_vazao_adotada(hidraulica: dict, preferencia: str = "auto") -> dict:
    """Decide entre Q_estavel e Q_ot, com justificativa tecnica."""
    p = (hidraulica or {}).get("parametros") or {}
    q_est = p.get("q_estavel_m3h")
    q_ot = p.get("Q_ot_m3h")
    q_jl = p.get("Q_jacob_lohman_m3h")

    if preferencia == "q_estavel" and q_est:
        return {"vazao": q_est, "origem": "Q_estavel",
                "justificativa": "Adotada a vazao estabilizada por decisao expressa do "
                                 "responsavel tecnico."}
    if preferencia == "q_ot" and q_ot:
        return {"vazao": q_ot, "origem": "Q_ot",
                "justificativa": "Adotada a vazao otima de explotacao por decisao "
                                 "expressa do responsavel tecnico."}

    if q_ot and q_est:
        adotada = min(q_ot, q_est)
        return {
            "vazao": adotada,
            "origem": "Q_ot" if adotada == q_ot else "Q_estavel",
            "justificativa": (
                "Adota-se o menor valor entre Q_ot (vazao otima de campo, que ja "
                "incorpora o fator de seguranca de longo prazo de "
                f"{C.FATOR_LONGO_PRAZO:g}) e Q_estavel, por criterio de seguranca "
                "hidrogeologica e preservacao do aquifero."),
        }
    if q_est:
        return {"vazao": q_est, "origem": "Q_estavel",
                "justificativa": "Sem Q_ot calculada (falta ensaio de recuperacao); "
                                 "adota-se Q_estavel com ressalva expressa no parecer."}
    if q_jl:
        return {"vazao": q_jl, "origem": "Jacob-Lohman",
                "justificativa": "Sem Q_estavel/Q_ot: usada a estimativa de "
                                 "Jacob-Lohman como ultimo recurso."}
    return {"vazao": None, "origem": None, "justificativa": "Sem dados hidraulicos."}


# --------------------------------------------------------------------------------------
# Agente
# --------------------------------------------------------------------------------------


def executar(proc, ano: int | None = None, preferencia_vazao: str = "auto") -> dict:
    """Executa o Agente 4 e devolve o balanco completo + auditorias."""
    import datetime as _dt

    ano = ano or _dt.date.today().year
    pe = proc.get("padrao_explotacao") or {}
    horas_dia = _num(pe.get("horas_dia"))
    dias_semana = _num(pe.get("dias_semana"))

    hidraulica = proc.get("hidraulica") or {}
    escolha = escolher_vazao_adotada(hidraulica, preferencia_vazao)
    vazao = escolha["vazao"]

    p = (hidraulica or {}).get("parametros") or {}
    q_est = p.get("q_estavel_m3h")
    q_ot = p.get("Q_ot_m3h")
    nd = p.get("nd_m")

    saida: dict[str, Any] = {
        "ok": False,
        "ano_referencia": ano,
        "vazao_adotada": escolha,
        "quadro": None,
        "equipamentos": None,
        "pendencias": [],
        "avisos": [],
        "erros": [],
    }

    # --- validacoes de regime ----------------------------------------------------------
    r_regime = rules.validar_padrao_explotacao(horas_dia, dias_semana)
    for pend in r_regime:
        saida["pendencias"].append(pend.to_dict())
    if not r_regime.ok or vazao is None or not horas_dia or not dias_semana:
        saida["erros"].append(
            "Regime de explotacao incompleto ou vazao adotada indisponivel: "
            "o quadro de vazoes nao pode ser montado."
        )
        return saida

    # --- quadro de vazoes --------------------------------------------------------------
    quadro = quadro_vazao(ano, horas_dia, dias_semana, vazao)
    saida["quadro"] = quadro

    # Verificacao: demanda diaria nao pode exceder a capacidade do poco.
    if q_est and vazao and vazao > q_est * 1.0001:
        saida["avisos"].append(
            f"A vazao adotada ({vazao:.2f} m3/h) excede a vazao estabilizada medida "
            f"({q_est:.2f} m3/h)."
        )
    if q_ot and vazao and vazao > q_ot * 1.05:
        saida["avisos"].append(
            f"A vazao adotada ({vazao:.2f} m3/h) excede em mais de 5% a vazao otima "
            f"de campo Q_ot ({q_ot:.2f} m3/h). Recomenda-se reduzir o regime."
        )

    # --- auditoria de equipamentos -------------------------------------------------------
    saida["equipamentos"] = auditar_equipamentos(proc, q_est, q_ot, nd, vazao, horas_dia)

    # --- repouso diario -------------------------------------------------------------------
    repouso = 24.0 - float(horas_dia)
    saida["repouso_diario_h"] = round(repouso, 2)
    saida["repouso_atende"] = repouso >= C.REPOUSO_MINIMO_H
    if not saida["repouso_atende"]:
        saida["pendencias"].append({
            "codigo": "EXP-003", "titulo": "Repouso minimo violado",
            "mensagem": f"Repouso de {repouso:g} h inferior ao minimo de "
                        f"{C.REPOUSO_MINIMO_H:g} h.",
            "bloqueante": True, "agente": 4,
        })

    saida["ok"] = all(not p.get("bloqueante") for p in saida["pendencias"])
    return saida


def quadro_para_tabela(quadro: dict) -> list[dict]:
    """Linhas do Quadro de Vazao da Intervencao prontas para o relatorio."""
    return quadro.get("linhas", [])
