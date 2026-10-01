# -*- coding: utf-8 -*-
"""Agente 6: relatorio de defeitos e o botao de download da pagina."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from outorgasys import config as C
from outorgasys.agents import agente6_dev as a6
from outorgasys.state import SESSION_KEY, Processo


def test_caminho_relatorio_aponta_para_o_arquivo_gravado(dados_tmp):
    p = Processo(pid="T-A6-001", carregar=False)
    assert a6.caminho_relatorio(p) is None

    saida = a6.executar(p, salvar=True)

    assert saida["ok"], saida.get("erro")
    rel = a6.caminho_relatorio(p)
    assert rel is not None
    assert C.caminho_absoluto(rel).is_file()
    assert C.caminho_absoluto(rel).name == "defeitos_T-A6-001.md"


def test_pagina_habilita_o_download_do_relatorio_ja_gerado(dados_tmp):
    p = Processo(pid="T-A6-002", carregar=False)
    a6.executar(p, salvar=True)
    p.salvar()

    at = AppTest.from_file(str(C.ROOT / "pages" / "6_Agente_Dev.py"), default_timeout=300)
    at.session_state[SESSION_KEY] = "T-A6-002"
    at.run()

    assert not at.exception, [str(e.value) for e in at.exception]
    botoes = at.get("download_button")
    assert len(botoes) == 1
    assert not botoes[0].proto.disabled, "o relatorio existe: o botao deveria estar ativo"


def test_pagina_nao_cita_diretorio_out_inexistente(dados_tmp):
    at = AppTest.from_file(str(C.ROOT / "pages" / "6_Agente_Dev.py"), default_timeout=300)
    at.run()

    texto = "\n".join(m.value for m in at.markdown)
    assert "`out/`" not in texto
