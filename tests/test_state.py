# -*- coding: utf-8 -*-
"""Persistencia do processo: ciclo salvar/carregar, uploads e identificadores."""

from __future__ import annotations

import json

import pandas as pd
import pytest

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


# --- identificador do processo -------------------------------------------------


@pytest.mark.parametrize("pid", ["../x", "a/b", "a\\b", "..", "", "x" * 80, "a b", "a.json"])
def test_pid_invalido_e_rejeitado(dados_tmp, pid):
    with pytest.raises(ValueError):
        Processo(pid=pid) if pid else Processo._json_de(pid)
    with pytest.raises(ValueError):
        Processo._json_de(pid)
    assert Processo.carregar(pid) is None


@pytest.mark.parametrize("pid", ["EX-CAMPOBOM-001", "20260930-A1B2C3", "T_x-1"])
def test_pid_valido_e_aceito(dados_tmp, pid):
    assert Processo._json_de(pid).name == f"{pid}.json"


# --- leitura tolerante ------------------------------------------------------------


def test_json_com_bom_do_windows_carrega(dados_tmp):
    dados = {"id": "T-BOM-001", "requerente": {"nome": "Ação"}}
    (C.PROCESSOS / "T-BOM-001.json").write_bytes(
        b"\xef\xbb\xbf" + json.dumps(dados).encode("utf-8"))

    p = Processo.carregar("T-BOM-001")

    assert p is not None and p["requerente"]["nome"] == "Ação"


def test_json_corrompido_e_preservado_em_vez_de_sobrescrito(dados_tmp):
    caminho = C.PROCESSOS / "T-RUIM-001.json"
    caminho.write_text('{"id": "T-RUIM-001", "requerente": {"nome": ', encoding="utf-8")

    assert Processo.carregar("T-RUIM-001") is None

    copias = list(C.PROCESSOS.glob("T-RUIM-001.json.corrompido-*"))
    assert len(copias) == 1
    assert copias[0].read_text(encoding="utf-8").startswith('{"id": "T-RUIM-001"')
    assert not caminho.exists()
