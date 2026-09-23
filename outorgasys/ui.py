# -*- coding: utf-8 -*-
"""Componentes de interface partilhados por todas as paginas do Streamlit."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

import streamlit as st

from . import config as C
from .state import Processo, garantir_processo


# --------------------------------------------------------------------------------------
# Tema e cabecalho
# --------------------------------------------------------------------------------------

CSS = """
<style>
  .block-container { padding-top: 1.4rem; padding-bottom: 2.5rem; }
  .out-header {
      border-left: 5px solid #1f4e79; padding: 0.35rem 0 0.35rem 0.85rem;
      margin-bottom: 0.9rem;
  }
  .out-header h2 { margin: 0; font-size: 1.35rem; color: #1f4e79; }
  .out-header p  { margin: 0; font-size: 0.82rem; color: #666; }
  .out-chip {
      display: inline-block; padding: 2px 9px; border-radius: 11px;
      font-size: 0.72rem; font-weight: 600; margin-right: 6px;
  }
  .chip-ok      { background: #e3f2e6; color: #1b5e20; border: 1px solid #a5d6a7; }
  .chip-pend    { background: #fff3e0; color: #e65100; border: 1px solid #ffcc80; }
  .chip-bloq    { background: #fdecea; color: #b71c1c; border: 1px solid #f5a9a9; }
  .chip-info    { background: #e8f0fe; color: #0d47a1; border: 1px solid #b3d4ff; }
  .chip-off     { background: #eceff1; color: #546e7a; border: 1px solid #cfd8dc; }
  .out-panel {
      background: #fbfcfd; border: 1px solid #e3e8ee; border-radius: 8px;
      padding: 0.85rem 1rem; margin-bottom: 0.9rem;
  }
  .out-pend { border-left: 4px solid #e53935; background: #fff8f7;
              padding: 0.5rem 0.8rem; border-radius: 5px; margin-bottom: 0.45rem; }
  .out-aviso { border-left: 4px solid #fb8c00; background: #fffdf5;
               padding: 0.5rem 0.8rem; border-radius: 5px; margin-bottom: 0.45rem; }
  .out-ok    { border-left: 4px solid #43a047; background: #f8fff9;
               padding: 0.5rem 0.8rem; border-radius: 5px; margin-bottom: 0.45rem; }
  .out-step { font-size: 0.78rem; color: #777; }
  div[data-testid="stMetricValue"] { font-size: 1.35rem; }
  .out-fonte { font-size: 0.72rem; color: #888; }
</style>
"""


def aplicar_tema() -> None:
    st.set_page_config(
        page_title="OutorgaSys - SIOUT RS",
        page_icon="💧",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={"About": f"{C.TITULO_SISTEMA}\n\nv{C.VERSAO}"},
    )
    st.markdown(CSS, unsafe_allow_html=True)


def cabecalho(titulo: str, subtitulo: str = "") -> None:
    st.markdown(
        f'<div class="out-header"><h2>{titulo}</h2>'
        f'<p>{subtitulo}</p></div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------------------
# Chips / badges
# --------------------------------------------------------------------------------------


def chip(texto: str, tipo: str = "info") -> str:
    mapa = {"ok": "chip-ok", "pendente": "chip-pend", "bloqueio": "chip-bloq",
            "info": "chip-info", "off": "chip-off", "dispensado": "chip-off"}
    return f'<span class="out-chip {mapa.get(tipo, "chip-info")}">{texto}</span>'


def chips(itens: Iterable[tuple[str, str]]) -> None:
    st.markdown(" ".join(chip(t, k) for t, k in itens), unsafe_allow_html=True)


# --------------------------------------------------------------------------------------
# Pendencias
# --------------------------------------------------------------------------------------


def mostrar_pendencias(pendencias: Sequence[dict], titulo: str = "Pendencias",
                       limite: int | None = None) -> None:
    if not pendencias:
        st.markdown('<div class="out-ok">Nenhuma pendencia registrada.</div>',
                    unsafe_allow_html=True)
        return
    itens = list(pendencias)[:limite] if limite else list(pendencias)
    with st.expander(f"{titulo} ({len(pendencias)})", expanded=len(pendencias) <= 6):
        for p in itens:
            bloqueante = p.get("bloqueante", True)
            classe = "out-pend" if bloqueante else "out-aviso"
            rotulo = "BLOQUEANTE" if bloqueante else "RESSALVA"
            codigo = p.get("codigo", "")
            st.markdown(
                f'<div class="{classe}"><b>{codigo}</b> '
                f'<span class="out-step">[{rotulo}]</span> — '
                f'<b>{p.get("titulo", "")}</b><br/>{p.get("mensagem", "")}'
                + (f'<br/><i>{p["sugestao"]}</i>' if p.get("sugestao") else "")
                + "</div>",
                unsafe_allow_html=True,
            )
    if limite and len(pendencias) > limite:
        st.caption(f"... e mais {len(pendencias) - limite} item(ns).")


def bloco_status(res: dict) -> None:
    """Mostra o resultado de uma validacao como metricas + pendencias."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Bloqueios", res.get("n_bloqueios", 0))
    c2.metric("Ressalvas", res.get("n_avisos", 0))
    c3.metric("Situacao", "LIBERADO" if res.get("ok") else "BLOQUEADO")
    mostrar_pendencias(res.get("bloqueios", []), "Bloqueios")
    if res.get("avisos"):
        mostrar_pendencias(res.get("avisos", []), "Ressalvas e advertencias")


# --------------------------------------------------------------------------------------
# Barra lateral / orquestrador
# --------------------------------------------------------------------------------------


def barra_lateral() -> Processo:
    """Desenha o painel do orquestrador e devolve o processo corrente."""
    proc = garantir_processo(st.session_state)

    with st.sidebar:
        st.markdown("## 💧 OutorgaSys")
        st.caption(f"SIOUT RS · v{C.VERSAO}")

        st.markdown("### Orquestrador")
        concluidos = set(proc.get("agentes_concluidos") or [])
        for num, (nome, desc) in C.AGENTES.items():
            if num in concluidos:
                st.markdown(f'{chip(f"{num}. {nome}", "ok")}', unsafe_allow_html=True)
            else:
                st.markdown(f'{chip(f"{num}. {nome}", "off")}', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Processo")
        st.code(proc.id, language=None)
        st.caption(f"Criado em {proc.get('criado_em')}")
        requerente = (proc.get("requerente") or {}).get("nome")
        municipio = (proc.get("imovel") or {}).get("municipio") or \
            (proc.get("geoespacial") or {}).get("municipio")
        st.caption(f"Requerente: **{requerente or '-'}**")
        st.caption(f"Municipio: **{municipio or '-'}**")

        st.markdown("---")
        with st.expander("Trocar de processo"):
            from .state import Processo as _P

            lista = _P.listar()
            if lista:
                opcoes = {f"{x['id']} — {x['requerente']} ({x['municipio']})": x["id"]
                          for x in lista}
                escolha = st.selectbox("Processos salvos", list(opcoes))
                if st.button("Abrir", width="stretch"):
                    from .state import trocar_processo

                    trocar_processo(st.session_state, opcoes[escolha])
                    st.rerun()
            if st.button("Novo processo", width="stretch"):
                st.session_state.pop("outorgasys_processo_id", None)
                st.rerun()

    return proc


# --------------------------------------------------------------------------------------
# Utilitarios de dados
# --------------------------------------------------------------------------------------


def campo_numero(rotulo: str, valor: Any = None, **kw) -> Any:
    """number_input tolerante a None (Streamlit nao aceita None em min/max)."""
    kwargs = dict(kw)
    kwargs.setdefault("value", float(valor) if valor not in (None, "") else 0.0)
    return st.number_input(rotulo, **kwargs)


def tabela(linhas: Sequence[dict], altura: int | None = None) -> None:
    if not linhas:
        st.info("Sem dados para exibir.")
        return
    try:
        import pandas as pd

        st.dataframe(pd.DataFrame(linhas), hide_index=True, height=altura,
                     width="stretch")
    except Exception:  # noqa: BLE001
        st.json(linhas)


def detalhar(dados: dict, titulo: str = "Detalhes") -> None:
    with st.expander(titulo):
        st.json(dados)


def caminho_absoluto(relativo: str | None) -> Path | None:
    if not relativo:
        return None
    return C.caminho_absoluto(relativo)


def mostrar_imagem(relativo: str | None, legenda: str = "") -> None:
    p = caminho_absoluto(relativo)
    if p and p.exists():
        st.image(str(p), caption=legenda or p.name, width="stretch")
    else:
        st.warning(f"Imagem nao disponivel: {relativo or '-'}")


def download_arquivo(relativo: str | None, rotulo: str = "Descarregar",
                     nome: str | None = None, mime: str | None = None) -> None:
    p = caminho_absoluto(relativo)
    if not p or not p.exists():
        st.button(rotulo, disabled=True, help="Arquivo ainda nao gerado.")
        return
    import mimetypes

    dados = p.read_bytes()
    st.download_button(
        rotulo, data=dados, file_name=nome or p.name,
        mime=mime or (mimetypes.guess_type(p.name)[0] or "application/octet-stream"),
        width="stretch",
    )


def passo(num: int, titulo: str) -> None:
    st.markdown(f'<div class="out-step">PASSO {num} · {titulo.upper()}</div>',
                unsafe_allow_html=True)


def fonte(texto: str) -> None:
    st.markdown(f'<div class="out-fonte">{texto}</div>', unsafe_allow_html=True)
