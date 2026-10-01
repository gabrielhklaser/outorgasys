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
