# -*- coding: utf-8 -*-
"""
Modelo (.xlsx) e ingestao da planilha de ensaio de bombeamento (Agente 3).

Descarga: o botao do Agente 1 entrega uma planilha-padrao em etapa unica com as
abas de cadastro, bombeamento (rebaixamento) e recuperacao.

Ingestao: a leitura e tolerante a variacoes de rotulo de coluna e de nome de aba
(planilhas de campo raramente seguem o modelo a risca).
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .. import config as C


# --------------------------------------------------------------------------------------
# Modelo para descarga
# --------------------------------------------------------------------------------------

ABA_CADASTRO = "01_Cadastro"
ABA_BOMBEAMENTO = "02_Bombeamento"
ABA_RECUPERACAO = "03_Recuperacao"
ABA_ORIENTACOES = "04_Orientacoes"

CAMPOS_CADASTRO: list[tuple[str, str, Any]] = [
    ("nome_cliente", "Nome do cliente / requerente", ""),
    ("municipio", "Municipio", ""),
    ("uf", "UF", "RS"),
    ("nome_poco", "Nome / identificacao do poco", ""),
    ("profundidade_total_m", "Profundidade total do poco (m)", ""),
    ("altura_boca_tubo_m", "Altura da boca do tubo (m)", ""),
    ("nivel_estatico_m", "Nivel estatico NE (m, a partir da boca)", ""),
    ("nivel_dinamico_m", "Nivel dinamico estabilizado ND (m, a partir da boca)", ""),
    ("posicao_crivo_de_m", "Posicao do crivo - de (m)", ""),
    ("posicao_crivo_ate_m", "Posicao do crivo - ate (m)", ""),
    ("diametro_util_pol", "Diametro util do poco (pol)", ""),
    ("data_ensaio", "Data do ensaio", ""),
    ("responsavel_tecnico", "Responsavel tecnico", ""),
    ("registro_profissional", "Registro profissional (CREA)", ""),
]

ORIENTACOES = [
    ("Objetivo",
     "Registrar o ensaio de bombeamento continuo de 24 horas e o ensaio de "
     "recuperacao, conforme exigido pelo SIOUT RS para pocos tubulares profundos "
     "(diametro util >= 4 pol)."),
    ("Aba 01_Cadastro",
     "Preencha os metadados do poco. NE e ND sao medidos a partir da boca do tubo, "
     "em metros, com duas casas decimais."),
    ("Aba 02_Bombeamento",
     "Uma linha por leitura. 't' e o tempo decorrido desde o inicio do bombeamento, "
     "em MINUTOS. 'ND' e o nivel dinamico medido naquele instante (m a partir da "
     "boca). 's' e calculado automaticamente como ND - NE. 'Q' e a vazao "
     "instantanea em m3/h. Frequencia sugerida: 1, 2, 3, 5, 10, 15, 20, 30, 45 e "
     "60 min, depois de hora em hora ate 24 h."),
    ("Aba 03_Recuperacao",
     "Uma linha por leitura apos o DESLIGAMENTO da bomba. \"t'\" e o tempo decorrido "
     "desde o desligamento, em MINUTOS. 'NA' e o nivel da agua no poco naquele "
     "instante (m a partir da boca). \"s'\" e calculado como NA - NE. A frequencia "
     "deve ser a mesma da fase de bombeamento e o ensaio deve seguir ate a "
     "recuperacao total ou por periodo igual ao de bombeamento."),
    ("Cuidados",
     "Mantenha a vazao constante durante o ensaio; registre qualquer interrupcao em "
     "'Observacoes'; use o mesmo referencial (boca do tubo) em todas as medicoes; "
     "nao altere o regime da bomba durante as 24 h."),
    ("Formatos aceitos",
     ".xlsx (este modelo), .xls e .csv. No CSV use ponto-e-virgula ou virgula como "
     "separador e virgula decimal opcional."),
]


def _norm(s: Any) -> str:
    """Normaliza rotulos de coluna para comparacao tolerante."""
    s = str(s or "").strip().lower()
    s = re.sub(r"[\s_/\\]+", "", s)
    s = (s.replace("á", "a").replace("à", "a").replace("ã", "a").replace("â", "a")
          .replace("é", "e").replace("ê", "e").replace("í", "i")
          .replace("ó", "o").replace("ô", "o").replace("õ", "o")
          .replace("ú", "u").replace("ç", "c"))
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def gerar_modelo(cadastro: dict | None = None,
                 bombeamento: list[dict] | None = None,
                 recuperacao: list[dict] | None = None) -> bytes:
    """Devolve os bytes de um .xlsx com o modelo de planilha de ensaio."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    cadastro = cadastro or {}

    linhas_cad = []
    for chave, rotulo, padrao in CAMPOS_CADASTRO:
        valor = cadastro.get(chave, padrao)
        linhas_cad.append({"campo": rotulo, "chave_interna": chave,
                           "valor": "" if valor in (None, "") else valor})
    df_cad = pd.DataFrame(linhas_cad)

    if not bombeamento:
        # Grade sugerida de leituras para 24 h (em minutos).
        grade = [1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60]
        grade += list(range(90, 1441, 30))
        bombeamento = [{"t_min": t} for t in grade]
    df_bom = pd.DataFrame(bombeamento)
    for col in ("t_min", "nd_m", "q_m3h", "observacoes"):
        if col not in df_bom.columns:
            df_bom[col] = "" if col == "observacoes" else None
    df_bom["s_m"] = ""
    df_bom = df_bom[["t_min", "nd_m", "s_m", "q_m3h", "observacoes"]]
    df_bom.columns = ["t (min)", "ND (m)", "s (m) = ND - NE", "Q (m3/h)", "Observacoes"]

    if not recuperacao:
        grade_r = [1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60]
        grade_r += list(range(90, 1441, 30))
        recuperacao = [{"t_linha_min": t} for t in grade_r]
    df_rec = pd.DataFrame(recuperacao)
    for col in ("t_linha_min", "na_m", "observacoes"):
        if col not in df_rec.columns:
            df_rec[col] = "" if col == "observacoes" else None
    df_rec["s_linha_m"] = ""
    df_rec = df_rec[["t_linha_min", "na_m", "s_linha_m", "observacoes"]]
    df_rec.columns = ["t' (min)", "NA (m)", "s' (m) = NA - NE", "Observacoes"]

    df_ori = pd.DataFrame(ORIENTACOES, columns=["Topico", "Orientacao"])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_cad.to_excel(writer, sheet_name=ABA_CADASTRO, index=False)
        df_bom.to_excel(writer, sheet_name=ABA_BOMBEAMENTO, index=False)
        df_rec.to_excel(writer, sheet_name=ABA_RECUPERACAO, index=False)
        df_ori.to_excel(writer, sheet_name=ABA_ORIENTACOES, index=False)

        wb = writer.book
        cabecalho_fill = PatternFill("solid", fgColor="1F4E79")
        cabecalho_font = Font(color="FFFFFF", bold=True, size=10)

        for nome in (ABA_CADASTRO, ABA_BOMBEAMENTO, ABA_RECUPERACAO, ABA_ORIENTACOES):
            ws = wb[nome]
            for celula in ws[1]:
                celula.fill = cabecalho_fill
                celula.font = cabecalho_font
                celula.alignment = Alignment(horizontal="center", vertical="center",
                                             wrap_text=True)
            ws.freeze_panes = "A2"
            larguras = {}
            for linha in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 200)):
                for c in linha:
                    if c.value is None:
                        continue
                    larguras[c.column] = min(60, max(larguras.get(c.column, 10),
                                                     len(str(c.value)) + 2))
            for col, largura in larguras.items():
                ws.column_dimensions[get_column_letter(col)].width = largura
            if nome == ABA_ORIENTACOES:
                for row in ws.iter_rows(min_row=2):
                    for c in row:
                        c.alignment = Alignment(wrap_text=True, vertical="top")

        # Formulas de rebaixamento: s = ND - NE, s' = NA - NE.
        wb[ABA_BOMBEAMENTO]["C2"] = (
            f'=IF(OR(B2="",\'{ABA_CADASTRO}\'!$C$7=""),"",B2-\'{ABA_CADASTRO}\'!$C$7)'
        )
        wb[ABA_RECUPERACAO]["C2"] = (
            f'=IF(OR(B2="",\'{ABA_CADASTRO}\'!$C$7=""),"",B2-\'{ABA_CADASTRO}\'!$C$7)'
        )

    return buf.getvalue()


def salvar_modelo(destino: Path, **kw) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(gerar_modelo(**kw))
    return destino


# --------------------------------------------------------------------------------------
# Ingestao
# --------------------------------------------------------------------------------------

ALIASES = {
    "t_min": {"tmin", "t", "tempo", "tempomin", "tempominutos", "tminutos",
              "tempodecorridomin", "tminbombeamento"},
    "nd_m": {"nd", "ndm", "niveldinamico", "niveldinamicoestabilizado", "ndm",
             "niveldinamicom", "nivelaguanapoco", "ndm"},
    "s_m": {"s", "sm", "rebaixamento", "rebaixamentom", "sm", "abaixamento"},
    "q_m3h": {"q", "qm3h", "vazao", "vazaom3h", "vazaoinstantanea", "qm3/h",
              "vazao_m3/h", "q_m3/h", "vazao_m3h", "qinst", "vazaomedida"},
    "t_linha_min": {"tlinha", "tlinhamin", "t", "temporecuperacao",
                    "temporecuperacaomin", "tlinha", "t", "tempominrecuperacao",
                    "tempodesdeodesligamentomin"},
    "na_m": {"na", "nam", "nivelagua", "nivelresidual", "nivelmedido", "nam",
             "niveldaguam"},
    "s_linha_m": {"slinha", "slinham", "rebaixamentoresidual", "rebaixamentoresidualm",
                  "s", "slinha(m)"},
    "observacoes": {"observacoes", "observacao", "obs", "notas"},
}

ALIASES_CADASTRO = {chave: {_norm(rotulo), _norm(chave)}
                    for chave, rotulo, _ in CAMPOS_CADASTRO}


def _mapear_colunas(df: pd.DataFrame) -> dict[str, str]:
    """Associa colunas do arquivo aos nomes internos conhecidos."""
    mapa: dict[str, str] = {}
    usadas: set[str] = set()
    for col in df.columns:
        n = _norm(col)
        for interno, aliases in ALIASES.items():
            if interno in mapa:
                continue
            if n in aliases or n.replace("m3h", "m3h") in aliases:
                mapa[interno] = col
                usadas.add(col)
                break
    return mapa


def ler_planilha(caminho: Path | bytes | Any) -> dict:
    """Le a planilha enviada e devolve estrutura normalizada.

    Retorna:
        {
          "ok": bool,
          "cadastro": {...},
          "bombeamento": DataFrame(t_min, nd_m, s_m, q_m3h),
          "recuperacao": DataFrame(t_linha_min, na_m, s_linha_m),
          "avisos": [...],
          "erros": [...],
          "abas": [...],
        }
    """
    avisos: list[str] = []
    erros: list[str] = []

    if hasattr(caminho, "read"):     # UploadedFile do Streamlit
        caminho.seek(0)
        dados = io.BytesIO(caminho.read())
        nome = getattr(caminho, "name", "planilha")
    elif isinstance(caminho, (bytes, bytearray)):
        dados = io.BytesIO(caminho)
        nome = "planilha"
    else:
        dados = Path(caminho)
        nome = Path(caminho).name

    sufixo = Path(str(nome)).suffix.lower()
    try:
        if sufixo == ".csv":
            try:
                abas = {"planilha": pd.read_csv(dados, sep=None, engine="python")}
            except Exception:  # noqa: BLE001
                dados.seek(0)
                abas = {"planilha": pd.read_csv(dados, sep=";", decimal=",", engine="python")}
        else:
            abas = pd.read_excel(dados, sheet_name=None)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "cadastro": {}, "bombeamento": pd.DataFrame(),
                "recuperacao": pd.DataFrame(), "avisos": avisos,
                "erros": [f"Falha ao ler o arquivo: {type(exc).__name__}: {exc}"],
                "abas": []}

    nomes_abas = list(abas.keys())
    cadastro: dict[str, Any] = {}

    # ---- aba de cadastro -------------------------------------------------------------
    for nome_aba, df in abas.items():
        if _norm(nome_aba) in {_norm(ABA_CADASTRO), "cadastro", "dados", "metadados"}:
            colunas = [_norm(c) for c in df.columns]
            # Formato chave/valor (campo, chave_interna, valor)
            if "campo" in colunas or "chaveinterna" in colunas:
                idx_campo = (colunas.index("chaveinterna") if "chaveinterna" in colunas
                             else colunas.index("campo"))
                idx_valor = colunas.index("valor") if "valor" in colunas else (
                    len(df.columns) - 1)
                for _, row in df.iterrows():
                    chave = str(row.iloc[idx_campo]).strip()
                    valor = row.iloc[idx_valor]
                    if pd.isna(valor) or str(valor).strip() == "":
                        continue
                    alvo = _norm(chave)
                    for interno, aliases in ALIASES_CADASTRO.items():
                        if alvo in aliases:
                            cadastro[interno] = valor
                            break
            else:
                # Formato largo: primeira coluna = campo, segunda = valor.
                if len(df.columns) >= 2:
                    for _, row in df.iterrows():
                        chave = str(row.iloc[0]).strip()
                        valor = row.iloc[1]
                        if pd.isna(valor) or str(chave).lower() == "nan":
                            continue
                        alvo = _norm(chave)
                        for interno, aliases in ALIASES_CADASTRO.items():
                            if alvo in aliases:
                                cadastro[interno] = valor
                                break
            break

    # ---- abas de bombeamento / recuperacao -------------------------------------------
    def achar_aba(candidatos: set[str], palavras_chave: set[str]) -> pd.DataFrame | None:
        for nome_aba, df in abas.items():
            if _norm(nome_aba) in candidatos:
                return df
        for nome_aba, df in abas.items():
            colunas = {_norm(c) for c in df.columns}
            if colunas & palavras_chave:
                return df
        return None

    df_bom = achar_aba(
        {_norm(ABA_BOMBEAMENTO), "bombeamento", "rebaixamento", "ensaio"},
        {"ndm", "niveldinamico", "qm3h", "vazao"},
    )
    df_rec = achar_aba(
        {_norm(ABA_RECUPERACAO), "recuperacao", "recuperação", "residual"},
        {"tlinhamin", "nam", "nivelagua", "slinham"},
    )

    bombeamento = pd.DataFrame(columns=["t_min", "nd_m", "s_m", "q_m3h"])
    if df_bom is not None and len(df_bom):
        mapa = _mapear_colunas(df_bom)
        out = pd.DataFrame()
        for interno in ("t_min", "nd_m", "s_m", "q_m3h"):
            col = mapa.get(interno)
            out[interno] = (pd.to_numeric(df_bom[col], errors="coerce")
                            if col else pd.Series([pd.NA] * len(df_bom)))
        bombeamento = out.dropna(how="all").reset_index(drop=True)
        if "t_min" not in mapa:
            avisos.append("Coluna de tempo de bombeamento (t) nao identificada; "
                          "usada a ordem das linhas como sequencia.")
            bombeamento["t_min"] = pd.Series(range(1, len(bombeamento) + 1))

    recuperacao = pd.DataFrame(columns=["t_linha_min", "na_m", "s_linha_m"])
    if df_rec is not None and len(df_rec):
        mapa_r = _mapear_colunas(df_rec)
        out = pd.DataFrame()
        for interno in ("t_linha_min", "na_m", "s_linha_m"):
            col = mapa_r.get(interno)
            out[interno] = (pd.to_numeric(df_rec[col], errors="coerce")
                            if col else pd.Series([pd.NA] * len(df_rec)))
        recuperacao = out.dropna(how="all").reset_index(drop=True)

    # ---- consistencia -----------------------------------------------------------------
    if not len(bombeamento):
        erros.append("Nenhuma leitura de bombeamento valida encontrada.")
    else:
        if bombeamento["nd_m"].notna().sum() == 0:
            erros.append("Nao foi localizada a coluna de nivel dinamico (ND).")
        if bombeamento["q_m3h"].notna().sum() == 0:
            avisos.append("Nao foi localizada a coluna de vazao (Q); a vazao "
                          "estabilizada tera de ser informada manualmente.")

    return {
        "ok": not erros,
        "cadastro": cadastro,
        "bombeamento": bombeamento,
        "recuperacao": recuperacao,
        "avisos": avisos,
        "erros": erros,
        "abas": nomes_abas,
    }


def numeric(v: Any) -> float | None:
    """Converte valores de planilha (podem vir com virgula decimal) para float."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return None if pd.isna(v) else float(v)
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None
