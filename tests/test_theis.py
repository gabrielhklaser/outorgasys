# -*- coding: utf-8 -*-
"""Testes unitarios da memoria de calculo do Agente 3 (pytest ou execucao direta)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from outorgasys.hydro import theis  # noqa: E402


def test_q_estavel_patamar_terminal():
    tempo = list(range(0, 1440, 60))
    vazao = [15.0, 14.0, 13.0] + [12.0] * (len(tempo) - 3)
    est = theis.identificar_q_estavel(tempo, vazao)
    assert est.q_estavel is not None
    assert abs(est.q_estavel - 12.0) < 0.5


def test_q_estavel_sem_dados():
    est = theis.identificar_q_estavel([], [])
    assert est.q_estavel is None


def test_reta_recuperacao_recupera_inclinacao():
    razao = [2, 5, 10, 50, 100]
    s = [3.0 - 0.5 * math.log10(x) for x in razao]
    reta = theis.ajustar_reta_recuperacao(razao, s)
    assert abs(reta.delta_s_linha - 0.5) < 1e-6
    assert reta.r2 is not None and reta.r2 > 0.999


def test_calcular_transmissividade_cooper_jacob():
    tempo = list(range(0, 1441, 60))
    vazao = [12.0] * len(tempo)
    t_linha = [10, 30, 60, 120, 240]
    t_total = 1440.0
    s_res = [0.5 * math.log10((t_total + t) / t) for t in t_linha]
    res = theis.calcular(ne=10.0, nd_final=13.0, tempo_min=tempo, vazao_m3h=vazao,
                         t_linha_min=t_linha, s_residual_m=s_res,
                         tempo_bombeamento_total_min=t_total)
    assert res.ok
    assert abs(res.T_m2h - 0.183 * 12.0 / 0.5) < 1e-6
    assert abs(res.Q_ot - res.T_m2h * 0.8 * 3.0) < 1e-6


def test_recuperacao_com_tempo_invalido_nao_desalinha():
    t_total = 1440.0
    t_linha = [float("nan"), 10, 30, 60, 120, 240]
    s_res = [99.0] + [0.5 * math.log10((t_total + t) / t) for t in t_linha[1:]]
    res = theis.calcular(ne=10.0, nd_final=13.0, tempo_min=[0, 60, 120, 180],
                         vazao_m3h=[12.0] * 4, t_linha_min=t_linha, s_residual_m=s_res,
                         tempo_bombeamento_total_min=t_total)
    assert abs(res.delta_s_linha - 0.5) < 1e-6


def test_nome_arquivo_seguro_bloqueia_traversal():
    from outorgasys.state import nome_arquivo_seguro
    assert nome_arquivo_seguro("..\\..\\x.py") == "x.py"
    assert nome_arquivo_seguro("/etc/passwd") == "passwd"
    assert nome_arquivo_seguro("ensaio.xlsx") == "ensaio.xlsx"


def test_calcular_nd_acima_de_ne_gera_erro():
    res = theis.calcular(ne=10.0, nd_final=9.0)
    assert not res.ok
    assert any("nao positivo" in e for e in res.erros)


if __name__ == "__main__":
    for nome, fn in list(globals().items()):
        if nome.startswith("test_") and callable(fn):
            fn()
            print(f"[OK] {nome}")
