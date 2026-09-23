# -*- coding: utf-8 -*-
"""
Gerador de anexos de EXEMPLO para o processo de demonstracao.

Todos os arquivos produzidos aqui sao claramente marcados como
"DOCUMENTO DE EXEMPLO - NAO VALIDO PARA PROTOCOLO". Existem para permitir a
validacao ponta a ponta da plataforma (Agente 1 liberando o fluxo, laudo
sendo emitido) sem que ninguem precise anexar documentos reais.

Em uso real cada um destes anexos e substituido pelo documento original
emitido pelo cartorio de registro de imoveis, pelo laboratorio acreditado
e pelo responsavel tecnico.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

MARCA = "DOCUMENTO DE EXEMPLO — NAO VALIDO PARA PROTOCOLO"


# --------------------------------------------------------------------------------------
# Infraestrutura minima de PDF
# --------------------------------------------------------------------------------------

def _pdf_bytes(linhas: list[tuple[str, str]] , titulo: str,
               tabela: list[dict] | None = None,
               colunas: list[tuple[str, str]] | None = None) -> bytes:
    """Monta um PDF simples de uma pagina (titulo, paragrafos e tabela opcional)."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, title=titulo, author="OutorgaSys",
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm)

    estilos = getSampleStyleSheet()
    s_tit = ParagraphStyle("t", parent=estilos["Title"], fontSize=14, leading=17,
                           textColor=colors.HexColor("#1F4E79"), spaceAfter=2)
    s_marca = ParagraphStyle("m", parent=estilos["Normal"], fontSize=8, leading=10,
                             textColor=colors.HexColor("#B71C1C"),
                             alignment=1, spaceAfter=10)
    s_h = ParagraphStyle("h", parent=estilos["Heading3"], fontSize=10.5, leading=13,
                         textColor=colors.HexColor("#1F4E79"), spaceBefore=8,
                         spaceAfter=3)
    s_p = ParagraphStyle("p", parent=estilos["Normal"], fontSize=9.5, leading=13,
                         alignment=TA_JUSTIFY, spaceAfter=4)
    s_cel = ParagraphStyle("c", parent=estilos["Normal"], fontSize=8.5, leading=11)

    fluxo: list[Any] = [Paragraph(titulo, s_tit), Paragraph(MARCA, s_marca)]
    for rotulo, texto in linhas:
        if rotulo:
            fluxo.append(Paragraph(rotulo, s_h))
        fluxo.append(Paragraph(texto, s_p))

    if tabela and colunas:
        dados = [[Paragraph(f"<b>{rot}</b>", s_cel) for _, rot in colunas]]
        for linha in tabela:
            dados.append([Paragraph(str(linha.get(ch, "-")), s_cel)
                          for ch, _ in colunas])
        fluxo.append(Spacer(1, 5))
        t = Table(dados, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9E9E9E")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F2F6FA")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        fluxo.append(t)

    fluxo.append(Spacer(1, 10))
    fluxo.append(Paragraph(
        "<font size=7 color='#777777'>Arquivo sintetico gerado pelo OutorgaSys "
        "apenas para demonstracao do fluxo. Nao possui valor probatorio e nao "
        "substitui o documento original.</font>", s_p))

    doc.build(fluxo)
    return buf.getvalue()


def _salvar(diretorio: Path, nome: str, dados: bytes) -> Path:
    diretorio.mkdir(parents=True, exist_ok=True)
    p = diretorio / nome
    p.write_bytes(dados)
    return p


# --------------------------------------------------------------------------------------
# Documentos
# --------------------------------------------------------------------------------------

def matricula_imovel(diretorio: Path, imovel: dict, requerente: dict) -> Path:
    linhas = [
        ("", "CERTIDAO DE REGISTRO DE IMOVEIS (exemplo)"),
        ("Dados do imovel",
         f"Denominacao: <b>{imovel.get('denominacao', '-')}</b><br/>"
         f"Endereco: {imovel.get('endereco', '-')}, {imovel.get('bairro', '-')} — "
         f"{imovel.get('municipio', '-')}/{imovel.get('uf', 'RS')}, "
         f"CEP {imovel.get('cep', '-')}<br/>"
         f"Area: {imovel.get('area_ha', '-')} ha"),
        ("Proprietario",
         f"{requerente.get('nome', '-')} — CNPJ {requerente.get('cpf_cnpj', '-')}"),
        ("Observacao",
         "Documento sintetico gerado para validacao da plataforma. O processo "
         "real exige certidao de inteiro teor emitida pelo Registro de Imoveis "
         "competente, com prazo de emissao inferior a 30 dias."),
    ]
    return _salvar(diretorio, "matricula_imovel_exemplo.pdf",
                   _pdf_bytes(linhas, "Matricula do Imovel (exemplo)"))


PARAMETROS_888 = [
    {"parametro": "Coliformes totais", "resultado": "Ausencia em 100 mL",
     "vmp": "Ausencia em 100 mL", "conforme": "Sim"},
    {"parametro": "Escherichia coli", "resultado": "Ausencia em 100 mL",
     "vmp": "Ausencia em 100 mL", "conforme": "Sim"},
    {"parametro": "Turbidez", "resultado": "0,42 uT", "vmp": "<= 5,0 uT", "conforme": "Sim"},
    {"parametro": "Cor aparente", "resultado": "< 5,0 uH", "vmp": "<= 15,0 uH",
     "conforme": "Sim"},
    {"parametro": "pH a 25 graus C", "resultado": "7,1", "vmp": "6,0 a 9,5", "conforme": "Sim"},
    {"parametro": "Cloreto", "resultado": "18,4 mg/L", "vmp": "<= 250 mg/L", "conforme": "Sim"},
    {"parametro": "Sulfato", "resultado": "9,7 mg/L", "vmp": "<= 250 mg/L", "conforme": "Sim"},
    {"parametro": "Nitrato (como N)", "resultado": "2,1 mg/L", "vmp": "<= 10 mg/L",
     "conforme": "Sim"},
    {"parametro": "Nitrito (como N)", "resultado": "< 0,01 mg/L", "vmp": "<= 1,0 mg/L",
     "conforme": "Sim"},
    {"parametro": "Ferro total", "resultado": "0,09 mg/L", "vmp": "<= 0,30 mg/L",
     "conforme": "Sim"},
    {"parametro": "Manganes", "resultado": "0,03 mg/L", "vmp": "<= 0,10 mg/L",
     "conforme": "Sim"},
    {"parametro": "Dureza total", "resultado": "86 mg/L CaCO3", "vmp": "<= 500 mg/L",
     "conforme": "Sim"},
    {"parametro": "Solidos dissolvidos totais", "resultado": "148 mg/L",
     "vmp": "<= 1000 mg/L", "conforme": "Sim"},
    {"parametro": "Fluoreto", "resultado": "0,12 mg/L", "vmp": "<= 1,5 mg/L",
     "conforme": "Sim"},
]


def analise_laboratorial(diretorio: Path, poco: dict, requerente: dict) -> Path:
    linhas = [
        ("Identificacao da amostra",
         f"Ponto: <b>{poco.get('nome', '-')}</b> — "
         f"profundidade de {poco.get('profundidade_total_m', '-')} m<br/>"
         f"Interessado: {requerente.get('nome', '-')}<br/>"
         "Tipo de agua: subterranea bruta (poço tubular)"),
        ("Referencia normativa",
         "Parametros de potabilidade da Portaria GM/MS n. 888/2021, Anexo 1 "
         "(padrao de potabilidade) e Anexo 10 (controle de qualidade)."),
        ("Conclusao",
         "Amostra em conformidade com os parametros analisados. Ressalva-se que "
         "a Portaria GM/MS n. 888/2021 exige plano de amostragem periodico; este "
         "relatorio e pontual e de exemplo."),
    ]
    return _salvar(
        diretorio, "analise_laboratorial_exemplo.pdf",
        _pdf_bytes(linhas, "Relatorio de Analise Laboratorial (exemplo) "
                           "— Portaria GM/MS 888/2021",
                   PARAMETROS_888,
                   [("parametro", "Parametro"), ("resultado", "Resultado"),
                    ("vmp", "VMP (Portaria 888/2021)"), ("conforme", "Conforme")]))


def declaracao_separacao_redes(diretorio: Path, imovel: dict,
                               requerente: dict) -> Path:
    linhas = [
        ("Declaracao",
         f"{requerente.get('nome', '-')}, inscrita no CNPJ "
         f"{requerente.get('cpf_cnpj', '-')}, responsavel pelo imovel "
         f"{imovel.get('denominacao', '-')}, situado em "
         f"{imovel.get('municipio', '-')}/{imovel.get('uf', 'RS')}, DECLARA que:"),
        ("1.",
         "O imovel e atendido por rede publica de abastecimento de agua."),
        ("2.",
         "A agua do poco tubular cuja outorga se requer destina-se EXCLUSIVAMENTE "
         "a usos industriais, limpeza geral de patio e vias e irrigacao, sendo "
         "VEDADA qualquer utilizacao para consumo humano direto, higiene pessoal, "
         "sanitarios ou preparo de alimentos."),
        ("3.",
         "As redes hidraulicas sao fisicamente SEPARADAS, sem interconexao, "
         "cross-connection, by-pass ou qualquer outro ponto de comunicacao entre "
         "a rede publica e a rede alimentada pelo poco."),
        ("4.",
         "O responsavel tecnico pela operacao mantem as instalacoes identificadas "
         "e disponiveis para vistoria pelo orgao gestor."),
        ("Observacao",
         "Documento sintetico gerado para validacao da plataforma. Em uso real a "
         "declaracao deve ser emitida em papel timbrado, datada e assinada pelo "
         "representante legal, com firma reconhecida quando exigido."),
    ]
    return _salvar(diretorio, "declaracao_separacao_redes_exemplo.pdf",
                   _pdf_bytes(linhas, "Declaracao de Separacao Fisica de Redes "
                                      "Hidraulicas (exemplo)"))


FOTOS = [
    ("foto_01_boca_poco.jpg", "Boca do poco",
     "Tubo de revestimento com tampa de protecao e acabamento da laje",
     "#6D4C41", "#A1887F"),
    ("foto_02_laje_protecao.jpg", "Laje de protecao sanitaria",
     "Laje de concreto, dimensoes minimas e cota de rebordo acima do terreno",
     "#B0BEC5", "#78909C"),
    ("foto_03_cercamento.jpg", "Cercamento de protecao",
     "Fechamento perimetral do raio de protecao do poco",
     "#455A64", "#CFD8DC"),
    ("foto_04_cavalete_hidrometro.jpg", "Cavalete com hidrometro",
     "Hidrometro instalado em cavalete, com registro de corte a montante",
     "#37474F", "#90A4AE"),
]


def registro_fotografico(diretorio: Path, poco: dict) -> list[Path]:
    """Gera as quatro fotos de exemplo exigidas pelo SIOUT RS."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    gerados: list[Path] = []
    diretorio.mkdir(parents=True, exist_ok=True)

    for nome, titulo, legenda, cor_escura, cor_clara in FOTOS:
        fig, ax = plt.subplots(figsize=(6.0, 4.0), dpi=200)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6.7)
        ax.set_aspect("equal")
        ax.axis("off")
        fig.patch.set_facecolor("#ECEFF1")
        ax.set_facecolor("#ECEFF1")

        ax.add_patch(Rectangle((0, 0), 10, 1.1, color="#9E9E9E"))
        ax.add_patch(Rectangle((0, 1.1), 10, 5.6, color="#C5E1A5"))

        if "boca" in nome:
            ax.add_patch(Rectangle((3.4, 1.1), 3.2, 0.55, color="#BDBDBD"))
            ax.add_patch(Circle((5.0, 1.65), 0.85, color=cor_escura, zorder=3))
            ax.add_patch(Circle((5.0, 1.65), 0.62, color="#37474F", zorder=4))
            ax.add_patch(Circle((5.0, 1.65), 0.30, color="#263238", zorder=5))
        elif "laje" in nome:
            ax.add_patch(Rectangle((3.0, 1.1), 4.0, 0.75, color=cor_clara, zorder=3))
            ax.add_patch(Circle((5.0, 1.85), 0.55, color="#37474F", zorder=4))
            ax.annotate("", xy=(8.7, 1.95), xytext=(8.7, 1.1),
                        arrowprops={"arrowstyle": "<->", "lw": 1.2, "color": "black"})
            ax.text(8.85, 1.55, "rebordo", fontsize=7, rotation=90, va="center")
            ax.annotate("", xy=(3.0, 2.35), xytext=(7.0, 2.35),
                        arrowprops={"arrowstyle": "<->", "lw": 1.2, "color": "black"})
            ax.text(5.0, 2.45, "area da laje", fontsize=7, ha="center")
        elif "cercamento" in nome:
            for x in (2.2, 3.0, 3.8):
                ax.add_patch(Rectangle((x, 1.1), 0.12, 3.2, color=cor_escura))
            for x in (6.1, 6.9, 7.7):
                ax.add_patch(Rectangle((x, 1.1), 0.12, 3.2, color=cor_escura))
            for y in (2.0, 2.9):
                ax.add_patch(Rectangle((2.2, y), 5.6, 0.10, color=cor_clara))
            ax.add_patch(Circle((5.0, 1.6), 0.60, color="#37474F", zorder=5))
        else:
            ax.add_patch(Rectangle((4.7, 1.1), 0.22, 2.4, color=cor_escura))
            ax.add_patch(Rectangle((4.0, 3.5), 1.6, 0.30, color=cor_escura))
            ax.add_patch(Circle((5.0, 4.05), 0.55, color="white", zorder=3))
            ax.add_patch(Circle((5.0, 4.05), 0.42, color=cor_clara, zorder=4))
            ax.add_patch(Circle((5.0, 4.05), 0.16, color="#263238", zorder=5))
            ax.add_patch(Rectangle((4.55, 2.35), 0.55, 0.35, color="#FFB300", zorder=3))

        ax.text(5.0, 6.2, titulo, ha="center", fontsize=12, fontweight="bold",
                color="#1F4E79")
        ax.text(5.0, 5.75, legenda, ha="center", fontsize=8, color="#455A64")
        ax.text(5.0, 0.45, f"{poco.get('nome', '-')} — {MARCA}", ha="center",
                fontsize=7.5, color="#B71C1C")
        fig.tight_layout()
        caminho = diretorio / nome
        fig.savefig(caminho, dpi=200, facecolor="#ECEFF1")
        plt.close(fig)
        gerados.append(caminho)

    return gerados


def gerar_todos(diretorio: Path, imovel: dict, requerente: dict,
                poco: dict) -> dict:
    """Gera e devolve os caminhos de todos os anexos de exemplo."""
    return {
        "matricula_imovel": matricula_imovel(diretorio, imovel, requerente),
        "analise_laboratorial": analise_laboratorial(diretorio, poco, requerente),
        "declaracao_separacao_redes": declaracao_separacao_redes(
            diretorio, imovel, requerente),
        "registro_fotografico": registro_fotografico(diretorio, poco),
    }
