# -*- coding: utf-8 -*-
"""Agente 4: quadro de vazao, vazao adotada e conversao numerica."""

from __future__ import annotations

import pytest

from outorgasys.agents import agente4_balanco as a4

# (horas/dia, dias/semana, vazao m3/h): inclui o regime do processo de exemplo
REGIMES = [
    (12.0, 5, 11.993949152542374),
    (7.2, 2, 16.398),
    (1.9, 7, 21.899),
    (24.0, 7, 0.5),
    (8.0, 3, 10.0),
]


@pytest.mark.parametrize("horas, dias, vazao", REGIMES)
def test_total_anual_e_a_soma_dos_volumes_mensais_exibidos(horas, dias, vazao):
    """Um quadro oficial precisa fechar: total = soma das linhas que ele mostra."""
    quadro = a4.quadro_vazao(2026, horas, dias, vazao)

    soma = round(sum(l["volume_m3_mes"] for l in quadro["linhas"]), 2)

    assert quadro["volume_anual_m3"] == soma


def test_quadro_do_exemplo_tem_12_meses_e_total_que_fecha():
    quadro = a4.quadro_vazao(2026, 12.0, 5, 11.993949152542374)

    assert len(quadro["linhas"]) == 12
    assert quadro["volume_anual_m3"] == 37521.84


def test_dias_de_operacao_sao_dias_corridos_proporcionais():
    dias = a4.dias_operacao_por_mes(2026, 7)
    assert dias[0] == 31 and dias[1] == 28           # 7 dias/semana = todos os dias
    dias5 = a4.dias_operacao_por_mes(2026, 5)
    assert dias5[0] == pytest.approx(31 * 5 / 7, abs=0.01)
    assert "uteis" not in (a4.dias_operacao_por_mes.__doc__ or "").lower()


@pytest.mark.parametrize("valor, esperado", [
    ("1.234,5", 1234.5), ("1,5", 1.5), (" 8 ", 8.0), (None, None), ("", None),
    ("nan", None), ("inf", None), ("abc", None),
])
def test_num_do_agente4_aceita_os_mesmos_formatos_que_rules(valor, esperado):
    assert a4._num(valor) == esperado


def _hid(q_est, q_ot):
    return {"parametros": {"q_estavel_m3h": q_est, "Q_ot_m3h": q_ot}}


def test_vazao_adotada_e_o_menor_entre_q_ot_e_q_estavel():
    menor_ot = a4.escolher_vazao_adotada(_hid(12.0, 9.0))
    assert menor_ot["vazao"] == 9.0 and menor_ot["origem"] == "Q_ot"

    menor_est = a4.escolher_vazao_adotada(_hid(8.0, 13.7))
    assert menor_est["vazao"] == 8.0 and menor_est["origem"] == "Q_estavel"


def test_vazao_adotada_sem_q_ot_usa_q_estavel_com_ressalva():
    r = a4.escolher_vazao_adotada(_hid(12.0, None), preferencia="q_ot")
    assert r["vazao"] == 12.0 and r["origem"] == "Q_estavel"
    assert "Sem Q_ot" in r["justificativa"]


def test_vazao_adotada_sem_dados_devolve_none():
    assert a4.escolher_vazao_adotada({})["vazao"] is None


def test_jacob_lohman_nao_vira_vazao_do_quadro():
    """A contraprova de Jacob-Lohman e informativa; nao substitui o ensaio.

    O ramo existia como "ultimo recurso", mas so e alcancavel se houver
    Q_jacob_lohman sem Q_estavel - e essa estimativa so e calculada quando existe
    Q_estavel. Se um dia fosse alcancado, colocaria uma estimativa de regime
    permanente no quadro de vazao que vai para a transcricao do SIOUT.
    """
    hid = {"parametros": {"q_estavel_m3h": None, "Q_ot_m3h": None,
                          "Q_jacob_lohman_m3h": 8.29}}

    r = a4.escolher_vazao_adotada(hid)

    assert r["vazao"] is None
    assert r["origem"] is None
    assert "Jacob-Lohman" in r["justificativa"]
    assert "8.29" in r["justificativa"]


def test_preferencia_expressa_nao_ignora_a_ausencia_de_dado():
    hid = {"parametros": {"q_estavel_m3h": None, "Q_ot_m3h": None,
                          "Q_jacob_lohman_m3h": 8.29}}

    assert a4.escolher_vazao_adotada(hid, preferencia="q_ot")["vazao"] is None
