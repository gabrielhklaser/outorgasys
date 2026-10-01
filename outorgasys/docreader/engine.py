# -*- coding: utf-8 -*-
"""
Motor de Leitura e Triagem Documental (Docling + GabeBrain).

Combina o poder de analise estrutural e extracao de tabelas do IBM Docling com
a velocidade e precisao de extracao do PyMuPDF, seguindo as diretrizes dos agentes
treinados do GabeBrain (skill biblioteca-triagem: 'uma leitura, quatro saidas').
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# PyMuPDF e opcional (licenca AGPL, nao esta no requirements.txt). Quando ausente,
# a leitura de texto usa pypdf, que ja e dependencia do projeto.
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

_DOCLING_AVAILABLE = False
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    _DOCLING_AVAILABLE = True
except ImportError:
    _DOCLING_AVAILABLE = False


@dataclass
class TabelaExtraida:
    """Tabela identificada em uma pagina de documento."""
    pagina: int
    cabecalhos: List[str]
    linhas: List[List[str]]
    dados_dict: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class DocumentoProcessado:
    """Resultado unificado da leitura estruturada ('uma leitura, quatro saidas')."""
    caminho: Path
    nome: str
    num_paginas: int
    tipo_estimado: str          # A, L, T, N, M, S, R, C, D (GabeBrain)
    rotulo_tipo: str
    confianca_fonte: str        # A, B, C, D, E (GabeBrain)
    justificativa_fonte: str
    texto_completo: str
    markdown: str
    paginas: List[str]
    tabelas: List[TabelaExtraida]
    metadados_brutos: Dict[str, Any] = field(default_factory=dict)
    achados_tecnicos: List[Dict[str, Any]] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)


def classificar_tipologia(texto: str) -> tuple[str, str, str, str]:
    """Classifica a tipologia do documento segundo o padrao da biblioteca-triagem do GabeBrain:
    Retorna: (codigo_tipo, rotulo_tipo, confianca_fonte, justificativa)
    """
    t_lower = texto.lower()

    if "laudo" in t_lower and ("analise" in t_lower or "laboratorial" in t_lower or "ensaio" in t_lower or "potabilidade" in t_lower):
        return ("R", "Relatorio Tecnico / Laudo Laboratorial", "A", "Laudo laboratorial analitico com parametros quantitativos e referencia normativa formal")
    if "matricula" in t_lower or "registro de imoveis" in t_lower or "certidao de inteiro teor" in t_lower:
        return ("D", "Documento Notarial / Certidao de Registro de Imoveis", "A", "Certidao notarial oficial dotada de fe publica")
    if "anotacao de responsabilidade tecnica" in t_lower or "art" in t_lower and "crea" in t_lower:
        return ("D", "Anotacao de Responsabilidade Tecnica (ART / CREA)", "A", "Atestado oficial de responsabilidade tecnica registrado em conselho de classe")
    if "portaria" in t_lower or "abnt" in t_lower or "nbr" in t_lower or "resolucao" in t_lower:
        return ("N", "Norma Tecnica / Regulamento Legal", "A", "Norma tecnica oficial ou resolucao estatal dotada de forca de lei")
    if "declaracao" in t_lower and "redes" in t_lower:
        return ("D", "Declaracao Administrativa de Separacao de Redes", "B", "Declaracao formal assinada pelo titular e responsavel com responsabilidade civil e penal")

    return ("R", "Documento Tecnico / Administrativo", "C", "Documento tecnico apresentado no processo de licenciamento/outorga")


def _ler_paginas(p: Path) -> tuple[List[str], Dict[str, Any]]:
    """Texto por pagina e metadados do PDF, com PyMuPDF ou pypdf."""
    if fitz is not None:
        with fitz.open(str(p)) as doc:
            return [pg.get_text() for pg in doc], dict(doc.metadata or {})

    from pypdf import PdfReader  # noqa: PLC0415

    leitor = PdfReader(str(p))
    meta = {str(k).lstrip("/").lower(): str(v) for k, v in (leitor.metadata or {}).items()}
    # O modo layout mantem cada linha de tabela numa linha de texto, com as
    # colunas separadas por varios espacos; o modo padrao quebra celula a celula.
    return [(pg.extract_text(extraction_mode="layout") or "") for pg in leitor.pages], meta


def processar_documento(caminho: str | Path, usar_docling: bool = True) -> DocumentoProcessado:
    """Executa a leitura economica e estruturada do documento."""
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {p}")

    texto_completo = ""
    paginas: List[str] = []
    tabelas: List[TabelaExtraida] = []
    avisos: List[str] = []
    markdown = ""
    meta_brutos: Dict[str, Any] = {}

    # 1. Leitura rapida (PyMuPDF se instalado, senao pypdf) de texto e metadados
    paginas, meta_brutos = _ler_paginas(p)
    num_paginas = len(paginas)
    for num_p, txt_pag in enumerate(paginas, 1):
        texto_completo += f"\n--- Pagina {num_p} ---\n" + txt_pag

    # 2. Leitura profunda com Docling se disponivel (para extracao de tabelas e markdown estruturado)
    if usar_docling and _DOCLING_AVAILABLE and p.suffix.lower() == ".pdf":
        try:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False
            pipeline_options.do_table_structure = True

            converter = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
            )
            conv_res = converter.convert(str(p))
            docling_doc = conv_res.document
            markdown = docling_doc.export_to_markdown()

            # Extrai tabelas do docling
            if hasattr(docling_doc, "tables"):
                for idx, t in enumerate(docling_doc.tables, start=1):
                    try:
                        df = t.export_to_dataframe()
                        headers = [str(c) for c in df.columns]
                        rows = [[str(v) for v in row] for row in df.values]
                        records = df.to_dict(orient="records")
                        tabelas.append(TabelaExtraida(
                            pagina=getattr(t, "page_no", 1) or 1,
                            cabecalhos=headers,
                            linhas=rows,
                            dados_dict=[{str(k): str(v) for k, v in rec.items()} for rec in records]
                        ))
                    except Exception as exc:  # noqa: BLE001
                        # A tabela ilegivel nao invalida o resto da leitura, mas o
                        # numero perdido tem de aparecer para quem assina o laudo:
                        # era exatamente esse o parametro de potabilidade.
                        avisos.append(
                            f"Docling: falha ao extrair a tabela {idx} "
                            f"(pagina {getattr(t, 'page_no', '?') or '?'}): "
                            f"{type(exc).__name__}: {exc}.")
        except Exception as exc:  # noqa: BLE001
            # Cai para o texto do pypdf/PyMuPDF. A queda precisa ser visivel:
            # sem Docling nao ha tabela estruturada, so texto corrido.
            markdown = texto_completo
            avisos.append(
                f"Docling falhou neste arquivo ({type(exc).__name__}: {exc}); "
                "usada a extracao de texto simples, sem tabelas estruturadas.")
    else:
        markdown = texto_completo

    # 3. Classificacao GabeBrain
    c_tipo, rot_tipo, conf, just = classificar_tipologia(texto_completo)

    return DocumentoProcessado(
        caminho=p,
        nome=p.name,
        num_paginas=num_paginas,
        tipo_estimado=c_tipo,
        rotulo_tipo=rot_tipo,
        confianca_fonte=conf,
        justificativa_fonte=just,
        texto_completo=texto_completo,
        markdown=markdown,
        paginas=paginas,
        tabelas=tabelas,
        metadados_brutos=meta_brutos,
        avisos=avisos,
    )
