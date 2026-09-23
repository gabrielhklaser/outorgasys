# -*- coding: utf-8 -*-
"""
Agente 1 - Triagem, Cadastro e Validacao Documental (SIOUT RS).

Responsavel por:
  1. triagem binaria de enquadramento (poco < 4" x poco >= 4");
  2. descarga do modelo de planilha de ensaio de bombeamento (.xlsx);
  3. campos de upload (ensaio, posse, analise laboratorial, registro fotografico);
  4. recolha de dados cadastrais e restricoes operacionais com validacoes;
  5. verificacao de que todos os ficheiros obrigatorios foram submetidos antes de
     liberar o Agente 2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config as C
from .. import rules
from ..hydro import planilha


def enquadrar(diametro_util_pol: float | None) -> dict:
    """Triagem inicial de enquadramento (Opcao A x Opcao B)."""
    return rules.classificar_poco(diametro_util_pol)


def modelo_planilha(cadastro: dict | None = None) -> bytes:
    """Bytes do modelo .xlsx de ensaio de bombeamento em etapa unica."""
    return planilha.gerar_modelo(cadastro or {})


def nome_modelo_planilha(proc_id: str) -> str:
    return f"modelo_ensaio_bombeamento_{proc_id}.xlsx"


def finalidades_disponiveis(rede_publica: bool | None) -> list[tuple[str, str, bool]]:
    """Lista (chave, rotulo, permitida) para montagem da UI."""
    permitidas = set(rules.finalidades_permitidas(rede_publica))
    return [
        (k, rotulo, k in permitidas)
        for k, (rotulo, _uso_humano) in C.FINALIDADES.items()
    ]


def parametros_potabilidade() -> list[dict]:
    """Catalogo de parametros da Portaria GM/MS n. 888/2021 para a triagem."""
    return [
        {"chave": k, "parametro": rot, "unidade": un, "criterio": crit, "limite": lim}
        for k, (rot, un, crit, lim) in C.PARAMETROS_POTABILIDADE.items()
    ]


def validar(proc) -> rules.ResultadoValidacao:
    """Bateria completa de regras do Agente 1 sobre o processo."""
    return rules.validar_triagem(proc.data)


def resumo_validacao(res: rules.ResultadoValidacao) -> dict:
    return {
        "ok": res.ok,
        "n_bloqueios": len(res.bloqueios),
        "n_avisos": len(res.avisos),
        "bloqueios": [p.to_dict() for p in res.bloqueios],
        "avisos": [p.to_dict() for p in res.avisos],
    }


def pode_avancar(proc) -> tuple[bool, list[str]]:
    """True apenas se nao ha pendencias bloqueantes do Agente 1."""
    res = validar(proc)
    return res.ok, [f"{p.codigo}: {p.titulo}" for p in res.bloqueios]


def registrar_upload(proc, chave: str, arquivo, papel: str | None = None) -> dict:
    """Persiste um arquivo enviado e devolve o registro criado."""
    if arquivo is None:
        return {}
    caminho = proc.salvar_upload(chave, arquivo)
    registro = {
        "nome": getattr(arquivo, "name", str(caminho)),
        "caminho": C.caminho_relativo(caminho) if caminho else None,
        "tamanho": caminho.stat().st_size if caminho else 0,
        "papel": papel,
    }
    if chave.startswith("camada_"):
        proc.data.setdefault("camadas_usuario", {})[chave] = registro
    proc.log(1, f"Arquivo recebido em '{chave}': {registro['nome']}")
    return registro


def registrar_upload_manual(proc, chave: str, caminho, nome: str | None = None,
                            meta: dict | None = None) -> dict:
    """Registra um arquivo JA existente em disco (gerado pela plataforma) como
    se fosse um envio do usuario. Usado pelo conjunto sintetico do Agente 3.

    O metadado ``sintetico`` fica explicito no registro para que o laudo e o
    Agente 6 declarem a origem nao-oficial do dado.
    """
    from pathlib import Path  # noqa: PLC0415

    p = Path(caminho)
    if not p.exists():
        return {}
    registro = {
        "nome": nome or p.name,
        "caminho": C.caminho_relativo(p),
        "tamanho": p.stat().st_size,
        "origem": "gerado pela plataforma",
    }
    registro.update(meta or {})
    proc.data.setdefault("documentos", {})[chave] = registro
    proc.log(1, f"Arquivo registrado em '{chave}': {registro['nome']}")
    return registro


def arquivos_enviados(proc) -> dict:
    docs = proc.get("documentos") or {}
    return {
        "ensaio_bombeamento": docs.get("ensaio_bombeamento"),
        "posse": [docs.get(k) for k in C.DOCS_POSSE if docs.get(k)],
        "analise_laboratorial": docs.get("analise_laboratorial"),
        "registro_fotografico": docs.get("registro_fotografico") or [],
        "declaracao_separacao_redes": docs.get("declaracao_separacao_redes"),
    }


def checklist_visual(proc) -> list[dict]:
    """Checklist em formato pronto para a interface."""
    enf = proc.get("enquadramento") or {}
    docs = proc.get("documentos") or {}
    exige_ensaio = enf.get("exige_ensaio_24h")

    itens: list[dict] = []

    if exige_ensaio is None:
        itens.append({"item": "Enquadramento do poco", "status": "pendente",
                      "detalhe": "Selecione a Opcao A ou B."})
    elif exige_ensaio:
        tem = bool(docs.get("ensaio_bombeamento"))
        itens.append({
            "item": "Ensaio de bombeamento 24 h + recuperacao (.xlsx/.csv)",
            "status": "ok" if tem else "pendente",
            "detalhe": "Obrigatorio para pocos com diametro util >= 4\"." if not tem
                       else (docs["ensaio_bombeamento"] or {}).get("nome"),
        })
    else:
        itens.append({"item": "Ensaio de bombeamento 24 h", "status": "dispensado",
                      "detalhe": "Dispensado: poco de pequeno diametro (< 4\")."})

    posse = [docs.get(k) for k in C.DOCS_POSSE if docs.get(k)]
    itens.append({
        "item": "Documentacao de posse e terra (PDF/imagem)",
        "status": "ok" if posse else "pendente",
        "detalhe": ", ".join(p["nome"] for p in posse) if posse
                   else "Matricula, contrato, termo de concessao ou recibo do CAR.",
    })

    lab = docs.get("analise_laboratorial")
    itens.append({
        "item": "Analise fisico-quimica e bacteriologica (PDF)",
        "status": "ok" if lab else "pendente",
        "detalhe": (lab or {}).get("nome") if lab
                   else "Conforme Portaria GM/MS n. 888/2021.",
    })

    fotos = docs.get("registro_fotografico") or []
    itens.append({
        "item": "Registro fotografico (4 fotos)",
        "status": "ok" if len(fotos) >= 4 else ("parcial" if fotos else "pendente"),
        "detalhe": f"{len(fotos)}/4 enviadas: boca do poco, laje sanitaria, "
                   "cercamento e cavalete com hidrometro.",
    })

    if proc.get("rede_publica"):
        dec = docs.get("declaracao_separacao_redes")
        itens.append({
            "item": "Declaracao de separacao fisica de redes hidraulicas",
            "status": "ok" if dec else "pendente",
            "detalhe": (dec or {}).get("nome") if dec
                       else "Obrigatoria: imovel atendido por rede publica.",
        })

    return itens
