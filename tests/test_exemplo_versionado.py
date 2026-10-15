# -*- coding: utf-8 -*-
"""O exemplo versionado nao pode ficar desatualizado em relacao ao codigo.

O JSON de ``EX-CAMPOBOM-001`` e commitado para a aplicacao abrir com um caso
completo, mas isso cria um risco: corrigir a formula no codigo e esquecer de
regenerar o exemplo. Ate 2026-10-01 o exemplo trazia a contraprova de
Jacob-Lohman pela metade (4,14 m3/h, com 2pi) e um volume anual que nao fechava
com as linhas. Estes testes recomputam o valor esperado a partir dos proprios
parametros gravados e falham se o JSON ficar para tras.
"""

from __future__ import annotations

import json
import math

import pytest

from outorgasys import config as C

JSON_EXEMPLO = C.ROOT / "data" / "processos" / f"{C.PROCESSO_EXEMPLO}.json"

pytestmark = pytest.mark.skipif(not JSON_EXEMPLO.exists(),
                                reason="exemplo versionado ausente")


@pytest.fixture(scope="module")
def exemplo() -> dict:
    return json.loads(JSON_EXEMPLO.read_text(encoding="utf-8-sig"))


def jacob_lohman_4pi(T_m2h: float, s_max: float, raio: float) -> float:
    """Cooper-Jacob invertido com 4pi, premissas documentadas (S=1e-4, t=365d)."""
    T_dia = T_m2h * 24.0
    arg = (2.25 * T_dia * 365.0) / (raio * raio * 1e-4)
    assert arg > 1.0
    return (4 * math.pi * T_dia * s_max) / math.log(arg) / 24.0


def test_contraprova_jacob_lohman_usa_4pi(exemplo):
    """O valor gravado tem de bater com a formula de 4pi, nao a antiga de 2pi."""
    p = (exemplo["hidrogeologia"] or {}).get("parametros") or {}
    T, s_max = p.get("T_m2h"), p.get("s_max_m")
    raio = ((exemplo.get("poco") or {}).get("raio_m")) or 0.0762

    esperado = jacob_lohman_4pi(T, s_max, raio)
    gravado = p.get("Q_jacob_lohman_m3h")

    assert gravado == pytest.approx(esperado, rel=1e-6), (
        f"o exemplo grava {gravado}, mas a contraprova com 4pi da {esperado:.4f}; "
        "regenerar com scripts/semente_campo_bom.py --sem-mapas")
    # e explicitamente diferente do valor pela metade (2pi)
    assert abs(gravado - esperado / 2) > 0.5


def test_volume_anual_fecha_com_as_linhas(exemplo):
    linhas = (exemplo["balanco"]["quadro"] or {}).get("linhas") or []
    soma = round(sum(l["volume_m3_mes"] for l in linhas), 2)

    assert exemplo["balanco"]["quadro"]["volume_anual_m3"] == soma


def test_caminhos_gravados_usam_barra_normal(exemplo):
    """JSON gerado no Windows gravava 'data\\processos\\...'; ler no Linux quebra."""
    mapas = (exemplo["geoespacial"] or {}).get("caminho_mapas") or []

    assert mapas, "o exemplo deve guardar as pranchas cartograficas"
    for m in mapas:
        assert "\\" not in m, f"caminho com barra invertida: {m}"
        assert C.caminho_absoluto(m).exists(), f"prancha inexistente: {m}"


def test_laudo_em_pdf_existe_e_tem_tamanho_saudavel(exemplo):
    pdf = ((exemplo["relatorio"] or {}).get("pdf"))
    assert pdf
    caminho = C.caminho_absoluto(pdf)
    assert caminho.exists() and caminho.stat().st_size > 100_000
