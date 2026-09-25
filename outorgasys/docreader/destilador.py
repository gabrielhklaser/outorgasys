# -*- coding: utf-8 -*-
"""
Destilador Documental GabeBrain (Uma Leitura, Quatro Saidas).

Converte o documento analisado por Docling/PyMuPDF em uma Nota Destilada
estruturada no padrao da skill `biblioteca-triagem` do GabeBrain:
1. Tipo Documental (A/L/T/N/M/S/R/C/D)
2. Autoria / Emissor / Ano validados
3. Nivel de Confianca da Fonte (A a E) com justificativa formal
4. Nota destilada com achados tecnicos e citacao exata de pagina.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .engine import DocumentoProcessado
from .water_quality import extrair_qualidade_agua


def extrair_metadados_gerais(doc: DocumentoProcessado) -> Dict[str, Any]:
    """Extrai entidades e metadados cadastrais gerais do texto."""
    texto = doc.texto_completo
    dados: Dict[str, Any] = {}

    import re

    # Proprietario / Requerente
    m_prop = re.search(r"(?:propriet[aá]rio|interessado|requerente|titular)[\s:]+([^\n\r,]+)", texto, re.IGNORECASE)
    if m_prop:
        dados["proprietario"] = m_prop.group(1).strip()

    # CPF / CNPJ
    m_cnpj = re.search(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", texto)
    if m_cnpj:
        dados["cnpj"] = m_cnpj.group(0)
    else:
        m_cpf = re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", texto)
        if m_cpf:
            dados["cpf"] = m_cpf.group(0)

    # Matricula / Registro
    m_mat = re.search(r"(?:matr[ií]cula|registro)[\s:]+(?:n[oº\.]*)?([0-9\.]+)", texto, re.IGNORECASE)
    if m_mat:
        dados["matricula"] = m_mat.group(1).strip()

    # Endereco / Localizacao
    m_end = re.search(r"endere[cç]o[\s:]+([^\n\r]+)", texto, re.IGNORECASE)
    if m_end:
        dados["endereco"] = m_end.group(1).strip()

    # Area
    m_area = re.search(r"[aá]rea[\s:]+([0-9,.]+)\s*(?:ha|hectares|m2|m²)", texto, re.IGNORECASE)
    if m_area:
        dados["area"] = m_area.group(1).strip()

    # ART / CREA
    m_art = re.search(r"\bART[\s:]+(?:n[oº\.]*)?([0-9\.-]+)", texto, re.IGNORECASE)
    if m_art:
        dados["art"] = m_art.group(1).strip()

    return dados


def gerar_nota_destilada(doc: DocumentoProcessado) -> str:
    """Gera a Nota Destilada GabeBrain em Markdown."""
    hoje = datetime.date.today().isoformat()
    meta = extrair_metadados_gerais(doc)
    qualidade = extrair_qualidade_agua(doc)

    achados_linhas = []

    if qualidade["parametros"]:
        achados_linhas.append(f"### Resultados Analiticos de Potabilidade (Portaria GM/MS 888/2021)")
        for p in qualidade["parametros"]:
            status_emoji = "✅" if p["status"] == "conforme" else "❌"
            achados_linhas.append(
                f"- {status_emoji} **{p['parametro']}:** `{p['resultado']}` (VMP: `{p['vmp']}`) — p. {p['pagina']} [{p['status'].upper()}]"
            )

    if meta.get("matricula"):
        achados_linhas.append(f"- **Matricula Imobiliaria:** n. {meta['matricula']} — p. 1")
    if meta.get("proprietario"):
        achados_linhas.append(f"- **Titular / Proprietario Declarado:** {meta['proprietario']} — p. 1")
    if meta.get("area"):
        achados_linhas.append(f"- **Area Superficial Registrada:** {meta['area']} — p. 1")
    if meta.get("art"):
        achados_linhas.append(f"- **Anotacao de Responsabilidade Tecnica (ART):** {meta['art']} — p. 1")

    achados_md = "\n".join(achados_linhas) if achados_linhas else "- Nenhum parametro quantitativo especifico identificado no texto, p. 1"

    md = f"""---
title: {doc.nome} (Destilacao GabeBrain)
tipo: {doc.tipo_estimado}
rotulo_tipo: {doc.rotulo_tipo}
confianca_fonte: {doc.confianca_fonte}
justificativa_fonte: {doc.justificativa_fonte}
processado_em: {hoje}
paginas: {doc.num_paginas}
---

# Destilacao Documental GabeBrain · {doc.nome}

**Tipo Documental:** `{doc.tipo_estimado}` — {doc.rotulo_tipo}  
**Nivel de Confianca da Fonte:** `{doc.confianca_fonte}` ({doc.justificativa_fonte})  
**Extensao:** {doc.num_paginas} pagina(s) analisadas via Docling / PyMuPDF  

---

## 📌 Escopo e Objeto do Documento
O presente documento foi submetido ao processo de outorga do SIOUT RS e triado automaticamente pelo leitor estruturado GabeBrain.

## 🔬 Principais Achados Tecnicos (com citacao de pagina)
{achados_md}

## ⚖️ Conformidade Normativa e Evidencias
- **Conformidade Geral de Potabilidade:** {'CONFORME' if qualidade['conforme_potabilidade'] else 'PENDENTE / INCONFORME'}
- **Total de Parametros Avaliados:** {qualidade['total_parametros_lidos']}
- **Citacao e Rastreabilidade:** Todos os dados foram extraidos diretamente do documento original anexado ao processo.
"""
    return md
