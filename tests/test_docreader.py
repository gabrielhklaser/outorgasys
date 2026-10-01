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


def test_nada_reconhecido_nao_vira_conforme():
    """Extracao vazia e verdade vacua: nao pode aparecer como CONFORME."""
    from outorgasys.docreader import extrair_qualidade_agua
    from outorgasys.docreader.engine import DocumentoProcessado

    doc = DocumentoProcessado(
        caminho=PDF_EXEMPLO, nome="vazio.pdf", num_paginas=1, tipo_estimado="R",
        rotulo_tipo="x", confianca_fonte="C", justificativa_fonte="x",
        texto_completo="Texto sem nenhum parametro de potabilidade.",
        markdown="", paginas=["x"], tabelas=[])

    q = extrair_qualidade_agua(doc)

    assert q["parametros"] == []
    assert q["conforme_potabilidade"] is None


# --------------------------------------------------------------------------------------
# Falhas do Docling nao podem ser engolidas em silencio
# --------------------------------------------------------------------------------------


class _TabelaQueFalha:
    page_no = 3

    def export_to_dataframe(self):
        raise ValueError("tabela corrompida")


class _DocumentoFake:
    tables = [_TabelaQueFalha()]

    def export_to_markdown(self) -> str:
        return "# Laudo de analise"


class _ConversorFake:
    """Docling de brinquedo: converte, mas quebra ao exportar a tabela."""

    def __init__(self, *args, **kwargs):
        pass

    def convert(self, caminho):
        class _Res:
            document = _DocumentoFake()

        return _Res()


class _ConversorQueFalha:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("modelo do Docling nao baixou")


@pytest.fixture
def engine_docling(monkeypatch, engine_sem_pymupdf):
    """Liga o caminho do Docling com classes de brinquedo injetadas no modulo."""
    import types

    engine = engine_sem_pymupdf
    monkeypatch.setattr(engine, "_DOCLING_AVAILABLE", True)
    monkeypatch.setattr(engine, "PdfPipelineOptions", types.SimpleNamespace,
                        raising=False)
    monkeypatch.setattr(engine, "InputFormat", types.SimpleNamespace(PDF="pdf"),
                        raising=False)
    monkeypatch.setattr(engine, "PdfFormatOption", lambda **kw: None, raising=False)
    return engine


def test_falha_na_tabela_do_docling_vira_aviso(engine_docling, monkeypatch):
    monkeypatch.setattr(engine_docling, "DocumentConverter", _ConversorFake,
                        raising=False)

    doc = engine_docling.processar_documento(PDF_EXEMPLO)

    assert doc.tabelas == []
    assert any("tabela" in a.lower() and "ValueError" in a for a in doc.avisos)


def test_falha_geral_do_docling_vira_aviso(engine_docling, monkeypatch):
    monkeypatch.setattr(engine_docling, "DocumentConverter", _ConversorQueFalha,
                        raising=False)

    doc = engine_docling.processar_documento(PDF_EXEMPLO)

    assert doc.markdown == doc.texto_completo
    assert any("Docling" in a and "RuntimeError" in a for a in doc.avisos)


def test_leitura_sem_docling_nao_produz_aviso_de_docling(engine_sem_pymupdf):
    doc = engine_sem_pymupdf.processar_documento(PDF_EXEMPLO)

    assert doc.avisos == []
