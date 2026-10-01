# -*- coding: utf-8 -*-
"""Persistencia do processo: ciclo salvar/carregar, uploads e identificadores."""

from __future__ import annotations

import pandas as pd

from outorgasys import config as C
from outorgasys.state import Processo


def test_dataframe_sobrevive_ao_ciclo_salvar_e_carregar(dados_tmp):
    p = Processo(pid="T-RT-001", carregar=False)
    p["ensaio"] = {
        "ok": True,
        "bombeamento": pd.DataFrame({"t_min": [1.0, 2.0], "nd_m": [9.7, 9.8]}),
        "recuperacao": pd.DataFrame({"t_linha_min": [5.0], "s_linha_m": [0.4]}),
    }
    p.salvar()

    ensaio = Processo.carregar("T-RT-001")["ensaio"]

    assert isinstance(ensaio["bombeamento"], pd.DataFrame)
    assert list(ensaio["bombeamento"]["t_min"]) == [1.0, 2.0]
    assert list(ensaio["recuperacao"].columns) == ["t_linha_min", "s_linha_m"]


def test_serie_sobrevive_ao_ciclo_salvar_e_carregar(dados_tmp):
    p = Processo(pid="T-RT-002", carregar=False)
    p["valores"] = pd.Series([1.5, 2.5, 3.5])
    p.salvar()

    de_volta = Processo.carregar("T-RT-002")["valores"]

    assert isinstance(de_volta, pd.Series)
    assert list(de_volta) == [1.5, 2.5, 3.5]


# --- uploads ------------------------------------------------------------------


class _Upload:
    """Substituto minimo do UploadedFile do Streamlit."""

    def __init__(self, name: str, dados: bytes = b"conteudo"):
        self.name = name
        self._dados = dados

    def getbuffer(self):
        return memoryview(self._dados)


def test_nome_arquivo_seguro_remove_caracteres_de_controle():
    from outorgasys.state import nome_arquivo_seguro

    assert nome_arquivo_seguro("a\x00b.pdf") == "ab.pdf"
    assert nome_arquivo_seguro("..\\..\\x.py") == "x.py"


def test_salvar_upload_registra_o_nome_seguro(dados_tmp):
    p = Processo(pid="T-UP-001", carregar=False)

    destino = p.salvar_upload("ensaio_bombeamento", _Upload("../../EX.json"))

    assert destino == p.dir_arquivos / "EX.json"
    assert p["documentos"]["ensaio_bombeamento"]["nome"] == "EX.json"
    assert not (dados_tmp / "EX.json").exists()
    assert not (C.PROCESSOS / "EX.json").exists()


def test_foto_enviada_duas_vezes_ocupa_um_registro(dados_tmp):
    p = Processo(pid="T-UP-002", carregar=False)

    p.salvar_upload("registro_fotografico", _Upload("a/foto.jpg", b"1"))
    p.salvar_upload("registro_fotografico", _Upload("b\\foto.jpg", b"22"))

    fotos = p["documentos"]["registro_fotografico"]
    assert [f["nome"] for f in fotos] == ["foto.jpg"]
    assert fotos[0]["tamanho"] == 2


def test_remover_upload_nao_apaga_fora_do_diretorio_de_arquivos(dados_tmp):
    p = Processo(pid="T-UP-003", carregar=False)
    alvo = C.PROCESSOS / "alvo.json"
    alvo.write_text("{}", encoding="utf-8")

    p.remover_upload("registro_fotografico", "../../alvo.json")

    assert alvo.exists()


def test_remover_upload_apaga_o_arquivo_registrado(dados_tmp):
    p = Processo(pid="T-UP-004", carregar=False)
    destino = p.salvar_upload("registro_fotografico", _Upload("foto.jpg"))

    p.remover_upload("registro_fotografico", "foto.jpg")

    assert not destino.exists()
    assert p["documentos"]["registro_fotografico"] == []
