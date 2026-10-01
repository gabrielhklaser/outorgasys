# -*- coding: utf-8 -*-
"""Caminho completo: os seis agentes sobre o poco de exemplo de Campo Bom.

Roda scripts/semente_campo_bom.py num diretorio temporario (cerca de 15 s, sem
rede obrigatoria) e confere os numeros publicados no README. Qualquer mudanca em
calculo, regra ou relatorio que altere esses resultados aparece aqui.
"""

from __future__ import annotations

import pytest
from pypdf import PdfReader

from outorgasys import config as C

pytestmark = pytest.mark.skipif(
    not (C.ROOT / "data" / "vetoriais").exists(), reason="base vetorial ausente")


@pytest.fixture(scope="module")
def processo(tmp_path_factory):
    """Gera o exemplo uma vez para todos os testes do modulo."""
    base = tmp_path_factory.mktemp("pipeline")
    anterior = (C.PROCESSOS, C.SAIDA)
    C.PROCESSOS, C.SAIDA = base / "processos", base / "saida"
    C.PROCESSOS.mkdir()
    C.SAIDA.mkdir()
    try:
        from scripts.semente_campo_bom import construir

        yield construir(limpar=True)
    finally:
        C.PROCESSOS, C.SAIDA = anterior


def test_seis_agentes_concluidos(processo):
    assert processo.get("agentes_concluidos") == [1, 2, 3, 4, 5, 6]


def test_localizacao_e_hidrografia(processo):
    geo = processo["geoespacial"]
    assert geo["municipio"] == "Campo Bom"
    assert "Rio dos Sinos" in geo["bacia_hidrografica"]
    assert geo["corpo_hidrico_proximo"]["distancia_m"] == pytest.approx(358.95, abs=0.5)


def test_parametros_hidraulicos(processo):
    p = processo["hidrogeologia"]["parametros"]
    assert p["s_max_m"] == pytest.approx(2.872, abs=1e-3)
    assert p["q_estavel_m3h"] == pytest.approx(11.994, abs=1e-3)
    assert p["T_m2h"] == pytest.approx(5.979, abs=1e-3)
    assert p["Q_ot_m3h"] == pytest.approx(13.738, abs=1e-3)
    # contraprova de Jacob-Lohman = Theis exato (4*pi), nao a metade
    assert p["Q_jacob_lohman_m3h"] == pytest.approx(8.29, abs=0.02)


def test_quadro_de_vazao_fecha_e_usa_a_menor_vazao(processo):
    bal = processo["balanco"]
    assert bal["vazao_adotada"]["vazao"] == pytest.approx(11.994, abs=1e-3)
    assert bal["vazao_adotada"]["origem"] == "Q_estavel"
    quadro = bal["quadro"]
    assert len(quadro["linhas"]) == 12
    assert quadro["volume_anual_m3"] == round(
        sum(l["volume_m3_mes"] for l in quadro["linhas"]), 2) == 37521.84


def test_laudo_em_pdf_tem_mapas_e_graficos(processo):
    pdf = C.caminho_absoluto(processo["relatorio"]["pdf"])
    leitor = PdfReader(str(pdf))
    assert len(leitor.pages) >= 9
    assert sum(len(pg.images) for pg in leitor.pages) >= 4
    texto = "\n".join(pg.extract_text() for pg in leitor.pages)
    assert "Imagem nao encontrada" not in texto
    assert "Campo Bom" in texto


def test_caminhos_gravados_usam_barra_normal(processo):
    for rel in processo["geoespacial"]["caminho_mapas"]:
        assert "\\" not in rel
    assert "\\" not in processo["relatorio"]["markdown"]
