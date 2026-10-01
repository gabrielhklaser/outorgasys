# -*- coding: utf-8 -*-
"""Imagens do laudo em PDF: caminhos gravados no Windows tambem precisam valer."""

from __future__ import annotations

import pytest
from pypdf import PdfReader

from outorgasys import config as C
from outorgasys.report import laudo, pdf
from outorgasys.state import Processo

MAPA = (C.ROOT / "data" / "processos" / C.PROCESSO_EXEMPLO / "mapas"
        / "mapa_situacao.jpg")


@pytest.mark.skipif(not MAPA.exists(), reason="mapa de exemplo ausente")
def test_imagem_com_caminho_windows_entra_no_pdf(dados_tmp):
    estrutura = laudo.montar_estrutura(Processo(pid="T-PDF-002", carregar=False))
    estrutura["anexos"]["mapas"] = [
        f"data\\processos\\{C.PROCESSO_EXEMPLO}\\mapas\\mapa_situacao.jpg"]
    destino = dados_tmp / "laudo.pdf"

    pdf.gerar_pdf(estrutura, destino)

    r = PdfReader(str(destino))
    assert sum(len(pg.images) for pg in r.pages) == 1
    assert "Imagem nao encontrada" not in "\n".join(pg.extract_text() for pg in r.pages)
