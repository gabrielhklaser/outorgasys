# -*- coding: utf-8 -*-
"""Leitura de laudos em PDF sem PyMuPDF/Docling (ambiente do Render)."""

from __future__ import annotations

import pytest

from outorgasys import config as C

PDF_EXEMPLO = (C.ROOT / "data" / "processos" / C.PROCESSO_EXEMPLO / "arquivos"
               / "analise_laboratorial_exemplo.pdf")

pytestmark = pytest.mark.skipif(not PDF_EXEMPLO.exists(),
                                reason="PDF de exemplo ausente")


@pytest.fixture
def engine_sem_pymupdf(monkeypatch):
    """Simula o ambiente de producao: so pypdf, sem PyMuPDF nem Docling."""
    from outorgasys.docreader import engine

    monkeypatch.setattr(engine, "fitz", None)
    monkeypatch.setattr(engine, "_DOCLING_AVAILABLE", False)
    return engine


def test_processar_documento_funciona_sem_pymupdf(engine_sem_pymupdf):
    doc = engine_sem_pymupdf.processar_documento(PDF_EXEMPLO)

    assert doc.num_paginas == 1
    assert "Coliformes totais" in doc.texto_completo
    assert doc.metadados_brutos.get("producer", "").startswith("ReportLab")


def test_extrai_parametros_do_laudo_so_com_pypdf(engine_sem_pymupdf):
    from outorgasys.docreader import extrair_qualidade_agua

    doc = engine_sem_pymupdf.processar_documento(PDF_EXEMPLO)
    q = extrair_qualidade_agua(doc)

    por_chave = {p["chave"]: p for p in q["parametros"]}
    esperados = {"coliformes_totais", "escherichia_coli", "turbidez", "cor_aparente",
                 "ph", "fluoreto", "nitrato", "cloreto", "sulfato", "dureza",
                 "ferro", "manganes"}
    assert esperados <= set(por_chave)
    assert por_chave["dureza"]["resultado"].startswith("86")
    assert por_chave["turbidez"]["resultado"].startswith("0,42")
    assert all(p["status"] == "conforme" for p in q["parametros"])
    assert q["conforme_potabilidade"] is True
