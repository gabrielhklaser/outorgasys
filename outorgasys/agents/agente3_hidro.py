# -*- coding: utf-8 -*-
"""
Agente 3 - Processamento Hidrogeologico e Graficos.

Le a planilha de ensaio de bombeamento (.xlsx), executa a memoria de calculo
(Theis / Cooper-Jacob / Jacob-Lohman) e renderiza o painel com os dois graficos
tecnicos. A saida alimenta os Agentes 4 e 5.
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any

import pandas as pd  # noqa: PLC0415

from .. import config as C
from ..hydro import graficos, planilha, theis


def processar_planilha(caminho: Path | Any, meta_manual: dict | None = None) -> dict:
    """Ingestao da planilha: cadastro, fases de bombeamento e de recuperacao."""
    r = planilha.ler_planilha(caminho)
    cadastro = dict(r.get("cadastro") or {})
    cadastro.update(meta_manual or {})
    return {
        "ok": r.get("ok", False),
        "cadastro": cadastro,
        "bombeamento": r.get("bombeamento"),
        "recuperacao": r.get("recuperacao"),
        "avisos": r.get("avisos") or [],
        "erros": r.get("erros") or [],
        "abas": r.get("abas") or [],
    }


def calcular(proc, usar_q_manual: bool = False, q_manual: float | None = None,
             gerar_graficos: bool = True) -> dict:
    """Executa a memoria de calculo completa e gera os graficos."""
    saida: dict[str, Any] = {
        "ok": False,
        "parametros": {},
        "memoria": {},
        "graficos": {},
        "avisos": [],
        "erros": [],
    }

    dados = proc.get("ensaio") or {}
    cad = dados.get("cadastro") or {}
    bombeamento = dados.get("bombeamento")
    recuperacao = dados.get("recuperacao")
    pouco = proc.get("poco") or {}

    ne = planilha.numeric(cad.get("nivel_estatico_m"))
    nd = planilha.numeric(cad.get("nivel_dinamico_m"))
    profundidade = planilha.numeric(cad.get("profundidade_total_m")) or \
        planilha.numeric(pouco.get("profundidade_total_m"))

    if bombeamento is not None and len(bombeamento) and nd is None:
        col = bombeamento.get("nd_m")
        if col is not None and col.notna().any():
            nd = float(col.dropna().iloc[-1])
    if bombeamento is not None and len(bombeamento) and ne is None:
        col_n = bombeamento.get("nd_m")
        col_s = bombeamento.get("s_m")
        if col_s is not None and col_s.notna().any() and col_n is not None:
            ne = float((col_n - col_s).dropna().iloc[0])

    t_min: list[float] = []
    nd_m: list[float] = []
    s_m: list[float] = []
    q_m3h: list[float] = []
    if bombeamento is not None and len(bombeamento):
        t_min = [v for v in bombeamento.get("t_min", pd.Series(dtype=float)).tolist()
                 if pd.notna(v)]
        nd_m = [v for v in bombeamento.get("nd_m", pd.Series(dtype=float)).tolist()
                if pd.notna(v)]
        s_m = [v for v in bombeamento.get("s_m", pd.Series(dtype=float)).tolist()
               if pd.notna(v)]
        q_m3h = [v for v in bombeamento.get("q_m3h", pd.Series(dtype=float)).tolist()
                 if pd.notna(v)]

    if not s_m and nd_m and ne is not None:
        s_m = [v - ne for v in nd_m if v is not None]

    t_linha: list[float] = []
    s_linha: list[float] = []
    if recuperacao is not None and len(recuperacao):
        t_linha = [v for v in recuperacao.get("t_linha_min", pd.Series(dtype=float)).tolist()
                   if pd.notna(v)]
        na = [v for v in recuperacao.get("na_m", pd.Series(dtype=float)).tolist()
              if pd.notna(v)]
        s_li = [v for v in recuperacao.get("s_linha_m", pd.Series(dtype=float)).tolist()
                if pd.notna(v)]
        if not s_li and na and ne is not None:
            s_li = [v - ne for v in na if v is not None]
        s_linha = s_li if len(s_li) == len(t_linha) else []

    tempo_total = planilha.numeric(cad.get("duracao_bombeamento_min"))
    if tempo_total is None and t_min:
        tempo_total = max(t_min)

    # ---- memoria de calculo ----------------------------------------------------------
    res = theis.calcular(
        ne=ne, nd_final=nd,
        tempo_min=t_min, vazao_m3h=q_m3h,
        t_linha_min=t_linha, s_residual_m=s_linha,
        raio_poco_m=planilha.numeric(pouco.get("raio_m")),
        tempo_bombeamento_total_min=tempo_total,
    )

    if usar_q_manual and q_manual:
        res.q_estavel = float(q_manual)
        if res.s_max:
            res.q_capacidade_especifica = res.q_estavel / res.s_max
            if res.T_m2h:
                res.q_longo_prazo = res.T_m2h * C.FATOR_LONGO_PRAZO
                res.Q_ot = res.q_longo_prazo * res.s_max
        res.detalhes["q_estavel_origem"] = "informada manualmente pelo responsavel tecnico"
    else:
        res.detalhes["q_estavel_origem"] = "identificada na planilha (patamar estabilizado)"

    saida["parametros"] = {
        "ne_m": res.ne,
        "nd_m": res.nd_final,
        "s_max_m": res.s_max,
        "q_estavel_m3h": res.q_estavel,
        "delta_s_linha_m": res.delta_s_linha,
        "T_m2h": res.T_m2h,
        "T_m2s": res.T_m2s,
        "q_capacidade_especifica_m3h_m": res.q_capacidade_especifica,
        "q_longo_prazo_m3h_m": res.q_longo_prazo,
        "Q_ot_m3h": res.Q_ot,
        "Q_jacob_lohman_m3h": res.Q_jacob_lohman,
        "tempo_bombeamento_min": res.tempo_bombeamento_min,
        "duracao_h": (res.tempo_bombeamento_min / 60.0) if res.tempo_bombeamento_min else None,
    }
    saida["memoria"] = res.to_dict()
    saida["avisos"] = list(res.avisos)
    saida["erros"] = list(res.erros)

    # ---- series e graficos -----------------------------------------------------------
    serie = theis.serie_rebaixamento(t_min, nd_m, ne)
    tendencia = theis.tendencia_rebaixamento(serie.get("t_min") or [], serie.get("s_m") or [])

    pontos_rec: dict | None = None
    if res.reta is not None and res.reta.x:
        pontos_rec = {"x": res.reta.x, "y": res.reta.y}

    saida["series"] = {
        "bombeamento": {
            "n": len(t_min),
            "t_min": t_min[:400], "nd_m": nd_m[:400], "s_m": s_m[:400],
            "q_m3h": q_m3h[:400],
        },
        "recuperacao": {"n": len(t_linha), "t_linha_min": t_linha[:400],
                        "s_linha_m": s_linha[:400]},
        "tendencia": {k: v for k, v in (tendencia or {}).items()
                      if k not in ("x", "y_hat")},
    }

    if gerar_graficos:
        try:
            nome_poco = cad.get("nome_poco") or (proc.get("poco") or {}).get("nome") or proc.id
            dir_g = proc.dir_graficos
            painel = graficos.gerar_painel(
                serie, tendencia,
                res.reta.to_dict() if res.reta else None,
                pontos_rec,
                dir_g / "graficos_ensaio.png",
                ne=ne, nd_final=nd, profundidade_total_m=profundidade,
                nome_poco=str(nome_poco),
            )
            g1 = graficos.gerar_individual("rebaixamento", dir_g / "grafico_rebaixamento.png",
                                           serie=serie, tendencia=tendencia, ne=ne,
                                           nd_final=nd, profundidade_total_m=profundidade,
                                           nome_poco=str(nome_poco))
            g2 = graficos.gerar_individual("recuperacao", dir_g / "grafico_recuperacao.png",
                                           reta=res.reta.to_dict() if res.reta else None,
                                           pontos_recuperacao=pontos_rec,
                                           nome_poco=str(nome_poco))
            saida["graficos"] = {
                "painel": C.caminho_relativo(painel),
                "rebaixamento": C.caminho_relativo(g1),
                "recuperacao": C.caminho_relativo(g2),
            }
        except Exception as exc:  # noqa: BLE001
            saida["erros"].append(f"Falha ao gerar graficos: {type(exc).__name__}: {exc}")
            saida["erros"].append(traceback.format_exc(limit=6))

    saida["ok"] = bool(res.s_max and res.q_estavel)
    return saida


def tabela_memoria(saida: dict) -> list[dict]:
    """Linhas da tabela 'Parametros Hidraulicos e Resultados do Ensaio'."""
    p = saida.get("parametros", {})
    m = saida.get("memoria", {})

    def f(v, nd=3, un=""):
        if v is None:
            return "-"
        return f"{v:,.{nd}f}{(' ' + un) if un else ''}".replace(",", "X").replace(".", ",").replace("X", ".")

    reta = m.get("reta_recuperacao") or {}
    est = m.get("vazao_estabilizada") or {}
    linhas = [
        ("Nivel estatico (NE)", f(p.get("ne_m"), 2, "m"),
         "Medido a partir da boca do tubo"),
        ("Nivel dinamico estabilizado (ND)", f(p.get("nd_m"), 2, "m"),
         "Fim do bombeamento continuo"),
        ("Rebaixamento maximo (s_max = ND - NE)", f(p.get("s_max_m"), 2, "m"),
         "Rebaixamento maximo observado"),
        ("Vazao estabilizada (Q_estavel)", f(p.get("q_estavel_m3h"), 2, "m3/h"),
         est.get("metodo") or "-"),
        ("Δs' (reta de recuperacao)", f(p.get("delta_s_linha_m"), 4, "m/ciclo"),
         reta.get("equacao") or "-"),
        ("Transmissividade (T)", f(p.get("T_m2h"), 3, "m2/h"),
         "T = 0,183 · Q_estavel / Δs'"),
        ("Transmissividade (T)", f(p.get("T_m2s"), 6, "m2/s"),
         "T(m2/h) / 3600"),
        ("Capacidade especifica do poco (q)", f(p.get("q_capacidade_especifica_m3h_m"), 3, "m3/h/m"),
         "q = Q_estavel / s_max"),
        ("Capacidade especifica de longo prazo (q(t))",
         f(p.get("q_longo_prazo_m3h_m"), 3, "m3/h/m"),
         f"q(t) = 0,8 · T  (fator {C.FATOR_LONGO_PRAZO:g})"),
        ("Vazao otima de explotacao (Q_ot)", f(p.get("Q_ot_m3h"), 2, "m3/h"),
         "Q_ot = q(t) · s_max"),
        ("Contraprova Jacob-Lohman", f(p.get("Q_jacob_lohman_m3h"), 2, "m3/h"),
         "Estimativa independente de longo prazo"),
        ("Duracao do ensaio", f(p.get("duracao_h"), 1, "h"),
         f"{f(p.get('tempo_bombeamento_min'), 0, 'min')}"),
    ]
    return [{"parametro": a, "valor": b, "criterio": c} for a, b, c in linhas]
