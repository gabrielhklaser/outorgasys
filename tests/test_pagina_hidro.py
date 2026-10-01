# -*- coding: utf-8 -*-
"""Regressao: a pagina do Agente 3 nao pode apagar o ensaio ja processado."""

from __future__ import annotations

import json

import pytest
from streamlit.testing.v1 import AppTest

from outorgasys import config as C
from outorgasys.state import SESSION_KEY, Processo

PAGINA = C.ROOT / "pages" / "3_Hidrogeologia.py"
EXEMPLO_JSON = C.ROOT / "data" / "processos" / f"{C.PROCESSO_EXEMPLO}.json"
PID = "T-ENSAIO-001"


def _grava_processo(dados_tmp, caminho_planilha: str) -> dict:
    """Cria um processo com o ensaio real do exemplo e a planilha em ``caminho``."""
    base = json.loads(EXEMPLO_JSON.read_text(encoding="utf-8"))
    base["id"] = PID
    base["documentos"]["ensaio_bombeamento"] = {
        "nome": "ensaio.xlsx", "caminho": caminho_planilha, "tamanho": 1}
    (C.PROCESSOS / f"{PID}.json").write_text(
        json.dumps(base, ensure_ascii=False), encoding="utf-8")
    return base


def _abre_pagina() -> AppTest:
    at = AppTest.from_file(str(PAGINA), default_timeout=300)
    at.session_state[SESSION_KEY] = PID
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def test_planilha_ausente_nao_apaga_ensaio_salvo(dados_tmp):
    _grava_processo(dados_tmp, "data/processos/nao-existe/ensaio.xlsx")

    at = _abre_pagina()

    salvo = Processo.carregar(PID)["ensaio"]
    assert salvo["ok"] is True
    assert salvo["cadastro"].get("nivel_estatico_m") == 8
    avisos = [w.value for w in at.warning]
    assert any("nao foi possivel ler" in a.lower() for a in avisos), avisos


@pytest.mark.skipif(not EXEMPLO_JSON.exists(), reason="processo de exemplo ausente")
def test_planilha_com_caminho_windows_e_encontrada(dados_tmp):
    # Caminho exatamente como o exemplo versionado o guarda (gerado no Windows).
    win = (f"data\\processos\\{C.PROCESSO_EXEMPLO}\\arquivos\\"
           "ensaio_bombeamento_PT-01.xlsx")
    _grava_processo(dados_tmp, win)

    at = _abre_pagina()

    assert not [w for w in at.warning if "nao foi possivel ler" in w.value.lower()]
    assert Processo.carregar(PID)["ensaio"]["ok"] is True
