# -*- coding: utf-8 -*-
"""
Smoke test da interface Streamlit.

Executa cada pagina fora do navegador com streamlit.testing.v1.AppTest e falha
se qualquer pagina levantar excecao. Uso:

    .venv/bin/python tests/smoke_ui.py            # todas as paginas
    .venv/bin/python tests/smoke_ui.py 1_Triagem  # uma pagina
"""

from __future__ import annotations

import ast
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tempfile  # noqa: E402

from streamlit.testing.v1 import AppTest  # noqa: E402

from outorgasys import config as C  # noqa: E402

# O AppTest executa as paginas de verdade: redireciona a gravacao de processos
# para um diretorio temporario para nao poluir data/processos.
_TMP = Path(tempfile.mkdtemp(prefix="outorgasys-smoke-"))
C.PROCESSOS = _TMP / "processos"
C.SAIDA = _TMP / "saida"
C.PROCESSOS.mkdir(parents=True, exist_ok=True)
C.SAIDA.mkdir(parents=True, exist_ok=True)

PAGINAS: list[tuple[str, str]] = [
    ("app.py", "Orquestrador"),
    ("pages/1_Triagem.py", "Agente 1"),
    ("pages/2_Inteligencia_Espacial.py", "Agente 2"),
    ("pages/3_Hidrogeologia.py", "Agente 3"),
    ("pages/4_Balanco_Hidrico.py", "Agente 4"),
    ("pages/5_Relatorio_Final.py", "Agente 5"),
    ("pages/6_Agente_Dev.py", "Agente 6"),
]


def rodar(arquivo: str) -> tuple[bool, str]:
    # O AppTest engole SyntaxError de compilacao: verifica antes de executar.
    try:
        ast.parse((ROOT / arquivo).read_text(encoding="utf-8"), arquivo)
    except SyntaxError as exc:
        return False, f"SyntaxError linha {exc.lineno}: {exc.msg}"
    at = AppTest.from_file(str(ROOT / arquivo), default_timeout=600)
    try:
        at.run()
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=8)}"
    if at.exception:
        msgs = "\n".join(f"  {e.type.__name__ if hasattr(e, 'type') else ''}: "
                         f"{getattr(e, 'value', e)}" for e in at.exception)
        return False, f"excecoes na pagina:\n{msgs}"
    return True, f"ok ({len(at.markdown or [])} markdown, {len(at.button)} botoes)"


def main() -> int:
    apenas = sys.argv[1] if len(sys.argv) > 1 else None
    alvos = [p for p in PAGINAS if not apenas or apenas in p[0]]
    if not alvos:
        print(f"Nenhuma pagina corresponde a {apenas!r}")
        return 2

    falhas = 0
    for arquivo, rotulo in alvos:
        caminho = ROOT / arquivo
        if not caminho.exists():
            print(f"[AUSENTE] {rotulo:14s} {arquivo}")
            falhas += 1
            continue
        ok, detalhe = rodar(arquivo)
        print(f"[{'OK     ' if ok else 'FALHOU '}] {rotulo:14s} {arquivo}  {detalhe}")
        if not ok:
            falhas += 1
    print()
    print(f"{len(alvos) - falhas}/{len(alvos)} paginas sem excecao.")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
