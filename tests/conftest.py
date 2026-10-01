# -*- coding: utf-8 -*-
"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

import pytest

from outorgasys import config as C


@pytest.fixture
def dados_tmp(tmp_path, monkeypatch):
    """Redireciona processos e saidas para um diretorio temporario.

    ``state.Processo`` e os agentes leem ``C.PROCESSOS`` e ``C.SAIDA`` no momento
    do uso, entao trocar o atributo isola o teste sem tocar em ``data/``.
    """
    processos = tmp_path / "processos"
    saida = tmp_path / "saida"
    processos.mkdir()
    saida.mkdir()
    monkeypatch.setattr(C, "PROCESSOS", processos)
    monkeypatch.setattr(C, "SAIDA", saida)
    return tmp_path
