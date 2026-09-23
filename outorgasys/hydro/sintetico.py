# -*- coding: utf-8 -*-
"""
Gerador de ensaio de bombeamento sintetico para validacao ponta a ponta.

A serie e construida pela SOLUCAO DIRETA das equacoes que o Agente 3 usa na
inversao, de modo que o processamento deve recuperar (com ruido) a
transmissividade de entrada:

  Rebaixamento (Cooper-Jacob / Theis para tempos longos):
      s(t)  = Q / (4 pi T) * ln( 2,25 T t / (r^2 S) )

  Recuperacao (Theis / Jacob-Lohman):
      s'(t') = Q / (4 pi T) * ln( (t_b + t') / t' )

Consequencia imediata: o Delta s' por ciclo logaritmico vale
  2,303 * Q / (4 pi T) = 0,183 * Q / T,
exatamente a identidade invertida pela plataforma em T = 0,183 Q / Delta s'.

Unidades: Q em m3/h, T em m2/h, t em horas, r em metros, S adimensional.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

import pandas as pd

from . import planilha


def _grade_min(duracao_h: float) -> list[float]:
    """Grade de leituras recomendada para ensaio de bombeamento (minutos)."""
    g = [1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60]
    g += list(range(90, int(duracao_h * 60) + 1, 30))
    return [float(x) for x in g if x <= duracao_h * 60 + 1e-9]


def serie_rebaixamento(q: float, T: float, S: float, raio: float,
                       duracao_h: float, ne: float, ruido_m: float = 0.02,
                       semente: int | None = None) -> list[dict]:
    """Devolve linhas {t_min, nd_m, s_m, q_m3h} da fase de bombeamento."""
    rnd = random.Random(semente)
    linhas = []
    for t_min in _grade_min(duracao_h):
        t_h = t_min / 60.0
        arg = 2.25 * T * t_h / (raio ** 2 * S)
        s = (q / (4.0 * math.pi * T)) * math.log(arg) if arg > 0 else 0.0
        s = max(0.0, s + rnd.gauss(0.0, ruido_m))
        nd = ne + s
        # Vazao constante com pequena oscilacao de campo
        qi = q * (1.0 + rnd.gauss(0.0, 0.01))
        linhas.append({"t_min": round(t_min, 2), "nd_m": round(nd, 3),
                       "s_m": round(s, 3), "q_m3h": round(qi, 3)})
    return linhas


def serie_recuperacao(q: float, T: float, duracao_h: float, ne: float,
                      ruido_m: float = 0.02,
                      semente: int | None = None) -> list[dict]:
    """Devolve linhas {t_linha_min, na_m, s_linha_m} da fase de recuperacao."""
    rnd = random.Random((semente or 0) + 1)
    t_b = duracao_h * 60.0
    linhas = []
    for tp_min in _grade_min(duracao_h):
        tp = max(tp_min, 0.5)
        s_l = (q / (4.0 * math.pi * T)) * math.log((t_b + tp) / tp)
        s_l = max(0.0, s_l + rnd.gauss(0.0, ruido_m))
        na = ne + s_l
        linhas.append({"t_linha_min": round(tp_min, 2), "na_m": round(na, 3),
                       "s_linha_m": round(s_l, 3)})
    return linhas


def gerar(q: float = 12.0, T: float = 6.0, S: float = 1.0e-3, raio: float = 0.0762,
          ne: float = 8.0, duracao_h: float = 24.0, ruido_m: float = 0.02,
          semente: int | None = 20240917,
          cadastro: dict | None = None) -> dict:
    """Ensaio sintetico completo, no mesmo formato devolvido por ler_planilha()."""
    bom = serie_rebaixamento(q, T, S, raio, duracao_h, ne, ruido_m, semente)
    rec = serie_recuperacao(q, T, duracao_h, ne, ruido_m, semente)
    cad = {
        "nome_cliente": "Exemplo de validacao",
        "municipio": "Campo Bom",
        "uf": "RS",
        "nome_poco": "Poco tubular 6\" - exemplo",
        "profundidade_total_m": 82.0,
        "altura_boca_tubo_m": 0.30,
        "nivel_estatico_m": ne,
        "nivel_dinamico_m": bom[-1]["nd_m"] if bom else ne,
        "posicao_crivo_de_m": 40.0,
        "posicao_crivo_ate_m": 78.0,
        "diametro_util_pol": 6,
        "data_ensaio": "2024-09-17",
        "responsavel_tecnico": "(a preencher)",
        "registro_profissional": "(a preencher)",
    }
    cad.update({k: v for k, v in (cadastro or {}).items() if v not in (None, "")})
    return {
        "ok": True,
        "cadastro": cad,
        "bombeamento": pd.DataFrame(bom),
        "recuperacao": pd.DataFrame(rec),
        "avisos": ["Conjunto sintetico gerado pela plataforma para validacao."],
        "erros": [],
        "abas": [planilha.ABA_CADASTRO, planilha.ABA_BOMBEAMENTO,
                 planilha.ABA_RECUPERACAO],
        "sintetico": True,
        "parametros_geracao": {
            "q_m3h": q, "T_m2h": T, "S": S, "raio_m": raio,
            "ne_m": ne, "duracao_h": duracao_h, "ruido_m": ruido_m,
        },
    }


def salvar_xlsx(ensaio: dict, destino: Path) -> Path:
    """Escreve o ensaio sintetico como .xlsx no formato do modelo fornecido."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cad = ensaio.get("cadastro") or {}
    bom = ensaio.get("bombeamento")
    rec = ensaio.get("recuperacao")

    df_bom = pd.DataFrame({
        "t (min)": bom["t_min"], "ND (m)": bom["nd_m"],
        "s (m)": bom["s_m"], "Q (m3/h)": bom["q_m3h"],
    }) if bom is not None and len(bom) else pd.DataFrame()
    df_rec = pd.DataFrame({
        "t' (min)": rec["t_linha_min"], "NA (m)": rec["na_m"],
        "s' (m)": rec["s_linha_m"],
    }) if rec is not None and len(rec) else pd.DataFrame()

    linhas = [{"campo": rot, "chave_interna": ch,
               "valor": "" if cad.get(ch) in (None, "") else cad.get(ch)}
              for ch, rot, _ in planilha.CAMPOS_CADASTRO]

    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        pd.DataFrame(linhas).to_excel(writer, sheet_name=planilha.ABA_CADASTRO,
                                      index=False)
        df_bom.to_excel(writer, sheet_name=planilha.ABA_BOMBEAMENTO, index=False)
        df_rec.to_excel(writer, sheet_name=planilha.ABA_RECUPERACAO, index=False)
        pd.DataFrame(planilha.ORIENTACOES, columns=["Topico", "Orientacao"]).to_excel(
            writer, sheet_name=planilha.ABA_ORIENTACOES, index=False)
    return destino
