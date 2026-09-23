# -*- coding: utf-8 -*-
"""
Estado do processo de outorga.

Um :class:`Processo` e o objeto que atravessa os seis agentes. Ele e serializado
em ``data/processos/<id>.json`` para sobreviver a reinicios do Streamlit e
permitir auditoria posterior.
"""

from __future__ import annotations

import datetime
import json
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config as C


# --------------------------------------------------------------------------------------
# Persistencia tolerante
# --------------------------------------------------------------------------------------

def _sanear_json(obj: Any, _profundidade: int = 0) -> Any:
    """Converte objetos nao serializaveis em estruturas JSON validas.

    O processo circula por agentes que guardam DataFrames (ensaio de bombeamento),
    escalares numpy e datas. Sem este saneamento o ``salvar()`` quebraria no meio
    do fluxo e o operador perderia o trabalho ja feito.
    """
    if _profundidade > 12:
        return "<limite de profundidade>"

    if obj is None or isinstance(obj, (str, bool, int)):
        return obj

    if isinstance(obj, float):
        # NaN/Infinity produzem JSON invalido para leitores estritos.
        return obj if obj == obj and obj not in (float("inf"), float("-inf")) else None

    if isinstance(obj, dict):
        return {str(k): _sanear_json(v, _profundidade + 1) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [_sanear_json(v, _profundidade + 1)
                for v in (obj[:2000] if len(obj) > 2000 else obj)]

    if isinstance(obj, (set, frozenset)):
        return [_sanear_json(v, _profundidade + 1)
                for v in sorted(obj, key=lambda x: str(x))[:2000]]

    if isinstance(obj, Path):
        try:
            return C.caminho_relativo(obj)
        except Exception:  # noqa: BLE001
            return str(obj)

    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()

    nome_tipo = type(obj).__name__
    modulo = type(obj).__module__ or ""

    if modulo.startswith("pandas") or nome_tipo in ("DataFrame", "Series"):
        try:
            if nome_tipo == "Series":
                return {"__tipo__": "serie", "valores": _sanear_json(
                    obj.tolist(), _profundidade + 1)}
            return {"__tipo__": "dataframe",
                    "colunas": [str(c) for c in obj.columns],
                    "linhas": _sanear_json(
                        obj.head(5000).to_dict("records"), _profundidade + 1)}
        except Exception:  # noqa: BLE001
            return f"<{nome_tipo}>"

    if modulo.startswith("numpy") or nome_tipo.startswith(("int", "float", "bool_",
                                                            "ndarray")):
        try:
            if nome_tipo == "ndarray":
                return _sanear_json(obj.tolist(), _profundidade + 1)
            return _sanear_json(obj.item(), _profundidade + 1)
        except Exception:  # noqa: BLE001
            return None

    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return _sanear_json(obj.to_dict(), _profundidade + 1)
        except Exception:  # noqa: BLE001
            pass

    if hasattr(obj, "__dict__"):
        try:
            return _sanear_json(vars(obj), _profundidade + 1)
        except Exception:  # noqa: BLE001
            pass

    return f"<{nome_tipo} nao serializavel>"


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

    def __init__(self, data: dict | None = None, pid: str | None = None,
                 carregar: bool = True):
        """Abre um processo.

        Com ``pid`` e sem ``data``, tenta carregar do disco antes de criar um
        processo novo — evita que ``Processo(pid=...)`` substitua silenciosamente
        um trabalho ja salvo. Passe ``carregar=False`` para forcar um novo.
        """
        if data is None and pid and carregar:
            existente = self._ler(pid)
            if existente is not None:
                data = existente
        self.data: dict = data if data is not None else _vazio_processo(pid or novo_id())
        self.id: str = self.data["id"]

    @staticmethod
    def _json_de(pid: str) -> Path:
        return C.PROCESSOS / f"{pid}.json"

    @staticmethod
    def _diretorio_de(pid: str) -> Path:
        return C.PROCESSOS / pid

    @staticmethod
    def _ler(pid: str) -> dict | None:
        p = Processo._json_de(pid)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None

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
        return self._json_de(self.id)

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
                "caminho": C.caminho_relativo(dest),
                "tamanho": dest.stat().st_size,
            }]
        else:
            docs[chave] = {
                "nome": uploaded.name,
                "caminho": C.caminho_relativo(dest),
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
        tmp.write_text(json.dumps(_sanear_json(self.data), ensure_ascii=False,
                                  indent=2), encoding="utf-8")
        tmp.replace(self.caminho_json)
        return self.caminho_json

    @classmethod
    def carregar(cls, pid: str) -> "Processo | None":
        dados = cls._ler(pid)
        return cls(dados) if dados is not None else None

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
