# -*- coding: utf-8 -*-
"""Texto livre no laudo em PDF nao pode ser lido como marcacao do ReportLab.

``Paragraph`` interpreta ``<b>``, ``<a>`` e ``<img src=...>``. Antes, um campo
com ``<Sul>`` perdia o trecho e ``<img src="caminho">`` embutia no PDF um
arquivo qualquer do servidor.
"""

from __future__ import annotations

import pytest
from pypdf import PdfReader

from outorgasys import config as C
from outorgasys.report import laudo, pdf
from outorgasys.state import Processo

MAPA = (C.ROOT / "data" / "processos" / C.PROCESSO_EXEMPLO / "mapas"
        / "mapa_situacao.jpg")


def _gera(tmp_path, nome: str) -> PdfReader:
    p = Processo(pid="T-PDF-001", carregar=False)
    p["requerente"] = {"nome": nome}
    destino = tmp_path / "laudo.pdf"
    pdf.gerar_pdf(laudo.montar_estrutura(p), destino)
    return PdfReader(str(destino))


def _texto(r: PdfReader) -> str:
    return "\n".join(pg.extract_text() for pg in r.pages)


def test_dado_escapa_marcacao_depois_de_converter_simbolos():
    assert pdf._dado("<b>x</b> & y") == "&lt;b&gt;x&lt;/b&gt; &amp; y"
    # "≤" vira "<=" no _sanitize; o escape tem de vir depois.
    assert pdf._dado("Q ≤ 5") == "Q &lt;= 5"


def test_sinais_de_marcacao_saem_literais_no_laudo(dados_tmp):
    r = _gera(dados_tmp, "Empresa <Sul> S/A & Cia")
    assert "Empresa <Sul> S/A & Cia" in _texto(r)


@pytest.mark.skipif(not MAPA.exists(), reason="mapa de exemplo ausente")
def test_tag_img_no_texto_nao_embute_arquivo_do_servidor(dados_tmp):
    r = _gera(dados_tmp, f'<img src="{MAPA}" width="200" height="120"/>')
    assert sum(len(pg.images) for pg in r.pages) == 0
    assert "<img" in _texto(r)  # aparece como texto, nao como imagem
