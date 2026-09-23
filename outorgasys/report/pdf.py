# -*- coding: utf-8 -*-
"""
Renderizacao do Laudo Tecnico em PDF (Agente 5).

Usa reportlab/platypus com:
  * capa e sumario de identificacao;
  * tabelas formatadas (parametros hidraulicos, quadro de vazoes, equipamentos);
  * imagens dos tres mapas e dos dois graficos embutidas em alta resolucao;
  * fluxograma em bloco desenhado vetorialmente;
  * apendice de proveniencia das bases geoespaciais;
  * espaco padronizado para assinatura do responsavel tecnico com numero da ART.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .. import config as C

AZUL = colors.HexColor("#1f4e79")
AZUL_CLARO = colors.HexColor("#dce9f5")
CINZA = colors.HexColor("#666666")
CINZA_CLARO = colors.HexColor("#f2f2f2")
BORDA = colors.HexColor("#bbbbbb")


# --------------------------------------------------------------------------------------
# Estilos
# --------------------------------------------------------------------------------------


def _estilos():
    ss = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle("titulo", parent=ss["Title"], fontSize=15, leading=18,
                                 textColor=AZUL, spaceAfter=2),
        "subtitulo": ParagraphStyle("subtitulo", parent=ss["Normal"], fontSize=10.5,
                                    leading=13, alignment=TA_CENTER, textColor=CINZA,
                                    spaceAfter=10),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=12, leading=15,
                             textColor=colors.white, backColor=AZUL,
                             borderPadding=(4, 5, 4, 5), spaceBefore=12, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=10.5, leading=13,
                             textColor=AZUL, spaceBefore=8, spaceAfter=4),
        "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontSize=9.5, leading=12,
                             textColor=colors.HexColor("#333333"), spaceBefore=6,
                             spaceAfter=3),
        "corpo": ParagraphStyle("corpo", parent=ss["BodyText"], fontSize=9, leading=12.5,
                                alignment=TA_JUSTIFY, spaceAfter=4),
        "item": ParagraphStyle("item", parent=ss["BodyText"], fontSize=9, leading=12.5,
                               leftIndent=10, bulletIndent=2, spaceAfter=3,
                               alignment=TA_JUSTIFY),
        "celula": ParagraphStyle("celula", parent=ss["BodyText"], fontSize=7.8,
                                 leading=10, spaceAfter=0),
        "celula_b": ParagraphStyle("celula_b", parent=ss["BodyText"], fontSize=7.8,
                                   leading=10, spaceAfter=0, fontName="Helvetica-Bold"),
        "nota": ParagraphStyle("nota", parent=ss["BodyText"], fontSize=7.5, leading=9.5,
                               textColor=CINZA, spaceAfter=4),
        "mono": ParagraphStyle("mono", parent=ss["BodyText"], fontName="Courier",
                               fontSize=7.6, leading=9.6, spaceAfter=2),
    }
    return estilos


# --------------------------------------------------------------------------------------
# Componentes
# --------------------------------------------------------------------------------------


#: Substituicoes para caracteres fora do WinAnsi (as fontes Type1 do reportlab
#: nao tem glifos para setas, letras gregas e simbolos unicode).
_MAPA_TEXTO = {
    "Δ": "Delta", "δ": "delta", "Σ": "Soma", "π": "pi",
    "→": "->", "←": "<-", "↑": "^", "↓": "v", "↔": "<->",
    "≥": ">=", "≤": "<=", "≠": "!=",
    "•": "-", "·": ".", "–": "-", "—": "-",
    "“": '"', "”": '"', "‘": "'", "’": "'",
    "…": "...", " ": " ", "≈": "~",
}


def _sanitize(texto: Any) -> str:
    """Converte texto para algo imprimivel nas fontes Type1 (WinAnsi/cp1252)."""
    s = str(texto)
    for k, v in _MAPA_TEXTO.items():
        if k in s:
            s = s.replace(k, v)
    # Escapa & < > soltos que nao sejam entidades conhecidas.
    try:
        s.encode("cp1252")
        limpo = s
    except UnicodeEncodeError:
        limpo = s.encode("cp1252", "replace").decode("cp1252")
    return limpo


def _p(texto: Any, estilo) -> Paragraph:
    return Paragraph(_sanitize(texto), estilo)


def _tabela_dados(pares: dict, estilos, largura_total: float = 17.0 * cm,
                  col1: float = 0.42) -> Table:
    dados = [[_p("<b>Item</b>", estilos["celula_b"]),
              _p("<b>Valor</b>", estilos["celula_b"])]]
    for k, v in pares.items():
        dados.append([_p(k, estilos["celula"]), _p(v, estilos["celula"])])
    t = Table(dados, colWidths=[largura_total * col1, largura_total * (1 - col1)],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _tabela_linhas(linhas: Sequence[dict], colunas: Sequence[tuple[str, str]],
                   estilos, largura_total: float = 17.0 * cm,
                   larguras: Sequence[float] | None = None) -> Table:
    dados = [[_p(f"<b>{rot}</b>", estilos["celula_b"]) for _, rot in colunas]]
    for ln in linhas:
        dados.append([_p(ln.get(ch, "-"), estilos["celula"]) for ch, _ in colunas])
    n = len(colunas)
    if larguras:
        soma = sum(larguras)
        widths = [largura_total * w / soma for w in larguras]
    else:
        widths = [largura_total / n] * n
    t = Table(dados, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _imagem(caminho: str | Path | None, largura: float = 17.0 * cm,
            altura_max: float = 10.5 * cm) -> Any:
    if not caminho:
        return _p("_Imagem nao disponivel._", getSampleStyleSheet()["BodyText"])
    p = Path(caminho)
    if not p.is_absolute():
        p = C.ROOT / p
    if not p.exists():
        return _p(f"_Imagem nao encontrada: {caminho}_",
                  getSampleStyleSheet()["BodyText"])
    try:
        from PIL import Image as PILImage  # noqa: PLC0415

        with PILImage.open(p) as im:
            w, h = im.size
        escala = min(largura / w, altura_max / h)
        return Image(str(p), width=w * escala, height=h * escala)
    except Exception:  # noqa: BLE001
        return Image(str(p), width=largura, height=altura_max)


def _fluxograma(estilos) -> Table:
    """Fluxograma esquematico em bloco do sistema de abastecimento."""
    e = estilos["celula"]
    blocos = [
        "POCO TUBULAR<br/>(captacao subterranea)",
        "MOTOBOMBA SUBMERSA<br/>+ QUADRO DE COMANDO",
        "CAVALETE<br/>+ HIDROMETRO",
        "RESERVATORIO SUPERIOR<br/>(caixa d'agua)",
        "REDE DE DISTRIBUICAO<br/>interna / externa",
        "PONTOS DE CONSUMO<br/>(finalidades declaradas)",
    ]
    dados = []
    for i, b in enumerate(blocos):
        dados.append([_p(f"<b>{b}</b>", e)])
        if i < len(blocos) - 1:
            dados.append([_p("<b>&#8595;</b>", e)])
    t = Table(dados, colWidths=[9.0 * cm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDA),
        ("BACKGROUND", (0, 0), (0, 0), AZUL_CLARO),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDA),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# --------------------------------------------------------------------------------------
# Cabecalho / rodape
# --------------------------------------------------------------------------------------


def _desenhar_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(CINZA)
    canvas.drawString(2 * cm, 1.15 * cm, C.TITULO_SISTEMA)
    canvas.drawRightString(19 * cm, 1.15 * cm, f"Pagina {doc.page}")
    canvas.setStrokeColor(BORDA)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.45 * cm, 19 * cm, 1.45 * cm)
    canvas.restoreState()


# --------------------------------------------------------------------------------------
# Geracao
# --------------------------------------------------------------------------------------


def gerar_pdf(estrutura: dict, destino: Path, titulo_extra: str = "") -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    est = _estilos()

    doc = SimpleDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.8 * cm,
        title="Laudo Tecnico de Caracterizacao Hidrogeologica",
        author=C.NOME_SISTEMA,
    )

    S: list[Any] = []
    cab = estrutura["cabecalho"]

    # ---------------- Capa ------------------------------------------------------------
    S.append(Paragraph(_sanitize(cab["titulo"]), est["titulo"]))
    S.append(Paragraph(_sanitize(cab["subtitulo"]), est["subtitulo"]))
    if titulo_extra:
        S.append(Paragraph(_sanitize(titulo_extra), est["subtitulo"]))
    S.append(Spacer(1, 4))

    S.append(_tabela_dados({
        "Processo": cab["processo"],
        "Data de emissao": cab["data_emissao"],
        "Sistema emissor": f"{C.NOME_SISTEMA} v{cab['versao_sistema']}",
    }, est))
    S.append(Spacer(1, 8))

    # ---------------- 1 -----------------------------------------------------------------
    S.append(Paragraph(_sanitize("1. IDENTIFICACAO DO REQUERENTE E DA PROPRIEDADE"), est["h1"]))
    S.append(Paragraph(_sanitize("1.1 Requerente"), est["h2"]))
    S.append(_tabela_dados(estrutura["identificacao"]["requerente"], est))
    S.append(Spacer(1, 5))
    S.append(Paragraph(_sanitize("1.2 Imovel e localizacao"), est["h2"]))
    S.append(_tabela_dados(estrutura["identificacao"]["imovel"], est))
    S.append(Spacer(1, 5))
    S.append(Paragraph(_sanitize("1.3 Documentacao de posse e terra"), est["h2"]))
    docs = estrutura["identificacao"]["documentacao_posse"]
    if docs:
        S.append(_tabela_linhas(docs, [("documento", "Documento"),
                                       ("situacao", "Situacao")], est))
    else:
        S.append(_p("Nenhum documento de posse anexado ao processo.", est["corpo"]))

    # ---------------- 2 -----------------------------------------------------------------
    S.append(Paragraph(_sanitize("2. CARACTERIZACAO CONSTRUTIVA E GEOLOGICA"), est["h1"]))
    S.append(Paragraph(_sanitize("2.1 Poco"), est["h2"]))
    S.append(_tabela_dados(estrutura["caracterizacao"]["poco"], est))
    S.append(Spacer(1, 4))
    S.append(_p(
        f"Referencias normativas: espaco anular minimo de {C.ESPACO_ANULAR_MIN_MM:g} mm "
        f"entre a parede do furo e a tubulacao de revestimento; selo sanitario com "
        f"profundidade minima recomendada de {C.SELO_SANITARIO_MIN_M:g} m.",
        est["nota"]))
    S.append(Paragraph(_sanitize("2.2 Laje de protecao sanitaria"), est["h2"]))
    S.append(_tabela_dados(estrutura["caracterizacao"]["laje_sanitaria"], est))
    S.append(Spacer(1, 4))
    S.append(_p(
        f"Minimos: espessura {C.LAJE_ESPESSURA_MIN_CM:g} cm, area "
        f"{C.LAJE_AREA_MIN_M2:g} m2, cota de rebordo {C.LAJE_REBORDO_MIN_CM:g} cm "
        "acima do terreno.", est["nota"]))
    S.append(Paragraph(_sanitize("2.3 Corpo hidrico mais proximo e raio de seguranca"), est["h2"]))
    S.append(_tabela_dados(estrutura["caracterizacao"]["corpo_hidrico"], est))
    rs = estrutura["caracterizacao"]["raio_seguranca"] or {}
    ocorr = rs.get("ocorrencias") or {}
    if ocorr:
        S.append(Spacer(1, 3))
        S.append(_tabela_linhas(
            [{"ocorrencia": k, "feicoes": v} for k, v in ocorr.items()],
            [("ocorrencia", "Ocorrencia no raio de seguranca"),
             ("feicoes", "Feicoes")], est))
    else:
        S.append(Spacer(1, 3))
        S.append(_p(f"Nenhuma ocorrencia mapeada dentro do raio de seguranca de "
                    f"{C.RAIO_SEGURANCA_M:g} m nas bases consultadas.", est["nota"]))

    # ---------------- 3 -----------------------------------------------------------------
    S.append(PageBreak())
    S.append(Paragraph(_sanitize("3. PARAMETROS HIDRAULICOS E RESULTADOS DO ENSAIO"), est["h1"]))
    if not estrutura["hidraulica"]["exige_ensaio"]:
        S.append(_p("Poco de pequeno diametro (inferior a 4 polegadas): o SIOUT RS "
                    "dispensa o ensaio de bombeamento continuo de 24 horas.", est["corpo"]))
        S.append(Spacer(1, 4))
    tabela = estrutura["hidraulica"]["tabela"]
    if tabela:
        S.append(_tabela_linhas(
            tabela, [("parametro", "Parametro"), ("valor", "Valor"),
                     ("criterio", "Criterio / Formula")],
            est, larguras=[3.0, 1.6, 3.0]))
    else:
        S.append(_p("Nenhum resultado hidraulico disponivel para este processo.",
                    est["corpo"]))

    graf = (estrutura["anexos"]["graficos"] or {})
    if graf.get("painel"):
        S.append(Spacer(1, 6))
        S.append(Paragraph(_sanitize("3.1 Graficos do ensaio de bombeamento"), est["h2"]))
        S.append(_imagem(graf["painel"], largura=17.0 * cm, altura_max=9.2 * cm))
        S.append(_p("Metodos de Theis / Cooper-Jacob. Grafico 1: rebaixamento x tempo "
                    "(escala semilogaritmica, eixo esquerdo em profundidade absoluta "
                    "invertida). Grafico 2: rebaixamento residual s' x t/t'.",
                    est["nota"]))
    elif graf.get("rebaixamento") or graf.get("recuperacao"):
        S.append(Spacer(1, 6))
        for chave, rot in (("rebaixamento", "Rebaixamento x tempo"),
                           ("recuperacao", "Recuperacao residual")):
            if graf.get(chave):
                S.append(Paragraph(_sanitize(f"3.1 {rot}"), est["h2"]))
                S.append(_imagem(graf[chave], largura=13.0 * cm, altura_max=8.5 * cm))

    # ---------------- 4 -----------------------------------------------------------------
    S.append(Paragraph(_sanitize("4. DESCRICAO DOS EQUIPAMENTOS INSTALADOS"), est["h1"]))
    S.append(Paragraph(_sanitize("4.1 Motobomba submersa"), est["h2"]))
    S.append(_tabela_dados(estrutura["equipamentos"]["motobomba"], est))
    S.append(Paragraph(_sanitize("4.2 Hidrometro"), est["h2"]))
    S.append(_tabela_dados(estrutura["equipamentos"]["hidrometro"], est))
    S.append(Paragraph(_sanitize("4.3 Reservacao"), est["h2"]))
    res = dict(estrutura["equipamentos"]["reservacao"])
    detalhe = res.pop("Detalhamento", [])
    S.append(_tabela_dados(res, est))
    if detalhe:
        S.append(Spacer(1, 4))
        S.append(_tabela_linhas(detalhe, [("reservatorio", "Reservatorio"),
                                          ("capacidade_l", "Capacidade"),
                                          ("local", "Local")], est))
    S.append(Paragraph(_sanitize("4.4 Auditoria tecnica dos equipamentos"), est["h2"]))
    pend = (estrutura["equipamentos"]["auditoria"] or {}).get("pendencias") or []
    if pend:
        S.append(_tabela_linhas(
            [{"codigo": p.get("codigo", "-"), "titulo": p.get("titulo", ""),
              "mensagem": p.get("mensagem", "")} for p in pend],
            [("codigo", "Cod."), ("titulo", "Titulo"), ("mensagem", "Descricao")],
            est, larguras=[0.8, 2.4, 4.4]))
    else:
        S.append(_p("Nenhuma inconformidade identificada nos equipamentos declarados.",
                    est["corpo"]))

    # ---------------- 5 -----------------------------------------------------------------
    S.append(PageBreak())
    S.append(Paragraph(_sanitize("5. FLUXOGRAMA E MEMORIAL DO SISTEMA DE ABASTECIMENTO"), est["h1"]))
    S.append(Paragraph(_sanitize("5.1 Memorial descritivo do percurso da agua"), est["h2"]))
    for e in estrutura["memorial"]["etapas"]:
        S.append(Paragraph(_sanitize(f"<b>{e['etapa']}</b> - {e['descricao']}"), est["item"]))
    S.append(Spacer(1, 6))
    S.append(Paragraph(_sanitize("5.2 Fluxograma esquematico em bloco"), est["h2"]))
    S.append(_fluxograma(est))

    # ---------------- 6 -----------------------------------------------------------------
    S.append(Paragraph(_sanitize("6. QUADRO DE VAZAO HOMOLOGADO DO SIOUT"), est["h1"]))
    S.append(Paragraph(_sanitize("6.1 Regime operacional"), est["h2"]))
    S.append(_tabela_dados(estrutura["regime"], est))
    q = estrutura.get("quadro_vazao") or {}
    if q.get("linhas"):
        S.append(Paragraph(_sanitize("6.2 Quadro de Vazao da Intervencao"), est["h2"]))
        S.append(_tabela_linhas(
            q["linhas"],
            [("mes", "Mes"), ("dias_operacao", "Dias/Mes"), ("horas_dia", "Horas/Dia"),
             ("vazao_m3h", "Vazao (m3/h)"), ("volume_m3_mes", "Volume (m3/mes)")],
            est, larguras=[1.8, 1.3, 1.3, 1.5, 1.9]))
        S.append(Spacer(1, 4))
        S.append(_tabela_dados({
            "Volume anual total": f"{q.get('volume_anual_m3', 0):,.2f} m3/ano"
            .replace(",", "X").replace(".", ",").replace("X", "."),
            "Vazao diaria maxima": f"{q.get('vazao_diaria_max_m3_dia', 0):,.3f} m3/dia"
            .replace(",", "X").replace(".", ",").replace("X", "."),
            "Vazao media diaria": f"{q.get('vazao_media_diaria_m3_dia', 0):,.3f} m3/dia"
            .replace(",", "X").replace(".", ",").replace("X", "."),
        }, est))
    else:
        S.append(_p("Quadro de vazoes nao disponivel.", est["corpo"]))

    # ---------------- 7 -----------------------------------------------------------------
    S.append(Paragraph(_sanitize("7. PARECER CONCLUSIVO E RECOMENDACOES"), est["h1"]))
    S.append(Paragraph(_sanitize("7.1 Conclusoes"), est["h2"]))
    for c in estrutura["parecer"]["conclusoes"]:
        S.append(Paragraph(_sanitize(c), est["item"], bulletText="-"))
    S.append(Paragraph(_sanitize("7.2 Recomendacoes"), est["h2"]))
    for r in estrutura["parecer"]["recomendacoes"]:
        S.append(Paragraph(_sanitize(r), est["item"], bulletText="-"))
    S.append(Paragraph(_sanitize("7.3 Declaracoes"), est["h2"]))
    S.append(_p(f"Imovel atendido por rede publica de abastecimento de agua: "
                f"<b>{estrutura['parecer']['rede_publica']}</b>", est["corpo"]))
    if estrutura["parecer"]["rede_publica"] == "Sim":
        S.append(_p("<b>Atestado de separacao de redes:</b> declara-se a separacao "
                    "fisica integral das redes hidraulicas, sem qualquer interconexao, "
                    "cross-connection ou by-pass entre a rede publica e a rede "
                    "alimentada pelo poco, ficando a agua subterranea restrita as "
                    "finalidades industriais, de limpeza geral de patio, irrigacao ou "
                    "recirculacao.", est["corpo"]))
    S.append(_p(f"<b>Repouso diario minimo do aquifero:</b> "
                f"{estrutura['regime'].get('Repouso diario', '-')} "
                f"(minimo exigido pelo SIOUT RS: {C.REPOUSO_MINIMO_H:g} h/dia).",
                est["corpo"]))

    # ---------------- Anexos: mapas -------------------------------------------------------
    mapas = estrutura["anexos"]["mapas"] or []
    if mapas:
        S.append(PageBreak())
        S.append(Paragraph(_sanitize("ANEXO I - PRANCHAS CARTOGRAFICAS"), est["h1"]))
        for m in mapas:
            S.append(_imagem(m, largura=17.0 * cm, altura_max=11.0 * cm))
            S.append(Spacer(1, 8))

    # ---------------- Anexo: proveniencia --------------------------------------------------
    prov = estrutura["anexos"]["proveniencia"] or {}
    if prov:
        S.append(PageBreak())
        S.append(Paragraph(_sanitize("APENDICE A - PROVENIENCIA DAS BASES GEOESPACIAIS"), est["h1"]))
        S.append(_p("Declara-se a origem de cada base vetorial consultada na elaboracao "
                    "deste laudo. Camadas com status 'ausente' nao estavam disponiveis "
                    "no ambiente de processamento e nao foram substituidas por dados "
                    "sinteticos.", est["nota"]))
        S.append(Spacer(1, 4))
        S.append(_tabela_linhas(
            [{"camada": k, "status": (v or {}).get("status", "-"),
              "origem": (v or {}).get("origem", "-"),
              "feicoes": (v or {}).get("feicoes", "-")}
             for k, v in sorted(prov.items())],
            [("camada", "Camada"), ("status", "Status"),
             ("origem", "Origem declarada"), ("feicoes", "Feicoes")],
            est, larguras=[1.6, 1.0, 3.6, 0.8]))

    # ---------------- Assinatura --------------------------------------------------------------
    S.append(Spacer(1, 14))
    a = estrutura["assinatura"]
    bloco = [
        Paragraph(_sanitize("RESPONSAVEL TECNICO"), est["h2"]),
        _tabela_dados({
            "Nome": a["responsavel_tecnico"],
            "Titulo / formacao": a["titulo"],
            "Registro profissional": a["registro"],
            "ART": a["art"],
        }, est),
        Spacer(1, 10),
        Paragraph(_sanitize(a["local_data"]), est["corpo"]),
        Spacer(1, 14),
        Paragraph("_" * 62, est["corpo"]),
        Paragraph(_sanitize("Assinatura do Responsavel Tecnico"), est["nota"]),
        Spacer(1, 6),
        Paragraph(_sanitize(a["nota_normativa"]), est["nota"]),
    ]
    S.append(KeepTogether(bloco))

    doc.build(S, onFirstPage=_desenhar_pagina, onLaterPages=_desenhar_pagina)
    return destino
