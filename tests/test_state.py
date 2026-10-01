# -*- coding: utf-8 -*-
"""Persistencia do processo: ciclo salvar/carregar, uploads e identificadores."""

from __future__ import annotations

import pandas as pd

from outorgasys.state import Processo


def test_dataframe_sobrevive_ao_ciclo_salvar_e_carregar(dados_tmp):
    p = Processo(pid="T-RT-001", carregar=False)
    p["ensaio"] = {
        "ok": True,
        "bombeamento": pd.DataFrame({"t_min": [1.0, 2.0], "nd_m": [9.7, 9.8]}),
        "recuperacao": pd.DataFrame({"t_linha_min": [5.0], "s_linha_m": [0.4]}),
    }
    p.salvar()

    ensaio = Processo.carregar("T-RT-001")["ensaio"]

    assert isinstance(ensaio["bombeamento"], pd.DataFrame)
    assert list(ensaio["bombeamento"]["t_min"]) == [1.0, 2.0]
    assert list(ensaio["recuperacao"].columns) == ["t_linha_min", "s_linha_m"]


def test_serie_sobrevive_ao_ciclo_salvar_e_carregar(dados_tmp):
    p = Processo(pid="T-RT-002", carregar=False)
    p["valores"] = pd.Series([1.5, 2.5, 3.5])
    p.salvar()

    de_volta = Processo.carregar("T-RT-002")["valores"]

    assert isinstance(de_volta, pd.Series)
    assert list(de_volta) == [1.5, 2.5, 3.5]
