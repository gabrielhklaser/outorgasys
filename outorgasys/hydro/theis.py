# -*- coding: utf-8 -*-
"""
Motor de calculo hidrogeologico (Agente 3).

Implementa a memoria de calculo exigida pelo SIOUT RS, com os metodos:

* **Cooper-Jacob (recuperacao)**: reta de ``s'`` (rebaixamento residual) contra
  ``log10(t/t')``; o coeficiente angular da reta estabilizada e o ``Δs'``.
* **Theis / Cooper-Jacob (transmissividade)**: ``T = 0,183 * Q_estavel / Δs'``.
* **Capacidade especifica do poco**: ``q = Q_estavel / s_max``.
* **Capacidade especifica de longo prazo do campo**: ``q(t) = 0,8 * T``.
* **Vazao otima de explotacao**: ``Q_ot = q(t) * s_max``.
* **Jacob-Lohman** (regime permanente com recarga por limite): estimativa
  independente de vazao sustentavel de longo prazo, usada como contraprova.

Seguindo a convencao do manual de campo, ``Δs'`` e tomado em modulo: a reta de
recuperacao tem inclinacao negativa (o rebaixamento residual decai com o tempo).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from .. import config as C


# --------------------------------------------------------------------------------------
# Utilidades numericas
# --------------------------------------------------------------------------------------


def _arr(v: Sequence[Any]) -> np.ndarray:
    a = np.asarray([float(x) if x is not None and x == x else np.nan for x in v], dtype=float)
    return a


def _finito(a: np.ndarray) -> np.ndarray:
    return np.isfinite(a)


def coeficiente_variacao(a: np.ndarray) -> float:
    a = a[_finito(a)]
    if len(a) < 2:
        return float("nan")
    m = float(np.mean(a))
    if abs(m) < 1e-12:
        return float("nan")
    return float(np.std(a, ddof=0) / abs(m))


# --------------------------------------------------------------------------------------
# Vazao estabilizada
# --------------------------------------------------------------------------------------


@dataclass
class VazaoEstabilizada:
    q_estavel: float | None
    indice_inicio: int | None
    n_pontos: int
    cv: float | None
    metodo: str
    serie: list[float] = field(default_factory=list)
    tempo_inicio_min: float | None = None
    observacao: str = ""

    def to_dict(self) -> dict:
        return {
            "q_estavel": self.q_estavel,
            "indice_inicio": self.indice_inicio,
            "n_pontos": self.n_pontos,
            "cv": self.cv,
            "metodo": self.metodo,
            "tempo_inicio_min": self.tempo_inicio_min,
            "observacao": self.observacao,
        }


def identificar_q_estavel(tempo_min: Sequence[Any],
                          vazao_m3h: Sequence[Any],
                          tolerancia_cv: float = 0.10,
                          fracao_minima: float = 0.25) -> VazaoEstabilizada:
    """Identifica a vazao estabilizada final de operacao (Q_estavel).

    Criterio: percorre janelas terminais da serie (da menor para a maior) e adota
    a maior janela cujo coeficiente de variacao fique abaixo de
    ``tolerancia_cv`` - ou seja, o trecho final em patamar continuo, conforme os
    criterios de regime permanente. Se nenhuma janela estabilizar, usa a mediana
    do ultimo terco da serie e sinaliza a ressalva.
    """
    t, q = _arr(tempo_min), _arr(vazao_m3h)
    mask = _finito(t) & _finito(q) & (q > 0)
    t, q = t[mask], q[mask]
    n = len(q)
    if n == 0:
        return VazaoEstabilizada(None, None, 0, None, "sem dados",
                                 observacao="Nenhuma vazao valida informada.")
    if n < 3:
        return VazaoEstabilizada(float(np.median(q)), 0, n, 0.0, "mediana (serie curta)",
                                 serie=q.tolist(), tempo_inicio_min=float(t[0]),
                                 observacao="Serie de vazoes muito curta para teste de "
                                            "estabilizacao; adotada a mediana.")

    # Ordena por tempo e garante monotonicidade crescente.
    ordem = np.argsort(t, kind="stable")
    t, q = t[ordem], q[ordem]

    minimo = max(3, int(math.ceil(fracao_minima * n)))
    melhor: VazaoEstabilizada | None = None
    for i in range(n, minimo - 1, -1):
        janela = q[:i][-i:] if False else q[n - i:]  # ultimos i pontos
        cv = coeficiente_variacao(janela)
        if math.isfinite(cv) and cv <= tolerancia_cv:
            # Quanto maior a janela, melhor (percorremos de tras para frente).
            melhor = VazaoEstabilizada(
                q_estavel=float(np.mean(janela)),
                indice_inicio=int(n - i),
                n_pontos=int(i),
                cv=float(cv),
                metodo="patamar terminal (CV <= %.0f%%)" % (tolerancia_cv * 100),
                serie=janela.tolist(),
                tempo_inicio_min=float(t[n - i]),
                observacao=f"Patamar de {i} leituras a partir de t = {t[n - i]:.0f} min "
                           f"(CV = {cv * 100:.1f}%).",
            )
            break

    if melhor is not None:
        # Amplia a janela enquanto o CV continuar aceitavel.
        i = melhor.n_pontos
        while i < n:
            janela = q[n - (i + 1):]
            cv = coeficiente_variacao(janela)
            if not (math.isfinite(cv) and cv <= tolerancia_cv):
                break
            i += 1
            melhor = VazaoEstabilizada(
                q_estavel=float(np.mean(janela)),
                indice_inicio=int(n - i),
                n_pontos=int(i),
                cv=float(cv),
                metodo=melhor.metodo,
                serie=janela.tolist(),
                tempo_inicio_min=float(t[n - i]),
                observacao=f"Patamar de {i} leituras a partir de t = {t[n - i]:.0f} min "
                           f"(CV = {cv * 100:.1f}%).",
            )
        return melhor

    # Sem patamar CV-baixo: cai para o ultimo terco.
    corte = max(1, int(n * 2 / 3))
    janela = q[corte:]
    cv = coeficiente_variacao(janela)
    return VazaoEstabilizada(
        q_estavel=float(np.median(janela)),
        indice_inicio=int(corte),
        n_pontos=int(len(janela)),
        cv=float(cv) if math.isfinite(cv) else None,
        metodo="mediana do ultimo terco (sem patamar CV-baixo)",
        serie=janela.tolist(),
        tempo_inicio_min=float(t[corte]),
        observacao="Nao foi identificado patamar com CV <= %.0f%%; adotou-se a mediana "
                   "do ultimo terco da serie. Revise a planilha." % (tolerancia_cv * 100),
    )


# --------------------------------------------------------------------------------------
# Ajuste da reta de recuperacao (Cooper-Jacob)
# --------------------------------------------------------------------------------------


@dataclass
class RetaRecuperacao:
    delta_s_linha: float | None       # Δs' em m por ciclo logaritmico (modulo)
    inclinacao: float | None          # coeficiente angular bruto (pode ser negativo)
    intercepto: float | None
    r2: float | None
    n_pontos: int
    metodo: str
    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)
    y_ajustado: list[float] = field(default_factory=list)
    observacao: str = ""

    @property
    def equacao(self) -> str:
        if self.inclinacao is None or self.intercepto is None:
            return "-"
        s = f"s' = {self.inclinacao:+.4f}·log10(t/t') {self.intercepto:+.4f}"
        if self.r2 is not None:
            s += f"   (R² = {self.r2:.4f})"
        return s

    def to_dict(self) -> dict:
        return {
            "delta_s_linha": self.delta_s_linha,
            "inclinacao": self.inclinacao,
            "intercepto": self.intercepto,
            "r2": self.r2,
            "n_pontos": self.n_pontos,
            "metodo": self.metodo,
            "equacao": self.equacao,
            "observacao": self.observacao,
        }


def ajustar_reta_recuperacao(t_sobre_tlinha: Sequence[Any],
                             s_residual_m: Sequence[Any],
                             metodo: str = "theil-sen") -> RetaRecuperacao:
    """Ajusta ``s'`` contra ``log10(t/t')`` e devolve Δs' (modulo)."""
    x_raw, y = _arr(t_sobre_tlinha), _arr(s_residual_m)
    mask = _finito(x_raw) & _finito(y) & (x_raw > 0)
    x_raw, y = x_raw[mask], y[mask]
    if len(x_raw) < 2:
        return RetaRecuperacao(None, None, None, None, int(len(x_raw)), "sem dados",
                               observacao="Menos de dois pontos validos de recuperacao.")

    x = np.log10(x_raw)
    n = len(x)

    if n == 2:
        b = (y[1] - y[0]) / (x[1] - x[0])
        a = y[0] - b * x[0]
        return RetaRecuperacao(
            abs(b), b, a, None, 2, "dois pontos",
            x=x_raw.tolist(), y=y.tolist(), y_ajustado=(a + b * x).tolist(),
            observacao="Apenas dois pontos: ajuste exato, sem estatistica de qualidade.",
        )

    try:
        from scipy import stats  # noqa: PLC0415

        res = stats.theilslopes(y, x, 0.95)
        b, a = float(res[0]), float(res[1])
        metodo_usado = "Theil-Sen (robusto)"
    except Exception:  # noqa: BLE001
        b, a = np.polyfit(x, y, 1)
        b, a = float(b), float(a)
        metodo_usado = "minimos quadrados"

    y_hat = a + b * x
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else None

    obs = ""
    if r2 is not None and r2 < 0.85:
        obs = (f"Ajuste com R² = {r2:.3f} (baixo). Verifique se a fase de recuperacao "
               "foi registrada corretamente e se ha leituras ruidosas.")
    if b > 0:
        obs = (obs + " " if obs else "") + (
            "Coeficiente angular positivo: o rebaixamento residual deveria decair "
            "com t/t'. Confira a planilha de recuperacao.")

    return RetaRecuperacao(
        delta_s_linha=abs(float(b)),
        inclinacao=float(b),
        intercepto=float(a),
        r2=r2,
        n_pontos=int(n),
        metodo=metodo_usado,
        x=x_raw.tolist(), y=y.tolist(), y_ajustado=y_hat.tolist(),
        observacao=obs or f"Ajuste {metodo_usado} sobre {n} pontos.",
    )


# --------------------------------------------------------------------------------------
# Memoria de calculo completa
# --------------------------------------------------------------------------------------


@dataclass
class ResultadoHidraulico:
    ok: bool
    s_max: float | None = None
    ne: float | None = None
    nd_final: float | None = None
    q_estavel: float | None = None
    delta_s_linha: float | None = None
    T_m2h: float | None = None
    T_m2s: float | None = None
    q_capacidade_especifica: float | None = None
    q_longo_prazo: float | None = None
    Q_ot: float | None = None
    Q_jacob_lohman: float | None = None
    tempo_bombeamento_min: float | None = None
    vazao_estabilizada: VazaoEstabilizada | None = None
    reta: RetaRecuperacao | None = None
    avisos: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)
    detalhes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "ok": self.ok,
            "s_max": self.s_max,
            "ne": self.ne,
            "nd_final": self.nd_final,
            "q_estavel": self.q_estavel,
            "delta_s_linha": self.delta_s_linha,
            "T_m2h": self.T_m2h,
            "T_m2s": self.T_m2s,
            "q_capacidade_especifica": self.q_capacidade_especifica,
            "q_longo_prazo": self.q_longo_prazo,
            "Q_ot": self.Q_ot,
            "Q_jacob_lohman": self.Q_jacob_lohman,
            "tempo_bombeamento_min": self.tempo_bombeamento_min,
            "vazao_estabilizada": self.vazao_estabilizada.to_dict() if self.vazao_estabilizada else None,
            "reta_recuperacao": self.reta.to_dict() if self.reta else None,
            "avisos": self.avisos,
            "erros": self.erros,
            "detalhes": self.detalhes,
        }
        return d


def calcular(ne: float | None, nd_final: float | None,
             tempo_min: Sequence[Any] | None = None,
             vazao_m3h: Sequence[Any] | None = None,
             t_linha_min: Sequence[Any] | None = None,
             s_residual_m: Sequence[Any] | None = None,
             raio_poco_m: float | None = None,
             tempo_bombeamento_total_min: float | None = None) -> ResultadoHidraulico:
    """Executa a memoria de calculo completa descrita no prompt do Agente 3."""
    avisos: list[str] = []
    erros: list[str] = []
    detalhes: dict = {}

    ne_f = float(ne) if ne is not None else None
    nd_f = float(nd_final) if nd_final is not None else None

    # 1) Rebaixamento maximo ----------------------------------------------------------
    s_max = None
    if ne_f is not None and nd_f is not None:
        s_max = nd_f - ne_f
        if s_max <= 0:
            erros.append(
                "Rebaixamento maximo nao positivo (ND deve ser mais profundo que NE). "
                f"NE = {ne_f:g} m, ND = {nd_f:g} m."
            )
            s_max = None
        elif s_max < 0.05:
            avisos.append(
                f"Rebaixamento maximo de apenas {s_max:.3f} m: ensaio de baixa "
                "sensibilidade, os parametros derivados tem pouca representatividade."
            )
    else:
        erros.append("NE e/ou ND nao informados: impossivel calcular s_max.")

    # 2) Vazao estabilizada -----------------------------------------------------------
    est = identificar_q_estavel(tempo_min or [], vazao_m3h or [])
    q_estavel = est.q_estavel
    if q_estavel is None:
        erros.append("Nao foi possivel identificar a vazao estabilizada (Q_estavel).")
    if est.observacao:
        detalhes["observacao_vazao"] = est.observacao
    if est.cv is not None and est.cv > 0.10:
        avisos.append(
            f"Vazao com variabilidade de {est.cv * 100:.1f}% no trecho adotado; "
            "o ensaio pode nao ter atingido regime permanente."
        )

    # 3-4) Recuperacao e transmissividade ---------------------------------------------
    t_total = float(tempo_bombeamento_total_min) if tempo_bombeamento_total_min else None
    if t_total is None and tempo_min:
        tt = _arr(tempo_min)
        tt = tt[_finito(tt)]
        t_total = float(tt.max()) if len(tt) else None
    detalhes["t_bombeamento_total_min"] = t_total

    reta: RetaRecuperacao | None = None
    if t_linha_min and s_residual_m and t_total:
        tl = _arr(t_linha_min)
        tl = tl[_finito(tl) & (tl >= 0)]
        if len(tl) >= 2:
            # t / t' com t = t_bombeamento_total + t' (convencao do enunciado)
            t_abs = t_total + tl
            with np.errstate(divide="ignore", invalid="ignore"):
                razao = np.where(tl > 0, t_abs / tl, np.nan)
            reta = ajustar_reta_recuperacao(razao, s_residual_m)
            if reta.observacao:
                detalhes["observacao_recuperacao"] = reta.observacao
        else:
            avisos.append("Fase de recuperacao incompleta: transmissividade nao calculada.")
    else:
        avisos.append(
            "Sem dados de recuperacao: transmissividade (T) e Q_ot nao podem ser "
            "calculados pelos metodos de Theis/Cooper-Jacob."
        )

    delta = reta.delta_s_linha if reta else None
    T_m2h = T_m2s = None
    if q_estavel and delta and delta > 1e-9:
        T_m2h = (C.COEF_COOPER_JACOB * q_estavel) / delta
        T_m2s = T_m2h / 3600.0
        if not (1e-4 <= T_m2s <= 1.0):
            avisos.append(
                f"Transmissividade de {T_m2s:.2e} m2/s fora da faixa usual para "
                "aquiferos brasileiros (1e-5 a 1e-1 m2/s). Confira Δs' e Q_estavel."
            )
    elif delta is not None and delta <= 1e-9:
        avisos.append("Δs' nulo ou desprezivel: reta de recuperacao horizontal, "
                      "transmissividade indeterminada.")

    # 5) Capacidade especifica do poco -------------------------------------------------
    q_ce = (q_estavel / s_max) if (q_estavel and s_max) else None

    # 6) Capacidade especifica de longo prazo do campo ---------------------------------
    q_lp = (T_m2h * C.FATOR_LONGO_PRAZO) if T_m2h else None

    # 7) Vazao otima de explotacao -----------------------------------------------------
    Q_ot = (q_lp * s_max) if (q_lp and s_max) else None

    # Contraprova de Jacob-Lohman -------------------------------------------------------
    Q_jl = None
    if T_m2h and s_max:
        # Q = 2*pi*T*s / ln(2.25*T*t/(r^2*S)), com S de 1e-4 e t de 1 ano (525600 min)
        # em unidades consistentes (m, h). Usado apenas como ordem de grandeza.
        r = raio_poco_m if raio_poco_m and raio_poco_m > 0 else 0.10
        S = 1e-4
        T_m2_dia = T_m2h * 24.0
        t_dia = 365.0
        try:
            arg = (2.25 * T_m2_dia * t_dia) / (r * r * S)
            if arg > 1.0:
                Q_jl = (2 * math.pi * T_m2_dia * s_max) / math.log(arg) / 24.0  # m3/h
                detalhes["jacob_lohman"] = {"raio_m": r, "S_adotado": S,
                                            "t_dias": t_dia, "arg": arg}
        except Exception:  # noqa: BLE001
            Q_jl = None

    return ResultadoHidraulico(
        ok=bool(s_max and q_estavel and T_m2h),
        s_max=s_max, ne=ne_f, nd_final=nd_f, q_estavel=q_estavel,
        delta_s_linha=delta, T_m2h=T_m2h, T_m2s=T_m2s,
        q_capacidade_especifica=q_ce, q_longo_prazo=q_lp, Q_ot=Q_ot,
        Q_jacob_lohman=Q_jl, tempo_bombeamento_min=t_total,
        vazao_estabilizada=est, reta=reta, avisos=avisos, erros=erros,
        detalhes=detalhes,
    )


# --------------------------------------------------------------------------------------
# Serie derivada: rebaixamento ao longo do bombeamento
# --------------------------------------------------------------------------------------


def serie_rebaixamento(tempo_min: Sequence[Any], nivel_dinamico_m: Sequence[Any],
                       ne: float | None) -> dict:
    """Monta a serie usada pelo Grafico 1."""
    t = _arr(tempo_min)
    nd = _arr(nivel_dinamico_m)
    mask = _finito(t) & _finito(nd)
    t, nd = t[mask], nd[mask]
    ordem = np.argsort(t, kind="stable")
    t, nd = t[ordem], nd[ordem]

    s = None
    if ne is not None:
        ne_f = float(ne)
        s = np.where(_finito(nd), nd - ne_f, np.nan)

    return {
        "t_min": t.tolist(),
        "nd_m": nd.tolist(),
        "s_m": (s.tolist() if s is not None else []),
        "n": int(len(t)),
    }


def tendencia_rebaixamento(t_min: Sequence[Any], s_m: Sequence[Any]) -> dict:
    """Ajuste semilogaritmico de Cooper-Jacob na fase de bombeamento.

    ``s = A + B*log10(t)`` -> usado para desenhar a reta de tendencia do Grafico 1.
    """
    t, s = _arr(t_min), _arr(s_m)
    mask = _finito(t) & _finito(s) & (t > 0)
    t, s = t[mask], s[mask]
    if len(t) < 3:
        return {}
    x = np.log10(t)
    try:
        b, a = np.polyfit(x, s, 1)
    except Exception:  # noqa: BLE001
        return {}
    y_hat = a + b * x
    ss_res = float(np.sum((s - y_hat) ** 2))
    ss_tot = float(np.sum((s - np.mean(s)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else None
    return {
        "a": float(a), "b": float(b), "r2": r2,
        "equacao": f"s = {b:+.4f}·log10(t) {a:+.4f}"
                   + (f"   (R² = {r2:.4f})" if r2 is not None else ""),
        "x": t.tolist(), "y_hat": y_hat.tolist(),
    }
