# -*- coding: utf-8 -*-
"""Pagina do Agente 1: leitura estruturada do laudo laboratorial."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from outorgasys import config as C
from outorgasys.state import SESSION_KEY, Processo

PAGINA = C.ROOT / "pages" / "1_Triagem.py"


def _abre(dados: dict) -> AppTest:
    p = Processo(pid="T-TRIAGEM-001", carregar=False)
    p["analise_laboratorial_dados"] = dados
    p.salvar()
    at = AppTest.from_file(str(PAGINA), default_timeout=300)
    at.session_state[SESSION_KEY] = "T-TRIAGEM-001"
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def test_laudo_sem_parametros_reconhecidos_gera_aviso(dados_tmp):
    at = _abre({"arquivo": "laudo.pdf", "conforme_potabilidade": None,
                "parametros": [], "total_parametros_lidos": 0,
                "avisos": ["Nenhum parametro de potabilidade foi reconhecido."]})

    avisos = [w.value for w in at.warning]
    assert any("Nenhum parametro de potabilidade" in a for a in avisos), avisos
    assert not [s for s in at.success if "conformidade" in s.value.lower()]
