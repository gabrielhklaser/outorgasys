# -*- coding: utf-8 -*-
"""Portao de acesso opcional por senha unica.

Sem a variavel de ambiente ``OUTORGASYS_SENHA`` nada muda: o app abre como
antes. Com ela definida (no Render, em Environment), toda pagina pede a senha
antes de mostrar qualquer dado.

Limites, para quem for decidir se basta:

* e uma senha compartilhada, sem usuarios individuais nem trilha de quem fez o que;
* a sessao do Streamlit guarda a liberacao; outra aba ou outro navegador pede de novo;
* o atraso de 1 s apos erro e por sessao, entao nao impede um ataque com muitas
  sessoes em paralelo. Use uma senha longa. Para acesso por pessoa, o caminho e o
  login OIDC do Streamlit (``st.login``) ou um proxy de autenticacao na frente.
"""

from __future__ import annotations

import hmac
import os
import time

import streamlit as st

VAR_SENHA = "OUTORGASYS_SENHA"
CHAVE_SESSAO = "outorgasys_acesso_liberado"


def senha_configurada() -> str | None:
    """Senha exigida, ou None quando o portao esta desligado."""
    senha = os.environ.get(VAR_SENHA, "")
    return senha if senha.strip() else None


def senha_confere(digitada: str, esperada: str) -> bool:
    """Compara em tempo constante (``hmac.compare_digest``), tambem com acentos."""
    return hmac.compare_digest(digitada.encode("utf-8"), esperada.encode("utf-8"))


def exigir_acesso() -> None:
    """Para a execucao da pagina enquanto a sessao nao informar a senha correta."""
    esperada = senha_configurada()
    if esperada is None or st.session_state.get(CHAVE_SESSAO):
        return

    st.title("OutorgaSys")
    st.caption("Acesso restrito. Informe a senha para continuar.")
    with st.form("acesso_outorgasys"):
        digitada = st.text_input("Senha de acesso", type="password")
        enviar = st.form_submit_button("Entrar")
    if enviar:
        if senha_confere(digitada, esperada):
            st.session_state[CHAVE_SESSAO] = True
            st.rerun()
        time.sleep(1.0)
        st.error("Senha incorreta.")
    st.stop()
