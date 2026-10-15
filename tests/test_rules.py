# -*- coding: utf-8 -*-
"""Conversao numerica e validacao do padrao de explotacao."""

from __future__ import annotations

import pytest

from outorgasys import rules


@pytest.mark.parametrize("valor", [
    "nan", "NaN", "inf", "-inf", "Infinity", "-Infinity",
    float("nan"), float("inf"), float("-inf"),
])
def test_num_rejeita_valores_nao_finitos(valor):
    assert rules._num(valor) is None


@pytest.mark.parametrize("valor, esperado", [
    ("1,5", 1.5), ("1.234,5", 1234.5), (" 12 ", 12.0), ("-2,5", -2.5), ("0", 0.0),
    (3, 3.0), (2.5, 2.5), ("1.5", 1.5),
])
def test_num_le_formatos_brasileiros(valor, esperado):
    assert rules._num(valor) == esperado


@pytest.mark.parametrize("valor", [None, "", "  ", "abc", True, False, "1,2,3"])
def test_num_devolve_none_para_o_que_nao_e_numero(valor):
    assert rules._num(valor) is None


@pytest.mark.parametrize("horas", ["nan", "inf", float("nan"), float("inf")])
def test_horas_nao_finitas_nao_passam_na_validacao_do_regime(horas):
    resultado = rules.validar_padrao_explotacao(horas, 3)
    assert not resultado.ok
    assert any(p.bloqueante for p in resultado)


def test_regime_valido_continua_passando():
    assert rules.validar_padrao_explotacao(8, 5).ok


# --------------------------------------------------------------------------------------
# Reservacao: indices da lista informada e capacidade invalida
# --------------------------------------------------------------------------------------


def test_reservacao_valida_passa():
    assert rules.validar_reservacao(
        [{"capacidade_l": 5000.0}, {"capacidade_l": 2000.0}]).ok


def test_reservacao_sem_nada_gera_pendencia_unica():
    r = rules.validar_reservacao([])
    assert [p.codigo for p in r] == ["RES-001"]


def test_capacidade_zero_ou_ilegivel_aponta_o_reservatorio_certo():
    """O filtro antigo descartava capacidade 0 antes do laco: RES-002 nao saia.

    E o indice do titulo vinha da lista ja filtrada, apontando o reservatorio
    errado quando havia item invalido no meio.
    """
    r = rules.validar_reservacao([
        {"capacidade_l": 5000.0},
        {"capacidade_l": 0},
        {"capacidade_l": "n/d"},
        {"capacidade_l": 1000.0},
    ])

    titulos = [p.titulo for p in r if p.codigo == "RES-002"]
    assert len(titulos) == 2
    assert "reservatorio 2" in titulos[0]
    assert "reservatorio 3" in titulos[1]
    assert not any(p.codigo == "RES-001" for p in r)


def test_mensagem_de_submergencia_e_portuguesa_e_ascii():
    """EQP-020 misturava 'cavitation' (ingles) e 'sucção' com cedilha num
    codigo que escreve o resto das mensagens sem acento."""
    r = rules.avaliar_motobomba_vs_poco({"profundidade_instalacao_m": 12.0},
                                        None, 8.0, None)

    p = next(p for p in r if p.codigo == "EQP-020")

    assert p.mensagem.isascii()
    assert "cavitation" not in p.mensagem
    assert "cavitacao" in p.mensagem
