# -*- coding: utf-8 -*-
"""Pacote de leitura, triagem e destilacao documental do OutorgaSys (Docling + GabeBrain)."""

from .engine import DocumentoProcessado, processar_documento
from .water_quality import extrair_qualidade_agua, LIMITES_POTABILIDADE
from .destilador import gerar_nota_destilada, extrair_metadados_gerais

__all__ = [
    "DocumentoProcessado",
    "processar_documento",
    "extrair_qualidade_agua",
    "LIMITES_POTABILIDADE",
    "gerar_nota_destilada",
    "extrair_metadados_gerais",
]
