# -*- coding: utf-8 -*-
"""Limites de potabilidade e leitura de resultados de laudo.

Fonte dos valores: Portaria GM/MS n. 888/2021, publicada em
https://bvsms.saude.gov.br/bvs/saudelegis/gm/2021/prt0888_07_05_2021.html
(Anexo 9: substancias quimicas que representam risco a saude; Anexo 11: padrao
organoleptico).
"""

from __future__ import annotations

from outorgasys import config as C
from outorgasys.docreader import extrair_qualidade_agua
from outorgasys.docreader.engine import DocumentoProcessado
from outorgasys.docreader.water_quality import LIMITES_POTABILIDADE


def _doc(linhas: list[str]) -> DocumentoProcessado:
    texto = "\n".join(linhas)
    return DocumentoProcessado(
        caminho=C.ROOT, nome="laudo.pdf", num_paginas=1, tipo_estimado="R",
        rotulo_tipo="Laudo", confianca_fonte="A", justificativa_fonte="teste",
        texto_completo=texto, markdown=texto, paginas=[texto], tabelas=[])


def _status(doc: DocumentoProcessado, chave: str) -> str:
    q = extrair_qualidade_agua(doc)
    achados = {p["chave"]: p for p in q["parametros"]}
    assert chave in achados, f"{chave} nao reconhecido: {sorted(achados)}"
    return achados[chave]["status"]


# --- limites ----------------------------------------------------------------


def test_limites_de_config_seguem_a_portaria_888():
    lim = {k: v[3] for k, v in C.PARAMETROS_POTABILIDADE.items()}
    assert lim["cadmio"] == 0.003                    # Anexo 9
    assert lim["dureza_total"] == 300.0              # Anexo 11
    assert lim["solidos_dissolvidos_totais"] == 500.0  # Anexo 11


def test_tabelas_de_limites_nao_divergem():
    """config e water_quality mantem a mesma lista de VMP para os parametros comuns."""
    equivalentes = {
        "turbidez": "turbidez", "cor_aparente": "cor_aparente", "fluoreto": "fluor",
        "nitrato": "nitrato", "cloreto": "cloreto", "sulfato": "sulfato",
        "dureza": "dureza_total", "ferro": "ferro", "manganes": "manganes",
    }
    for chave_wq, chave_cfg in equivalentes.items():
        assert LIMITES_POTABILIDADE[chave_wq]["vmp"] == C.PARAMETROS_POTABILIDADE[chave_cfg][3], \
            f"VMP de {chave_wq} diverge entre water_quality e config"


def test_dureza_acima_de_300_e_nao_conforme():
    doc = _doc(["Dureza total      350 mg/L CaCO3     <= 300 mg/L     Nao"])
    assert _status(doc, "dureza") == "nao_conforme"


def test_dureza_ate_300_e_conforme():
    doc = _doc(["Dureza total      86 mg/L CaCO3     <= 300 mg/L     Sim"])
    assert _status(doc, "dureza") == "conforme"
