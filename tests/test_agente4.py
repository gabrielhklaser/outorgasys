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
