# -*- coding: utf-8 -*-
"""
Extracao e Validacao de Laudo de Qualidade da Agua (Portaria GM/MS n. 888/2021).

Extrai tabelas de parametros fisico-quimicos e microbiologicos de laudos
analiticos laboratoriais via Docling/PyMuPDF e audita a conformidade com os
Padroes de Potabilidade brasileiros (Anexo 1 e Anexo 10 da Portaria 888/2021).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from .engine import DocumentoProcessado

# Limites da Portaria GM/MS n. 888/2021
LIMITES_POTABILIDADE = {
    "coliformes_totais": {"rotulo": "Coliformes Totais", "vmp": "Ausencia em 100 mL", "tipo": "microbio"},
    "escherichia_coli": {"rotulo": "Escherichia coli", "vmp": "Ausencia em 100 mL", "tipo": "microbio"},
    "turbidez": {"rotulo": "Turbidez", "vmp": 5.0, "unidade": "uT", "tipo": "max"},
    "cor_aparente": {"rotulo": "Cor Aparente", "vmp": 15.0, "unidade": "uH", "tipo": "max"},
    "ph": {"rotulo": "pH", "min": 6.0, "max": 9.5, "unidade": "-", "tipo": "faixa"},
    "cloro_residual": {"rotulo": "Cloro Residual Livre", "min": 0.2, "max": 5.0, "unidade": "mg/L", "tipo": "faixa_opcional"},
    "fluoreto": {"rotulo": "Fluoreto", "vmp": 1.5, "unidade": "mg/L", "tipo": "max"},
    "nitrato": {"rotulo": "Nitrato (como N)", "vmp": 10.0, "unidade": "mg/L", "tipo": "max"},
    "cloreto": {"rotulo": "Cloreto", "vmp": 250.0, "unidade": "mg/L", "tipo": "max"},
    "sulfato": {"rotulo": "Sulfato", "vmp": 250.0, "unidade": "mg/L", "tipo": "max"},
    "dureza": {"rotulo": "Dureza Total", "vmp": 500.0, "unidade": "mg/L", "tipo": "max"},
    "ferro": {"rotulo": "Ferro Total", "vmp": 0.3, "unidade": "mg/L", "tipo": "max"},
    "manganes": {"rotulo": "Manganes", "vmp": 0.1, "unidade": "mg/L", "tipo": "max"},
}


def _converter_valor(val_str: str) -> Optional[float]:
    """Converte representacoes textuais de resultados ('< 5,0', '0,42 uT') para float."""
    s = val_str.replace("mg/L", "").replace("uT", "").replace("uH", "").replace("NTU", "").strip()
    s = s.replace("<", "").replace(">", "").replace("≤", "").replace("≥", "").strip()
    s = s.replace(",", ".")
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def extrair_qualidade_agua(doc: DocumentoProcessado) -> Dict[str, Any]:
    """Processa o documento e extrai parametros laboratoriais e status de conformidade."""
    parametros_encontrados: Dict[str, Dict[str, Any]] = {}
    texto = doc.markdown if doc.markdown else doc.texto_completo

    # 1. Varredura atraves das tabelas estruturadas extraidas pelo Docling
    for tab in doc.tabelas:
        for item in tab.dados_dict:
            # Encontra colunas relevantes
            param_key = None
            resultado_val = None

            for k, v in item.items():
                k_lower = k.lower()
                if "parametro" in k_lower or "analise" in k_lower or "ensaio" in k_lower or "descricao" in k_lower:
                    param_key = v
                elif "resultado" in k_lower or "valor" in k_lower or "obtido" in k_lower:
                    resultado_val = v

            if param_key and resultado_val:
                p_norm = param_key.lower().strip()
                for chave_padrao, meta in LIMITES_POTABILIDADE.items():
                    nome_padrao = meta["rotulo"].lower()
                    if chave_padrao in p_norm or nome_padrao in p_norm or p_norm in nome_padrao:
                        parametros_encontrados[chave_padrao] = {
                            "parametro": meta["rotulo"],
                            "resultado_bruto": resultado_val,
                            "valor_num": _converter_valor(resultado_val),
                            "pagina": tab.pagina,
                            "fonte": "tabela_docling",
                        }

    # 2. Se a tabela nao pegou tudo, varre o texto bruto por regex
    linhas = texto.splitlines()
    for linha in linhas:
        l_lower = linha.lower()
        for chave_padrao, meta in LIMITES_POTABILIDADE.items():
            if chave_padrao in parametros_encontrados:
                continue
            nome_padrao = meta["rotulo"].lower()
            if nome_padrao in l_lower or chave_padrao in l_lower:
                m_val = re.search(r"[:\|]\s*([<>]?\s*[\d,.]+(?:\s*(?:mg/L|uT|uH|NTU))?|aus[eê]ncia[^\n|]*)", linha, re.IGNORECASE)
                if m_val:
                    res_raw = m_val.group(1).strip()
                    parametros_encontrados[chave_padrao] = {
                        "parametro": meta["rotulo"],
                        "resultado_bruto": res_raw,
                        "valor_num": _converter_valor(res_raw),
                        "pagina": 1,
                        "fonte": "texto_regex",
                    }

    # 3. Auditoria de conformidade com a Portaria GM/MS n. 888/2021
    relatorio_conformidade = []
    conforme_geral = True

    for ch, meta in LIMITES_POTABILIDADE.items():
        achado = parametros_encontrados.get(ch)
        if not achado:
            continue

        raw = achado["resultado_bruto"].strip()
        num = achado["valor_num"]
        tipo = meta["tipo"]
        status = "conforme"
        motivo = "Em conformidade com a Portaria 888/2021"

        if tipo == "microbio":
            if "aus" not in raw.lower() and (num is not None and num > 0):
                status = "nao_conforme"
                motivo = "Presenca detectada (exige ausencia)"
                conforme_geral = False
        elif tipo == "max" and num is not None:
            if num > meta["vmp"]:
                status = "nao_conforme"
                motivo = f"Valor {num:g} excede o VMP de {meta['vmp']:g} {meta.get('unidade', '')}"
                conforme_geral = False
        elif tipo == "faixa" and num is not None:
            if num < meta["min"] or num > meta["max"]:
                status = "nao_conforme"
                motivo = f"Valor {num:g} fora da faixa recomendada ({meta['min']} a {meta['max']})"
                conforme_geral = False

        relatorio_conformidade.append({
            "chave": ch,
            "parametro": meta["rotulo"],
            "resultado": raw,
            "vmp": meta.get("vmp") or f"{meta.get('min')} a {meta.get('max')}",
            "unidade": meta.get("unidade", ""),
            "status": status,
            "motivo": motivo,
            "pagina": achado["pagina"],
        })

    return {
        "arquivo": doc.nome,
        "conforme_potabilidade": conforme_geral,
        "parametros": relatorio_conformidade,
        "total_parametros_lidos": len(relatorio_conformidade),
    }
