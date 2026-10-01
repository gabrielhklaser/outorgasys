# -*- coding: utf-8 -*-
"""Texto vindo do usuario nao pode virar HTML na interface.

As paginas usam ``st.markdown(..., unsafe_allow_html=True)`` para chips e
paineis. Nome de arquivo, nome de camada e campos livres chegam a esses blocos.
"""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from outorgasys import config as C
from outorgasys import ui
from outorgasys.state import SESSION_KEY, Processo


def _html(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_chip_escapa_texto():
    saida = ui.chip('<img src=x onerror="alert(1)">', "ok")
    assert "<img" not in saida
    assert "&lt;img" in saida


def test_escapar_converte_none_e_numeros():
    assert ui.escapar(None) == ""
    assert ui.escapar(12.5) == "12.5"
    assert ui.escapar("a & b <c>") == "a &amp; b &lt;c&gt;"


# Script gravado em arquivo: from_function e from_string falham no AppTest do
# Streamlit 1.49 quando rodam depois de testes que usam st.rerun().
_SCRIPT_BLOCOS_HTML = """
from outorgasys import ui

carga = '<img src=x onerror="alert(1)"><script>alert(2)</script>'
ui.cabecalho(carga, carga)
ui.passo(1, carga)
ui.fonte(carga)
ui.chips([(carga, "info")])
ui.mostrar_pendencias([{
    "codigo": carga, "titulo": carga, "mensagem": carga, "sugestao": carga,
    "bloqueante": True}])
"""


def test_blocos_html_da_ui_escapam_conteudo(tmp_path):
    script = tmp_path / "blocos_html.py"
    script.write_text(_SCRIPT_BLOCOS_HTML, encoding="utf-8")
    at = AppTest.from_file(str(script), default_timeout=60)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]

    html = _html(at)
    assert "<img" not in html
    assert "<script" not in html
    assert html.count("&lt;img") >= 6


def test_checklist_da_triagem_escapa_nome_de_arquivo(dados_tmp):
    nome = '<img src=x onerror="alert(1)">.pdf'
    p = Processo(pid="T-ESC-001", carregar=False)
    p["documentos"] = {
        "matricula_imovel": {"nome": nome, "caminho": "x/a.pdf", "tamanho": 1},
        "analise_laboratorial": {"nome": nome, "caminho": "x/b.pdf", "tamanho": 1},
    }
    p.salvar()

    at = AppTest.from_file(str(C.ROOT / "pages" / "1_Triagem.py"), default_timeout=300)
    at.session_state[SESSION_KEY] = "T-ESC-001"
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]

    html = _html(at)
    assert "<img" not in html
    assert "&lt;img" in html
