# -*- coding: utf-8 -*-
"""
Smoke test das paginas COM o processo de exemplo carregado.

Diferente de tests/smoke_ui.py (que usa um processo vazio): aqui cada pagina e
aberta com EX-CAMPOBOM-001 na sessao, o que exercita os trechos que so rodam
quando ha dados — tabelas de parametros, pranchas, quadro de vazao, laudo.

    .venv/bin/python scripts/semente_campo_bom.py   # garante o exemplo
    .venv/bin/python tests/smoke_exemplo.py
"""

from __future__ import annotations

import ast
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from outorgasys import config as C  # noqa: E402
from outorgasys.state import SESSION_KEY, Processo  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

# As paginas chamam proc.salvar() ao abrir. Rodar sobre o JSON versionado o
# reescrevia (em Linux chegou a apagar o ensaio do exemplo); por isso o teste
# trabalha numa copia em diretorio temporario. Os arquivos referenciados pelo
# processo (mapas, planilha) continuam sendo lidos de data/ por caminho relativo.
_ORIGEM = C.PROCESSOS
_TMP = Path(tempfile.mkdtemp(prefix="outorgasys-exemplo-"))
C.PROCESSOS = _TMP / "processos"
C.SAIDA = _TMP / "saida"
C.PROCESSOS.mkdir(parents=True, exist_ok=True)
C.SAIDA.mkdir(parents=True, exist_ok=True)

PAGINAS = [
    ("app.py", "Orquestrador"),
    ("pages/1_Triagem.py", "Agente 1"),
    ("pages/2_Inteligencia_Espacial.py", "Agente 2"),
    ("pages/3_Hidrogeologia.py", "Agente 3"),
    ("pages/4_Balanco_Hidrico.py", "Agente 4"),
    ("pages/5_Relatorio_Final.py", "Agente 5"),
    ("pages/6_Agente_Dev.py", "Agente 6"),
]


def main() -> int:
    pid = C.PROCESSO_EXEMPLO
    if not (_ORIGEM / f"{pid}.json").exists():
        print(f"Processo de exemplo {pid} nao encontrado. Rode:")
        print("  .venv/bin/python scripts/semente_campo_bom.py")
        return 2

    shutil.copy2(_ORIGEM / f"{pid}.json", C.PROCESSOS / f"{pid}.json")
    if (_ORIGEM / pid).is_dir():
        shutil.copytree(_ORIGEM / pid, C.PROCESSOS / pid, dirs_exist_ok=True)

    proc = Processo(pid=pid)
    print(f"Processo: {proc.id} | agentes concluidos: {proc.get('agentes_concluidos')}")
    print()

    falhas = 0
    for arquivo, rotulo in PAGINAS:
        caminho = ROOT / arquivo
        if not caminho.exists():
            print(f"[AUSENTE] {rotulo:14s} {arquivo}")
            falhas += 1
            continue
        try:
            ast.parse(caminho.read_text(encoding="utf-8"), arquivo)
        except SyntaxError as exc:
            print(f"[FALHOU ] {rotulo:14s} {arquivo}  SyntaxError {exc.lineno}: {exc.msg}")
            falhas += 1
            continue

        at = AppTest.from_file(str(caminho), default_timeout=600)
        try:
            at.session_state[SESSION_KEY] = pid
            at.run()
            if at.exception:
                msgs = "\n".join(f"    {getattr(e, 'value', e)}"
                                 for e in at.exception)
                print(f"[FALHOU ] {rotulo:14s} {arquivo}\n{msgs}")
                falhas += 1
                continue
            n_md = len(at.markdown or [])
            n_img = len(at.get("image") or [])
            print(f"[OK     ] {rotulo:14s} {arquivo}  ({n_md} markdown, "
                  f"{n_img} imagens)")
        except Exception as exc:  # noqa: BLE001
            print(f"[FALHOU ] {rotulo:14s} {arquivo}  {type(exc).__name__}: {exc}")
            print(traceback.format_exc(limit=6))
            falhas += 1

    print()
    print(f"{len(PAGINAS) - falhas}/{len(PAGINAS)} paginas sem excecao.")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
