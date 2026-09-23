# -*- coding: utf-8 -*-
"""
Agente 5 - Emissao do Relatorio Tecnico Final e da Minuta SIOUT.

Consolida os dados dos Agentes 1 a 4 num documento tecnico coeso e formal,
disponivel em tres formatos:

* Markdown editavel (``laudo.md``);
* PDF pronto para assinatura (``laudo.pdf``);
* Minuta estruturada para preenchimento no SIOUT (``minuta_siout.md``).
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any

from .. import config as C
from ..report import laudo, pdf as pdf_mod


def gerar(proc, resp_tecnico: dict | None = None, art: str | None = None,
          gerar_pdf: bool = True) -> dict:
    """Executa o Agente 5 e devolve os caminhos dos documentos gerados."""
    saida: dict[str, Any] = {
        "ok": False,
        "estrutura": None,
        "markdown": None,
        "pdf": None,
        "minuta": None,
        "erros": [],
        "avisos": [],
    }

    try:
        estrutura = laudo.montar_estrutura(proc, resp_tecnico, art)
        saida["estrutura"] = estrutura
    except Exception as exc:  # noqa: BLE001
        saida["erros"].append(f"Falha ao montar a estrutura do laudo: "
                              f"{type(exc).__name__}: {exc}")
        saida["erros"].append(traceback.format_exc(limit=8))
        return saida

    diretorio = proc.dir_relatorio

    # ---- Markdown ---------------------------------------------------------------------
    try:
        md = laudo.para_markdown(estrutura)
        p_md = diretorio / "laudo_tecnico.md"
        p_md.write_text(md, encoding="utf-8")
        saida["markdown"] = C.caminho_relativo(p_md)
    except Exception as exc:  # noqa: BLE001
        saida["erros"].append(f"Falha ao gerar o Markdown: {type(exc).__name__}: {exc}")

    # ---- Minuta SIOUT -------------------------------------------------------------------
    try:
        minuta = gerar_minuta(proc, estrutura)
        p_min = diretorio / "minuta_siout.md"
        p_min.write_text(minuta, encoding="utf-8")
        saida["minuta"] = C.caminho_relativo(p_min)
    except Exception as exc:  # noqa: BLE001
        saida["erros"].append(f"Falha ao gerar a minuta SIOUT: {type(exc).__name__}: {exc}")

    # ---- PDF ---------------------------------------------------------------------------
    if gerar_pdf:
        try:
            p_pdf = pdf_mod.gerar_pdf(estrutura, diretorio / "laudo_tecnico.pdf")
            saida["pdf"] = C.caminho_relativo(p_pdf)
        except Exception as exc:  # noqa: BLE001
            saida["erros"].append(f"Falha ao gerar o PDF: {type(exc).__name__}: {exc}")
            saida["erros"].append(traceback.format_exc(limit=8))

    saida["ok"] = bool(saida["markdown"]) and (not gerar_pdf or bool(saida["pdf"]))
    proc["relatorio"] = saida
    proc.concluir_agente(5)
    proc.log(5, "Relatorio tecnico emitido.")
    return saida


# --------------------------------------------------------------------------------------
# Minuta SIOUT
# --------------------------------------------------------------------------------------


def gerar_minuta(proc, estrutura: dict) -> str:
    """Minuta com os campos a transcrever no formulario do SIOUT RS."""
    e = estrutura
    hid = (proc.get("hidraulica") or proc.get("hidrogeologia") or {}).get("parametros") or {}
    bal = proc.get("balanco") or {}
    geo = proc.get("geoespacial") or {}
    enf = proc.get("enquadramento") or {}
    poco = proc.get("poco") or {}
    constr = proc.get("construtivo") or {}
    pe = proc.get("padrao_explotacao") or {}
    req = proc.get("requerente") or {}
    imo = proc.get("imovel") or {}

    def n(v, casas=2, un=""):
        if v in (None, "", "-"):
            return "-"
        try:
            f = float(v)
        except (TypeError, ValueError):
            return str(v)
        return f"{f:,.{casas}f} {un}".strip().replace(",", "X").replace(".", ",").replace("X", ".")

    q = bal.get("quadro") or {}
    linhas_quadro = "\n".join(
        f"| {l['mes']} | {n(l['dias_operacao'], 2)} | {n(l['horas_dia'], 2)} | "
        f"{n(l['vazao_m3h'], 3)} | {n(l['volume_m3_mes'], 2)} |"
        for l in q.get("linhas", [])
    )

    return f"""# MINUTA PARA PREENCHIMENTO NO SIOUT RS

**Processo interno:** {proc.id}
**Gerado em:** {e['cabecalho']['data_emissao']} por {C.NOME_SISTEMA} v{C.VERSAO}

> Transcreva os campos abaixo para o formulario do SIOUT RS. Os valores marcados
> com `-` nao foram determinados e devem ser preenchidos manualmente.

---

## 1. Identificacao do requerente

| Campo SIOUT | Valor |
|---|---|
| Nome / Razao social | {e['identificacao']['requerente'].get('Nome / Razao social')} |
| CPF / CNPJ | {e['identificacao']['requerente'].get('CPF / CNPJ')} |
| Telefone | {e['identificacao']['requerente'].get('Telefone')} |
| E-mail | {e['identificacao']['requerente'].get('E-mail')} |

## 2. Localizacao da intervencao

| Campo SIOUT | Valor |
|---|---|
| Municipio / UF | {e['identificacao']['imovel'].get('Municipio / UF')} |
| Endereco | {e['identificacao']['imovel'].get('Endereco')} |
| Coordenadas (SIRGAS 2000) | {e['identificacao']['imovel'].get('Coordenadas (SIRGAS 2000)')} |
| Coordenadas UTM | {e['identificacao']['imovel'].get('Coordenadas UTM')} |
| Bacia hidrografica | {e['identificacao']['imovel'].get('Bacia hidrografica')} |
| Regiao hidrografica | {e['identificacao']['imovel'].get('Regiao hidrografica')} |

## 3. Caracteristicas construtivas

| Campo SIOUT | Valor |
|---|---|
| Tipo de poco | {e['caracterizacao']['poco'].get('Tipo de poco')} |
| Diametro util (pol) | {e['caracterizacao']['poco'].get('Diametro util (pol)')} |
| Profundidade total (m) | {e['caracterizacao']['poco'].get('Profundidade total (m)')} |
| Diametro da perfuracao (mm) | {e['caracterizacao']['poco'].get('Diametro da perfuracao (mm)')} |
| Diametro do revestimento (mm) | {e['caracterizacao']['poco'].get('Diametro do revestimento (mm)')} |
| Espaco anular (mm) | {e['caracterizacao']['poco'].get('Espaco anular (mm)')} |
| Profundidade do selo sanitario (m) | {e['caracterizacao']['poco'].get('Profundidade do selo sanitario (m)')} |
| Posicao do crivo (m) | {e['caracterizacao']['poco'].get('Posicao do crivo (m)')} |
| Formacao geologica | {e['caracterizacao']['poco'].get('Formacao geologica')} |
| Litologia predominante | {e['caracterizacao']['poco'].get('Litologia predominante')} |
| Sistema aquifer | {e['caracterizacao']['poco'].get('Sistema aquifer')} |
| Tipo de aquifer | {e['caracterizacao']['poco'].get('Tipo de aquifer')} |

## 4. Resultados do ensaio de bombeamento

| Campo SIOUT | Valor |
|---|---|
| Nivel estatico NE (m) | {n(hid.get('ne_m'))} |
| Nivel dinamico ND (m) | {n(hid.get('nd_m'))} |
| Rebaixamento maximo s_max (m) | {n(hid.get('s_max_m'))} |
| Vazao estabilizada Q (m3/h) | {n(hid.get('q_estavel_m3h'))} |
| Delta s' (m/ciclo) | {n(hid.get('delta_s_linha_m'), 4)} |
| Transmissividade T (m2/h) | {n(hid.get('T_m2h'), 3)} |
| Transmissividade T (m2/s) | {n(hid.get('T_m2s'), 6)} |
| Capacidade especifica q (m3/h/m) | {n(hid.get('q_capacidade_especifica_m3h_m'), 3)} |
| Capacidade especifica longo prazo q(t) (m3/h/m) | {n(hid.get('q_longo_prazo_m3h_m'), 3)} |
| Vazao otima Q_ot (m3/h) | {n(hid.get('Q_ot_m3h'))} |
| Duracao do ensaio (h) | {n(hid.get('duracao_h'), 1)} |

## 5. Equipamentos

| Campo SIOUT | Valor |
|---|---|
| Bomba - fabricante / modelo | {e['equipamentos']['motobomba'].get('Fabricante')} / {e['equipamentos']['motobomba'].get('Modelo')} |
| Bomba - numero de serie | {e['equipamentos']['motobomba'].get('Numero de serie')} |
| Bomba - potencia (HP/CV) | {e['equipamentos']['motobomba'].get('Potencia (HP/CV)')} |
| Bomba - estagios | {e['equipamentos']['motobomba'].get('Numero de estagios')} |
| Bomba - profundidade de instalacao (m) | {e['equipamentos']['motobomba'].get('Profundidade de instalacao (m)')} |
| Hidrometro - fabricante / modelo | {e['equipamentos']['hidrometro'].get('Fabricante')} / {e['equipamentos']['hidrometro'].get('Modelo')} |
| Hidrometro - numero de serie | {e['equipamentos']['hidrometro'].get('Numero de serie')} |
| Hidrometro - DN (mm) | {e['equipamentos']['hidrometro'].get('Diametro nominal (DN)')} |
| Hidrometro - vazao nominal (m3/h) | {e['equipamentos']['hidrometro'].get('Vazao nominal (m3/h)')} |
| Reservacao total (L) | {e['equipamentos']['reservacao'].get('Capacidade total (L)')} |

## 6. Finalidades e regime de uso

| Campo SIOUT | Valor |
|---|---|
| Finalidades declaradas | {e['parecer']['finalidades']} |
| Imovel atendido por rede publica | {e['parecer']['rede_publica']} |
| Declaracao de separacao de redes | {e['parecer']['separacao_redes']} |
| Horas por dia | {e['regime'].get('Horas por dia')} |
| Dias por semana | {e['regime'].get('Dias por semana')} |
| Vazao adotada (m3/h) | {e['regime'].get('Vazao adotada')} |
| Repouso diario (h) | {e['regime'].get('Repouso diario')} |

## 7. Quadro de Vazao da Intervencao

| Mes | Dias/Mes | Horas/Dia | Vazao (m3/h) | Volume (m3/mes) |
|---|---|---|---|---|
{linhas_quadro}

**Volume anual total:** {n(q.get('volume_anual_m3'), 0)} m3/ano
**Vazao diaria maxima:** {n(q.get('vazao_diaria_max_m3_dia'), 2)} m3/dia

---

## 8. Documentos a anexar no SIOUT

1. Laudo Tecnico de Caracterizacao Hidrogeologica (PDF assinado, com ART).
2. Anotacao de Responsabilidade Tecnica (ART).
3. Arquivos dos tres mapas: `{', '.join(e['anexos']['mapas']) or '-'}`.
4. Graficos do ensaio de bombeamento.
5. Relatorio de analise fisico-quimica e bacteriologica (Portaria GM/MS n. 888/2021).
6. Comprovante de posse ou dominio do imovel.
7. Registro fotografico do poco, da laje sanitaria, do cercamento e do cavalete
   com hidrometro.
8. Declaracao de separacao fisica de redes hidraulicas (quando atendido por rede
   publica).

---

_Conforme a norma CEGM/CREA-RS n. 08/2022, o laudo deve ser assinado por
profissional habilitado (Geologo ou Engenheiro de Minas) com ART registrada._
"""
