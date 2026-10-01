# -*- coding: utf-8 -*-
"""Agente 3: vazao manual e planilhas com a coluna Q incompleta."""

from __future__ import annotations

import json

import pytest

from outorgasys import config as C
from outorgasys.agents import agente3_hidro as a3
from outorgasys.hydro import theis
from outorgasys.state import Processo

EXEMPLO_JSON = C.ROOT / "data" / "processos" / f"{C.PROCESSO_EXEMPLO}.json"

pytestmark = pytest.mark.skipif(not EXEMPLO_JSON.exists(),
                                reason="processo de exemplo ausente")


def _processo(dados_tmp, sem_vazao: bool) -> Processo:
    """Processo carregado do disco com o ensaio real do exemplo."""
    base = json.loads(EXEMPLO_JSON.read_text(encoding="utf-8"))
    base["id"] = "T-A3-001"
    (C.PROCESSOS / "T-A3-001.json").write_text(json.dumps(base), encoding="utf-8")
    p = Processo.carregar("T-A3-001")
    if sem_vazao:
        p["ensaio"]["bombeamento"]["q_m3h"] = float("nan")
    return p


def test_vazao_manual_calcula_t_e_q_ot_quando_a_planilha_nao_tem_q(dados_tmp):
    p = _processo(dados_tmp, sem_vazao=True)

    out = a3.calcular(p, usar_q_manual=True, q_manual=12.0, gerar_graficos=False)

    par = out["parametros"]
    assert par["q_estavel_m3h"] == 12.0
    assert par["T_m2h"] == pytest.approx(0.183 * 12.0 / par["delta_s_linha_m"])
    assert par["Q_ot_m3h"] == pytest.approx(0.8 * par["T_m2h"] * par["s_max_m"])


def test_vazao_manual_prevalece_sobre_a_da_planilha_no_calculo_de_t(dados_tmp):
    p = _processo(dados_tmp, sem_vazao=False)

    out = a3.calcular(p, usar_q_manual=True, q_manual=10.0, gerar_graficos=False)

    par = out["parametros"]
    assert par["q_estavel_m3h"] == 10.0
    assert par["T_m2h"] == pytest.approx(0.183 * 10.0 / par["delta_s_linha_m"])
    metodo = out["memoria"]["vazao_estabilizada"]["metodo"]
    assert "manual" in metodo.lower()


def test_planilha_sem_q_e_sem_vazao_manual_informa_erro_sem_levantar(dados_tmp):
    p = _processo(dados_tmp, sem_vazao=True)

    out = a3.calcular(p, gerar_graficos=False)

    assert not out["ok"]
    assert any("vazao" in e.lower() for e in out["erros"])


def test_identificar_q_estavel_aceita_tempos_e_vazoes_de_tamanhos_diferentes():
    est = theis.identificar_q_estavel(list(range(59)), [])
    assert est.q_estavel is None

    est = theis.identificar_q_estavel(list(range(10)), [12.0, 12.1, 11.9, 12.0])
    assert est.q_estavel == pytest.approx(12.0, abs=0.1)
