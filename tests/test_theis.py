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


def _ensaio_sintetico(q=12.0, delta=0.5, ne=10.0, nd=13.0, t_total=1440.0):
    tempo = list(range(0, int(t_total) + 1, 60))
    t_linha = [10, 30, 60, 120, 240]
    s_res = [delta * math.log10((t_total + x) / x) for x in t_linha]
    return theis.calcular(ne=ne, nd_final=nd, tempo_min=tempo, vazao_m3h=[q] * len(tempo),
                          t_linha_min=t_linha, s_residual_m=s_res,
                          tempo_bombeamento_total_min=t_total)


def test_contraprova_jacob_lohman_coincide_com_theis_exato():
    """Q = 4*pi*T*s / W(u), com W a funcao de poco de Theis (referencia independente).

    A aproximacao de Cooper-Jacob, s = Q/(4*pi*T) * ln(2,25*T*t/(r2*S)), vale para
    u pequeno; aqui u e da ordem de 1e-11. O codigo usava 2*pi e saia pela metade.
    """
    from scipy.special import exp1

    res = _ensaio_sintetico()
    T_dia = res.T_m2h * 24.0
    r, S, t_dias = 0.10, 1e-4, 365.0
    u = r * r * S / (4.0 * T_dia * t_dias)
    esperado_m3h = 4.0 * math.pi * T_dia * res.s_max / exp1(u) / 24.0

    assert abs(res.Q_jacob_lohman - esperado_m3h) / esperado_m3h < 1e-3


def test_premissas_da_contraprova_aparecem_na_tabela_de_memoria():
    from outorgasys.agents import agente3_hidro as a3

    res = _ensaio_sintetico()
    linhas = a3.tabela_memoria({"parametros": {"Q_jacob_lohman_m3h": res.Q_jacob_lohman},
                                "memoria": res.to_dict()})
    criterio = next(l["criterio"] for l in linhas if "Jacob-Lohman" in l["parametro"])

    assert "4π" in criterio
    assert "premissas adotadas" in criterio
    assert "S = 0.0001" in criterio and "t = 365 d" in criterio and "r = 0.1 m" in criterio


def test_arr_tolera_texto_nulo_e_na_do_pandas():
    import pandas as pd

    a = theis._arr(["1", "x", None, float("nan"), 2, pd.NA])

    assert [None if math.isnan(v) else v for v in a] == [1.0, None, None, None, 2.0, None]


def _janela_maxima_referencia(q, tol=0.10, fracao=0.25):
    """Maior janela terminal (>= max(3, 25% de n)) com CV <= tol; None se nao houver."""
    n = len(q)
    minimo = max(3, math.ceil(fracao * n))
    for i in range(n, minimo - 1, -1):
        janela = q[n - i:]
        media = sum(janela) / i
        if abs(media) < 1e-12:
            continue
        desvio = (sum((x - media) ** 2 for x in janela) / i) ** 0.5
        if desvio / abs(media) <= tol:
            return i, media
    return None


def test_q_estavel_adota_a_maior_janela_terminal_com_cv_aceitavel():
    """Equivale a procurar, de n para o minimo, a primeira janela com CV <= 10%."""
    import random

    rng = random.Random(20260930)
    for _ in range(300):
        n = rng.randint(3, 40)
        rampa = rng.randint(0, n // 2)
        base = rng.uniform(2.0, 20.0)
        q = [base * (1.0 + rng.uniform(0.1, 0.8)) for _ in range(rampa)]
        q += [base * (1.0 + rng.uniform(-0.04, 0.04)) for _ in range(n - rampa)]
        est = theis.identificar_q_estavel(list(range(n)), q)
        ref = _janela_maxima_referencia(q)
        if ref is None:
            assert "ultimo terco" in est.metodo
        else:
            assert est.n_pontos == ref[0]
            assert abs(est.q_estavel - ref[1]) < 1e-9


if __name__ == "__main__":
    for nome, fn in list(globals().items()):
        if nome.startswith("test_") and callable(fn):
            fn()
            print(f"[OK] {nome}")


def test_reta_recuperacao_respeita_o_metodo_pedido():
    """O parametro ``metodo`` existia mas era ignorado: sempre saia Theil-Sen."""
    razao = [2, 5, 10, 50, 100]
    s = [3.0 - 0.5 * math.log10(x) for x in razao]

    r = theis.ajustar_reta_recuperacao(razao, s, metodo="minimos-quadrados")

    assert "minimos quadrados" in r.metodo.lower()
    assert abs(r.delta_s_linha - 0.5) < 1e-6


def test_reta_recuperacao_padrao_continua_sendo_theil_sen():
    razao = [2, 5, 10, 50, 100]
    s = [3.0 - 0.5 * math.log10(x) for x in razao]

    assert "theil-sen" in theis.ajustar_reta_recuperacao(razao, s).metodo.lower()


def test_reta_recuperacao_avisa_a_queda_para_minimos_quadrados(monkeypatch):
    """Sem scipy o ajuste cai para minimos quadrados; o laudo precisa dizer."""
    import scipy.stats as st

    def _quebra(*args, **kwargs):  # noqa: ANN001
        raise RuntimeError("scipy indisponivel")

    monkeypatch.setattr(st, "theilslopes", _quebra)

    razao = [2, 5, 10, 50, 100]
    s = [3.0 - 0.5 * math.log10(x) for x in razao]
    r = theis.ajustar_reta_recuperacao(razao, s)

    assert "minimos quadrados" in r.metodo.lower()
    assert "theil-sen" in r.observacao.lower()
    assert "RuntimeError" in r.observacao


def test_reta_recuperacao_com_metodo_desconhecido_avisa(monkeypatch):
    razao = [2, 5, 10, 50, 100]
    s = [3.0 - 0.5 * math.log10(x) for x in razao]

    r = theis.ajustar_reta_recuperacao(razao, s, metodo="wavelets")

    assert "wavelets" in r.observacao
    assert "theil-sen" in r.metodo.lower()
