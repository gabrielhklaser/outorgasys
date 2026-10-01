# -*- coding: utf-8 -*-
"""Caminhos gravados no JSON do processo precisam valer em Windows e Linux.

O exemplo versionado foi gerado no Windows e guarda ``data\\processos\\...``.
No Render (Linux) essa string nao e um caminho: a pagina do Agente 5 quebrava e
a do Agente 3 apagava o ensaio salvo ao nao achar a planilha.
"""

from __future__ import annotations

from outorgasys import config as C


def test_caminho_absoluto_aceita_separador_windows():
    r = C.caminho_absoluto("data\\processos\\EX\\relatorio\\laudo_tecnico.md")
    assert r == C.ROOT / "data" / "processos" / "EX" / "relatorio" / "laudo_tecnico.md"


def test_caminho_absoluto_preserva_caminho_absoluto(tmp_path):
    alvo = tmp_path / "a.txt"
    assert C.caminho_absoluto(str(alvo)) == alvo


def test_caminho_absoluto_vazio_devolve_none():
    assert C.caminho_absoluto(None) is None
    assert C.caminho_absoluto("") is None


def test_caminho_relativo_grava_barra_normal():
    alvo = C.ROOT / "data" / "processos" / "X" / "a.md"
    assert C.caminho_relativo(alvo) == "data/processos/X/a.md"


def test_ida_e_volta_entre_relativo_e_absoluto():
    alvo = C.ROOT / "data" / "processos" / "X" / "mapas" / "m.jpg"
    assert C.caminho_absoluto(C.caminho_relativo(alvo)) == alvo
