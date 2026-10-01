# -*- coding: utf-8 -*-
"""Pagina do Agente 5: parecer conclusivo."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from outorgasys import config as C
from outorgasys.state import SESSION_KEY, Processo


def test_parecer_da_pagina_5_lista_conclusoes_e_recomendacoes(dados_tmp):
    """O parecer gerado tem conclusoes e recomendacoes; a pagina nao mostrava nenhuma."""
    p = Processo(pid="T-PAR-001", carregar=False)
    p["relatorio"] = {"estrutura": {"parecer": {
        "conclusoes": ["Conclusao <b>unica</b> do teste."],
        "recomendacoes": ["Recomendacao de teste."],
    }}}
    p.salvar()

    at = AppTest.from_file(str(C.ROOT / "pages" / "5_Relatorio_Final.py"),
                           default_timeout=300)
    at.session_state[SESSION_KEY] = "T-PAR-001"
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]

    html = "\n".join(m.value for m in at.markdown)
    assert "Conclusao" in html and "Recomendacao de teste." in html
    assert 'chip-bloq">-</span>' not in html
