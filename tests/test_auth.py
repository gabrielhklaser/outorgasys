# -*- coding: utf-8 -*-
"""Portao de acesso opcional por senha unica (variavel OUTORGASYS_SENHA)."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from outorgasys import config as C

SENHA = "segredo-de-teste"
PAGINAS = [
    "app.py", "pages/1_Triagem.py", "pages/2_Inteligencia_Espacial.py",
    "pages/3_Hidrogeologia.py", "pages/4_Balanco_Hidrico.py",
    "pages/5_Relatorio_Final.py", "pages/6_Agente_Dev.py",
]


def _abre(pagina: str) -> AppTest:
    at = AppTest.from_file(str(C.ROOT / pagina), default_timeout=300)
    at.run()
    return at


def _texto(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_senha_confere_compara_em_tempo_constante_e_aceita_unicode():
    from outorgasys import auth

    assert auth.senha_confere("abc", "abc")
    assert not auth.senha_confere("abd", "abc")
    assert not auth.senha_confere("", "abc")
    assert auth.senha_confere("açaí-ß", "açaí-ß")
    assert not auth.senha_confere("acai", "açaí")


@pytest.mark.parametrize("valor", ["", "   "])
def test_variavel_vazia_ou_em_branco_nao_ativa_o_portao(monkeypatch, valor):
    from outorgasys import auth

    monkeypatch.setenv("OUTORGASYS_SENHA", valor)
    assert auth.senha_configurada() is None


def test_sem_senha_configurada_a_pagina_abre_normalmente(dados_tmp, monkeypatch):
    monkeypatch.delenv("OUTORGASYS_SENHA", raising=False)

    at = _abre("app.py")

    assert not at.exception
    assert "Orquestrador Central" in _texto(at)
    assert not at.text_input


@pytest.mark.parametrize("pagina", PAGINAS)
def test_com_senha_configurada_toda_pagina_pede_senha_e_nao_mostra_dados(
        dados_tmp, monkeypatch, pagina):
    monkeypatch.setenv("OUTORGASYS_SENHA", SENHA)

    at = _abre(pagina)

    assert not at.exception, [str(e.value) for e in at.exception]
    assert [t.label for t in at.text_input] == ["Senha de acesso"]
    assert not at.sidebar.markdown, "a barra lateral (processo) nao pode aparecer"
    assert "Orquestrador Central" not in _texto(at)
    # nenhum processo foi criado so por abrir a pagina bloqueada
    assert not list(C.PROCESSOS.glob("*.json"))


def test_senha_errada_continua_bloqueado(dados_tmp, monkeypatch):
    monkeypatch.setenv("OUTORGASYS_SENHA", SENHA)
    monkeypatch.setattr("time.sleep", lambda s: None)  # nao espera o atraso no teste
    at = _abre("app.py")

    at.text_input[0].input("errada").run()
    at.button[0].click().run()

    assert [e.value for e in at.error] == ["Senha incorreta."]
    assert "Orquestrador Central" not in _texto(at)


def test_senha_correta_libera_a_pagina_nesta_sessao(dados_tmp, monkeypatch):
    monkeypatch.setenv("OUTORGASYS_SENHA", SENHA)
    at = _abre("app.py")

    at.text_input[0].input(SENHA).run()
    at.button[0].click().run()

    assert not at.exception
    assert "Orquestrador Central" in _texto(at)
    assert not at.text_input
    # e continua liberada nas proximas execucoes da mesma sessao
    at.run()
    assert "Orquestrador Central" in _texto(at)
