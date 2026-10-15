# -*- coding: utf-8 -*-
"""O lock travado precisa continuar dentro dos limites de requirements.txt.

``requirements.lock`` e gerado por ``uv pip compile`` (ver README). Se alguem
sobe um teto em ``requirements.txt`` e esquece de regenerar o lock, os dois
divergem em silencio: o Render instala pelo requirements.txt e o lock fica
mentindo. Estes testes rodam sem rede e pegam a divergencia na CI.
"""

from __future__ import annotations

import re

import pytest

from outorgasys import config as C

try:
    from packaging.requirements import Requirement
    from packaging.version import Version
except ImportError:  # pragma: no cover - packaging vem com pytest/streamlit
    pytest.skip("packaging indisponivel", allow_module_level=True)

REQUISITOS = C.ROOT / "requirements.txt"
LOCK = C.ROOT / "requirements.lock"


def _requisitos() -> dict[str, Requirement]:
    """Pacotes pedidos em requirements.txt, por nome normalizado."""
    out: dict[str, Requirement] = {}
    for linha in REQUISITOS.read_text(encoding="utf-8").splitlines():
        linha = linha.split("#", 1)[0].strip()
        if not linha or linha.startswith("-"):
            continue
        req = Requirement(linha)
        out[re.sub(r"[-_.]+", "-", req.name).lower()] = req
    return out


def _pins() -> dict[str, list[str]]:
    """Versoes travadas em requirements.lock, por nome normalizado.

    O lock e de resolucao universal: um mesmo pacote pode aparecer mais de uma
    vez com marcadores de ambiente (``numpy==2.4.6 ; python_full_version <
    '3.12'``). Todas as versoes tem de respeitar o limite, porque o limite de
    requirements.txt vale para qualquer marcador.
    """
    out: dict[str, list[str]] = {}
    for m in re.finditer(r"^([A-Za-z0-9][\w.\-]*)==([^\s;\\]+)",
                         LOCK.read_text(encoding="utf-8"), flags=re.M):
        nome = re.sub(r"[-_.]+", "-", m.group(1)).lower()
        out.setdefault(nome, []).append(m.group(2))
    return out


def test_lock_existe_e_tem_hashes():
    assert LOCK.exists(), "gere o lock: uv pip compile requirements.txt ..."
    texto = LOCK.read_text(encoding="utf-8")
    assert "--hash=sha256:" in texto


def test_todo_pacote_travado_respeita_o_limite_de_requirements():
    reqs, pins = _requisitos(), _pins()

    problemas = [
        f"{nome}=={versao} esta fora de {reqs[nome]}"
        for nome, versoes in pins.items() if nome in reqs
        for versao in versoes
        if not reqs[nome].specifier.contains(Version(versao), prereleases=True)
    ]

    assert not problemas, "regenerar: uv pip compile requirements.txt --generate-hashes " \
                          "--universal --python-version 3.11 -o requirements.lock"


def test_tudo_que_requirements_pede_esta_no_lock():
    reqs, pins = _requisitos(), _pins()

    faltando = sorted(set(reqs) - set(pins))

    assert not faltando, f"faltam no lock: {', '.join(faltando)}"
