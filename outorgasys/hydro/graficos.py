# -*- coding: utf-8 -*-
"""
Graficos tecnicos do ensaio de bombeamento (Agente 3).

Painel unico com duas pranchas, exportado em PNG de alta resolucao:

* **Grafico 1 - Rebaixamento x Tempo**: escala horizontal semilogaritmica
  (t em minutos); eixo vertical esquerdo com a profundidade absoluta a partir da
  boca do poco (0 a 150 m ou a profundidade total, invertido) e eixo direito com
  o rebaixamento relativo ``s`` (m). Inclui a reta de tendencia de Cooper-Jacob.
* **Grafico 2 - Recuperacao residual**: escala horizontal semilogaritmica em
  funcao de ``t/t'``; eixo vertical com o rebaixamento residual ``s'`` (m) e a
  reta de recuperacao com a equacao que determina Δs'.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402

from .. import config as C

# Paleta tecnica
AZUL = "#1f4e79"
VERMELHO = "#c00000"
CINZA = "#595959"
VERDE = "#2e7d32"
LARANJA = "#e07b00"


def _fmt(x: float, _pos=None) -> str:
    if x == 0:
        return "0"
    if abs(x) >= 100:
        return f"{x:.0f}"
    if abs(x) >= 10:
        return f"{x:.1f}"
    return f"{x:g}".replace(".", ",")


def _aplicar_estilo(ax, titulo: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(titulo, fontsize=11, fontweight="bold", color="#1a1a1a", pad=10)
    ax.set_xlabel(xlabel, fontsize=9.5)
    ax.set_ylabel(ylabel, fontsize=9.5)
    ax.grid(True, which="major", linestyle="-", linewidth=0.5, color="#cccccc", alpha=0.9)
    ax.grid(True, which="minor", linestyle=":", linewidth=0.4, color="#dddddd", alpha=0.7)
    ax.tick_params(labelsize=8.5)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_color("#999999")
        ax.spines[side].set_linewidth(0.8)


def grafico_rebaixamento(ax, serie: dict, tendencia: dict, ne: float | None,
                         nd_final: float | None, profundidade_total_m: float | None,
                         nome_poco: str = "") -> None:
    """Grafico 1: profundidade absoluta (eixo esq.) e rebaixamento (eixo dir.)."""
    t = list(serie.get("t_min") or [])
    nd = list(serie.get("nd_m") or [])
    s = list(serie.get("s_m") or [])

    profundidade_max = float(profundidade_total_m or 0.0)
    if profundidade_max <= 0:
        profundidade_max = max([v for v in nd if v is not None] + [C.PROFUNDIDADE_EIXO_PADRAO_M])
        profundidade_max = profundidade_max * 1.15
    limite_sup = max(C.PROFUNDIDADE_EIXO_PADRAO_M if profundidade_max <= 0 else profundidade_max, 10.0)

    # Eixo esquerdo: profundidade absoluta a partir da boca do poco (invertido).
    ax.set_xscale("log")
    if t and nd:
        ax.plot(t, nd, marker="o", markersize=3.2, linewidth=1.5, color=AZUL,
                markerfacecolor="white", markeredgewidth=1.0, zorder=5,
                label="Nivel dinamico medido")
    if ne is not None:
        ax.axhline(float(ne), linestyle="--", linewidth=1.2, color=VERDE, zorder=4,
                   label=f"Nivel estatico NE = {float(ne):.2f} m")
    if nd_final is not None:
        ax.axhline(float(nd_final), linestyle=":", linewidth=1.2, color=VERMELHO, zorder=4,
                   label=f"Nivel dinamico estabilizado ND = {float(nd_final):.2f} m")

    # Reta de tendencia projetada sobre o eixo de PROFUNDIDADE (esquerdo).
    if tendencia and t:
        tx = tendencia.get("x") or t
        ty = tendencia.get("y_hat") or []
        if ty and ne is not None:
            profundidade_prevista = [float(ne) + float(v) for v in ty]
            ax.plot(tx, profundidade_prevista, linestyle="-", linewidth=1.6,
                    color=LARANJA, alpha=0.95, zorder=6,
                    label="Reta de tendencia (Cooper-Jacob)")
            ax.annotate(
                tendencia.get("equacao", "").replace("s =", "Δs ="),
                xy=(0.02, 0.03), xycoords="axes fraction",
                fontsize=7.6, color=LARANJA,
                bbox={"boxstyle": "round,pad=0.35", "facecolor": "#fff8ec",
                      "edgecolor": LARANJA, "linewidth": 0.7},
            )

    ax.set_ylim(limite_sup, 0)
    ax.set_xlim(left=max(0.5, min(t) * 0.7 if t else 1.0))
    ax.xaxis.set_major_formatter(FuncFormatter(_fmt))
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt))
    _aplicar_estilo(ax,
                    f"GRAFICO 1 - Rebaixamento x Tempo{'  ·  ' + nome_poco if nome_poco else ''}",
                    "Tempo de bombeamento t (min) - escala logaritmica",
                    "Profundidade a partir da boca do poco (m)")
    ax.legend(loc="lower right", fontsize=7.4, framealpha=0.95, edgecolor="#bbbbbb")

    # Eixo direito: rebaixamento relativo s (m), mesma origem do NE.
    if s and t:
        ax2 = ax.twinx()
        ax2.plot(t, s, marker="s", markersize=0, linewidth=0, alpha=0)  # reserva de escala
        ax2.set_ylim(limite_sup - (float(ne) if ne is not None else 0.0),
                     -(float(ne) if ne is not None else 0.0))
        ax2.set_ylabel("Rebaixamento relativo s (m)", fontsize=9.5, color=VERMELHO)
        ax2.tick_params(axis="y", labelcolor=VERMELHO, labelsize=8.5)
        ax2.yaxis.set_major_formatter(FuncFormatter(_fmt))
        ax2.spines["right"].set_color(VERMELHO)
        ax2.grid(False)


def grafico_recuperacao(ax, reta: dict | None, pontos: dict | None,
                        nome_poco: str = "") -> None:
    """Grafico 2: rebaixamento residual s' x t/t' (escala semilog)."""
    ax.set_xscale("log")
    if pontos and pontos.get("x"):
        ax.plot(pontos["x"], pontos["y"], marker="o", markersize=3.4, linewidth=0,
                color=AZUL, markerfacecolor="white", markeredgewidth=1.1, zorder=5,
                label="Rebaixamento residual medido s'")

    if reta and reta.get("delta_s_linha") is not None:
        xs = reta.get("x") or []
        ys = reta.get("y_ajustado") or []
        if xs and ys:
            ordem = sorted(range(len(xs)), key=lambda i: xs[i])
            xs = [xs[i] for i in ordem]
            ys = [ys[i] for i in ordem]
            ax.plot(xs, ys, linestyle="-", linewidth=1.8, color=VERMELHO, zorder=6,
                    label="Reta de recuperacao ajustada")

            # Extensao de um ciclo logaritmico a partir do primeiro ponto,
            # evidenciando graficamente o Δs'.
            x0 = max(xs[0], min(x for x in xs if x > 0))
            x1 = x0 * 10.0
            if x1 <= max(xs) * 1.0001:
                y0 = ys[min(range(len(xs)), key=lambda i: abs(xs[i] - x0))]
                y1 = y0 + (reta.get("inclinacao") or 0.0)
                ax.annotate(
                    "", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops={"arrowstyle": "<->", "color": VERDE, "linewidth": 1.2},
                )
                ax.annotate(
                    f"Δs' = {reta['delta_s_linha']:.4f} m/ciclo",
                    xy=(x0 * 3.2, (y0 + y1) / 2), fontsize=8, color=VERDE, fontweight="bold",
                    bbox={"boxstyle": "round,pad=0.3", "facecolor": "#eef7ee",
                          "edgecolor": VERDE, "linewidth": 0.7},
                )

        equacao = reta.get("equacao", "")
        if equacao:
            ax.annotate(
                equacao.replace("log10(t/t')", "log₁₀(t/t')"),
                xy=(0.02, 0.04), xycoords="axes fraction", fontsize=7.8, color=VERMELHO,
                bbox={"boxstyle": "round,pad=0.35", "facecolor": "#fff5f5",
                      "edgecolor": VERMELHO, "linewidth": 0.7},
            )
        metodo = reta.get("metodo", "")
        if metodo:
            ax.annotate(f"Ajuste: {metodo} · n = {reta.get('n_pontos', 0)}",
                        xy=(0.02, 0.96), xycoords="axes fraction", fontsize=7.2,
                        color=CINZA, va="top")
    else:
        ax.text(0.5, 0.5, "Fase de recuperacao nao informada\nou insuficiente",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=10, color=CINZA,
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "#f5f5f5",
                      "edgecolor": "#cccccc"})

    ax.xaxis.set_major_formatter(FuncFormatter(_fmt))
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt))
    _aplicar_estilo(ax,
                    f"GRAFICO 2 - Recuperacao residual{'  ·  ' + nome_poco if nome_poco else ''}",
                    "Tempo relativo t / t'  (adimensional) - escala logaritmica",
                    "Rebaixamento residual s' (m)")
    ax.legend(loc="upper right", fontsize=7.6, framealpha=0.95, edgecolor="#bbbbbb")


def gerar_painel(serie: dict, tendencia: dict, reta: dict | None,
                 pontos_recuperacao: dict | None, destino: Path,
                 ne: float | None = None, nd_final: float | None = None,
                 profundidade_total_m: float | None = None,
                 nome_poco: str = "", dpi: int = C.DPI_MAPAS) -> Path:
    """Renderiza os dois graficos lado a lado num unico painel PNG."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.6), dpi=dpi)
    grafico_rebaixamento(axes[0], serie, tendencia, ne, nd_final,
                         profundidade_total_m, nome_poco)
    grafico_recuperacao(axes[1], reta, pontos_recuperacao, nome_poco)

    fig.suptitle(
        "Ensaio de Bombeamento - Interpretacao de Rebaixamento e Recuperacao\n"
        "(Metodos de Theis / Cooper-Jacob)",
        fontsize=13, fontweight="bold", y=0.985,
    )
    fig.text(0.5, 0.008,
             "Escala horizontal semilogaritmica · Eixo esquerdo do Grafico 1 em "
             "profundidade absoluta a partir da boca do poco (invertido)",
             ha="center", fontsize=7.6, color=CINZA)
    fig.tight_layout(rect=(0, 0.028, 1, 0.94))
    fig.savefig(destino, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return destino


def gerar_individual(qual: str, destino: Path, **kw) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9.2, 6.0), dpi=C.DPI_MAPAS)
    if qual == "rebaixamento":
        grafico_rebaixamento(ax, kw.get("serie") or {}, kw.get("tendencia") or {},
                             kw.get("ne"), kw.get("nd_final"),
                             kw.get("profundidade_total_m"), kw.get("nome_poco", ""))
    else:
        grafico_recuperacao(ax, kw.get("reta"), kw.get("pontos_recuperacao"),
                            kw.get("nome_poco", ""))
    fig.tight_layout()
    fig.savefig(destino, dpi=C.DPI_MAPAS, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return destino
