# -*- coding: utf-8 -*-
"""
Estado do processo de outorga.

Um :class:`Processo` e o objeto que atravessa os seis agentes. Ele e serializado
em ``data/processos/<id>.json`` para sobreviver a reinicios do Streamlit e
permitir auditoria posterior.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config as C


def novo_id() -> str:
    return time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()


def _vazio_processo(pid: str) -> dict:
    return {
        "id": pid,
        "versao": C.VERSAO,
        "criado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "atualizado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),

        # ---- orchestrator -------------------------------------------------------
        "status": "triagem",           # triagem|espacial|hidrogeologia|balanco|relatorio|concluido
        "agentes_concluidos": [],

        # ---- Agente 1 -----------------------------------------------------------
        "enquadramento": {},           # classificar_poco()
        "requerente": {},
        "imovel": {},
        "poco": {},
        "documentos": {},              # chave -> {"nome", "caminho", "mime", "tamanho", ...}
        "hidrometro": {},
        "motobomba": {},
        "reservacao": [],
        "padrao_explotacao": {"horas_dia": None, "dias_semana": None},
        "rede_publica": None,
        "finalidades": [],
        "declaracao_separacao_redes": False,
        "laje": {},
        "construtivo": {},
        "analise_laboratorial": {},

        # ---- Agente 2 -----------------------------------------------------------
        "coordenadas": {},
        "geoespacial": {},

        # ---- Agente 3 -----------------------------------------------------------
        "ensaio": {},
        "hidraulica": {},

        # ---- Agente 4 -----------------------------------------------------------
        "balanco": {},

        # ---- Agente 5 -----------------------------------------------------------
        "relatorio": {},

        # ---- Agente 6 -----------------------------------------------------------
        "issues": [],
        "log": [],
    }


class Processo:
    """Wrapper fino em torno do dicionario de estado, com persistencia em JSON."""

    def __init__(self, data: dict | None = None, pid: str | None = None):
        self.data: dict = data if data is not None else _vazio_processo(pid or novo_id())
        self.id: str = self.data["id"]

    # ------------------------------------------------------------------ caminhos
    @property
    def dir(self) -> Path:
        d = C.PROCESSOS / self.id
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def dir_arquivos(self) -> Path:
        d = self.dir / "arquivos"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def dir_mapas(self) -> Path:
        d = self.dir / "mapas"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def dir_graficos(self) -> Path:
        d = self.dir / "graficos"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def dir_relatorio(self) -> Path:
        d = self.dir / "relatorio"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def caminho_json(self) -> Path:
        return C.PROCESSOS / f"{self.id}.json"

    # ------------------------------------------------------------------ acesso
    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def update(self, **kw) -> "Processo":
        self.data.update(kw)
        return self

    # ------------------------------------------------------------------ eventos
    def log(self, agente: int, mensagem: str, nivel: str = "info") -> None:
        self.data.setdefault("log", []).append({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "agente": agente,
            "nivel": nivel,
            "mensagem": mensagem,
        })

    def add_issue(self, issue: dict) -> None:
        self.data.setdefault("issues", []).append(issue)

    def concluir_agente(self, agente: int) -> None:
        done = set(self.data.get("agentes_concluidos") or [])
        done.add(agente)
        self.data["agentes_concluidos"] = sorted(done)

    # ------------------------------------------------------------------ arquivos
    def salvar_upload(self, chave: str, uploaded) -> Path | None:
        """Persiste um UploadedFile do Streamlit e registra no campo 'documentos'."""
        if uploaded is None:
            return None
        dest = self.dir_arquivos / uploaded.name
        with open(dest, "wb") as fh:
            fh.write(uploaded.getbuffer())
        docs = self.data.setdefault("documentos", {})
        if chave == "registro_fotografico":
            docs.setdefault(chave, [])
            docs[chave] = [
                d for d in docs[chave] if d.get("nome") != uploaded.name
            ] + [{
                "nome": uploaded.name,
                "caminho": str(dest.relative_to(C.ROOT)),
                "tamanho": dest.stat().st_size,
            }]
        else:
            docs[chave] = {
                "nome": uploaded.name,
                "caminho": str(dest.relative_to(C.ROOT)),
                "tamanho": dest.stat().st_size,
            }
        return dest

    def remover_upload(self, chave: str, nome: str | None = None) -> None:
        docs = self.data.setdefault("documentos", {})
        if chave == "registro_fotografico":
            docs[chave] = [d for d in docs.get(chave, []) if d.get("nome") != nome]
        else:
            docs.pop(chave, None)
        if nome:
            p = self.dir_arquivos / nome
            if p.exists():
                p.unlink()

    # ------------------------------------------------------------------ io
    def salvar(self) -> Path:
        self.data["atualizado_em"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.caminho_json.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.caminho_json.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.caminho_json)
        return self.caminho_json

    @classmethod
    def carregar(cls, pid: str) -> "Processo | None":
        p = C.PROCESSOS / f"{pid}.json"
        if not p.exists():
            return None
        return cls(json.loads(p.read_text(encoding="utf-8")))

    @classmethod
    def listar(cls) -> list[dict]:
        out = []
        for p in sorted(C.PROCESSOS.glob("*.json"), reverse=True):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                out.append({
                    "id": d.get("id"),
                    "criado_em": d.get("criado_em"),
                    "atualizado_em": d.get("atualizado_em"),
                    "status": d.get("status"),
                    "requerente": (d.get("requerente") or {}).get("nome") or "-",
                    "municipio": (d.get("imovel") or {}).get("municipio") or "-",
                    "agentes": len(d.get("agentes_concluidos") or []),
                })
            except Exception:  # noqa: BLE001
                continue
        return out

    def excluir(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)
        self.caminho_json.unlink(missing_ok=True)


# --------------------------------------------------------------------------------------
# Helpers de sessao do Streamlit
# --------------------------------------------------------------------------------------

SESSION_KEY = "outorgasys_processo_id"


def garantir_processo(session_state) -> Processo:
    """Obtem (ou cria) o processo corrente a partir do session_state do Streamlit."""
    pid = session_state.get(SESSION_KEY)
    proc = Processo.carregar(pid) if pid else None
    if proc is None:
        proc = Processo()
        session_state[SESSION_KEY] = proc.id
        proc.salvar()
    return proc


def trocar_processo(session_state, pid: str) -> Processo | None:
    proc = Processo.carregar(pid)
    if proc:
        session_state[SESSION_KEY] = proc.id
    return proc


def exportar_bundle(proc: Processo) -> Path:
    """Empacota tudo de um processo (json + anexos + mapas + graficos + relatorio)."""
    import zipfile

    dest = C.SAIDA / f"{proc.id}_bundle.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        if proc.caminho_json.exists():
            zf.write(proc.caminho_json, arcname=f"{proc.id}.json")
        base = proc.dir
        for p in sorted(base.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(C.PROCESSOS)))
    return dest


def carregar_exemplo(nome: str = "campo_bom") -> Processo | None:
    """Carrega um processo de exemplo pronto para demonstracao."""
    p = C.EXEMPLOS / f"{nome}.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    data["id"] = novo_id()
    data["criado_em"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    proc = Processo(data)
    proc.salvar()
    return proc
