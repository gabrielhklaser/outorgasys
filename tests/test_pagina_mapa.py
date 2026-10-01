# -*- coding: utf-8 -*-
"""Pagina do Agente 2: mapa interativo embutido."""

from __future__ import annotations

import shutil

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from outorgasys import config as C
from outorgasys.state import SESSION_KEY

EXEMPLO = C.ROOT / "data" / "processos" / f"{C.PROCESSO_EXEMPLO}.json"
PAGINA = C.ROOT / "pages" / "2_Inteligencia_Espacial.py"


@pytest.mark.skipif(not hasattr(st, "iframe"), reason="Streamlit sem st.iframe")
@pytest.mark.skipif(not EXEMPLO.exists(), reason="processo de exemplo ausente")
def test_mapa_interativo_nao_usa_components_html_deprecado(dados_tmp, monkeypatch):
    """st.components.v1.html sera removido; a pagina usa st.iframe quando existe."""
    import streamlit.components.v1 as components

    def proibido(*args, **kwargs):
        raise AssertionError("st.components.v1.html esta deprecado: use st.iframe")

    monkeypatch.setattr(components, "html", proibido)
    shutil.copy2(EXEMPLO, C.PROCESSOS / EXEMPLO.name)

    at = AppTest.from_file(str(PAGINA), default_timeout=300)
    at.session_state[SESSION_KEY] = C.PROCESSO_EXEMPLO
    at.run()

    assert not at.exception, [str(e.value) for e in at.exception]
    assert at.get("iframe"), "o mapa interativo deveria estar na pagina"
