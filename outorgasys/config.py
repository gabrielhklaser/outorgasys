# -*- coding: utf-8 -*-
"""Configuracao global, constantes normativas e caminhos do outorgasys."""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------------------
# Caminhos
# --------------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VETORIAIS = DATA / "vetoriais"
CACHE_OSM = DATA / "cache" / "osm"
PROCESSOS = DATA / "processos"
SAIDA = DATA / "saida"
EXEMPLOS = DATA / "exemplos"

# Identificador do processo de exemplo (gerado por scripts/semente_campo_bom.py)
PROCESSO_EXEMPLO = "EX-CAMPOBOM-001"
ASSETS = ROOT / "assets"

for _p in (VETORIAIS, CACHE_OSM, PROCESSOS, SAIDA, EXEMPLOS, ASSETS):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------------
# Geodesia
# --------------------------------------------------------------------------------------

CRS_GEOGRAFICO = "EPSG:4674"   # SIRGAS 2000 - coordenadas geograficas
CRS_UTM_22S = "EPSG:31982"     # SIRGAS 2000 / UTM fuso 22S
CRS_UTM_21S = "EPSG:31981"     # SIRGAS 2000 / UTM fuso 21S (oeste do RS)
CRS_UTM_23S = "EPSG:31983"     # SIRGAS 2000 / UTM fuso 23S (litoral norte)

# Caixa envolvente do Rio Grande do Sul (WGS84 / SIRGAS 2000)
RS_BBOX = (-57.6548, -33.7512, -49.6935, -27.0752)

# --------------------------------------------------------------------------------------
# Regras do SIOUT RS e referencias normativas
# --------------------------------------------------------------------------------------

#: Diametro util que separa poco de pequeno diametro de poco tubular profundo.
DIAMETRO_CORTE_POL = 4.0

#: Repouso minimo obrigatorio do aquifero (SIOUT RS).
REPOUSO_MINIMO_H = 4.0
#: Consequencia: tempo diario maximo de bombeamento.
BOMBEAMENTO_MAX_H_DIA = 24.0 - REPOUSO_MINIMO_H  # 20 h/dia

#: O enunciado fixa trava em 18:00 h/dia (mais conservador que o minimo de 4 h).
BOMBEAMENTO_TRAVA_H_DIA = 18.0

#: Raio de seguranca sanitaria exigido pelo SIOUT RS.
RAIO_SEGURANCA_M = 500.0

#: Selo sanitario minimo recomendado.
SELO_SANITARIO_MIN_M = 20.0
#: Espaco anular minimo entre parede do furo e tubulacao de revestimento.
ESPACO_ANULAR_MIN_MM = 75.0

#: Laje de protecao sanitaria.
LAJE_ESPESSURA_MIN_CM = 10.0
LAJE_AREA_MIN_M2 = 1.0
LAJE_REBORDO_MIN_CM = 30.0

#: Submergencia minima recomendada da motobomba abaixo do nivel dinamico.
SUBMERGENCIA_MIN_M = 6.0
SUBMERGENCIA_MAX_M = 10.0

#: Fator de seguranca de longo prazo aplicado a transmissividade para obter q(t).
FATOR_LONGO_PRAZO = 0.8

#: Constante do metodo de Cooper-Jacob para transmissividade (log natural -> log10).
COEF_COOPER_JACOB = 0.183

#: Profundidade padrao do eixo de profundidade nos graficos.
PROFUNDIDADE_EIXO_PADRAO_M = 150.0

#: Numero de dias por mes usado no Quadro de Vazao da Intervencao (SIOUT RS).
DIAS_POR_MES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
NOMES_MESES = [
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# --------------------------------------------------------------------------------------
# Catalogo de finalidades de uso
# --------------------------------------------------------------------------------------

#: Finalidades incompativeis com imovel atendido por rede publica de abastecimento.
FINALIDADES_USO_HUMANO = {
    "consumo_humano_direto",
    "higiene_sanitarios",
    "cozinha_preparo_alimentos",
}

FINALIDADES = {
    # chave                          rotulo                                      uso humano?
    "consumo_humano_direto": ("Consumo humano direto (beber)", True),
    "higiene_sanitarios": ("Higiene pessoal / sanitarios", True),
    "cozinha_preparo_alimentos": ("Cozinha / preparo de alimentos", True),
    "industrial": ("Uso industrial", False),
    "limpeza_geral_patio": ("Limpeza geral de patio e vias", False),
    "irrigacao": ("Irrigacao", False),
    "recirculacao": ("Recirculacao / resfriamento", False),
    "dessedentacao_animais": ("Dessedentacao de animais", False),
    "piscicultura": ("Piscicultura / aquicultura", False),
    "construcao_civil": ("Construcao civil", False),
}

# --------------------------------------------------------------------------------------
# Documentos obrigatorios (Agente 1)
# --------------------------------------------------------------------------------------

DOCS_POSSE = {
    "matricula_imovel": "Certidao de registro de imoveis / matricula atualizada",
    "contrato_locacao": "Contrato de arrendamento / locacao / comodato",
    "termo_concessao": "Termo de concessao de uso",
    "recibo_car": "Recibo do CAR (Cadastro Ambiental Rural)",
}

EXTENSOES_POSSE = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
EXTENSOES_LAUDO = {".pdf"}
EXTENSOES_ENSAIO = {".xlsx", ".xls", ".csv"}
EXTENSOES_FOTO = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
EXTENSOES_GEO = {".kml", ".kmz", ".gpkg", ".geojson", ".json", ".zip"}

TAMANHO_MAX_UPLOAD_MB = int(os.environ.get("OUTORGASYS_MAX_UPLOAD_MB", "200"))

# --------------------------------------------------------------------------------------
# Parametros de potabilidade - Portaria GM/MS n. 888/2021
# --------------------------------------------------------------------------------------

#: Valores maximos permitidos (VMP) dos parametros cobrados na triagem documental.
#: Fonte: Portaria GM/MS n. 888/2021, Anexos 1-10 (padroes de potabilidade).
PARAMETROS_POTABILIDADE = {
    "coliformes_totais": ("Coliformes totais", "Presenca/Ausencia", "Ausencia em 100 mL", None),
    "escherichia_coli": ("Escherichia coli", "Presenca/Ausencia", "Ausencia em 100 mL", None),
    "turbidez": ("Turbidez", "uT", "<=", 5.0),
    "cor_aparente": ("Cor aparente", "uH (mg Pt-Co/L)", "<=", 15.0),
    "cloro_residual_livre": ("Cloro residual livre", "mg/L", ">=", 0.2),
    "ph": ("pH", "-", "6,0 a 9,5", None),
    "fluor": ("Fluoreto", "mg/L", "<=", 1.5),
    "nitrato": ("Nitrato (como N)", "mg/L", "<=", 10.0),
    "nitrito": ("Nitrito (como N)", "mg/L", "<=", 1.0),
    "sulfato": ("Sulfato", "mg/L", "<=", 250.0),
    "cloreto": ("Cloreto", "mg/L", "<=", 250.0),
    "ferro": ("Ferro", "mg/L", "<=", 0.3),
    "manganes": ("Manganes", "mg/L", "<=", 0.1),
    "sodio": ("Sodio", "mg/L", "<=", 200.0),
    "solidos_dissolvidos_totais": ("Solidos dissolvidos totais", "mg/L", "<=", 1000.0),
    "dureza_total": ("Dureza total", "mg/L", "<=", 500.0),
    "arsenio": ("Arsenio", "mg/L", "<=", 0.01),
    "cadmio": ("Cadmio", "mg/L", "<=", 0.005),
    "chumbo": ("Chumbo", "mg/L", "<=", 0.01),
    "mercurio": ("Mercurio", "mg/L", "<=", 0.001),
    "cromo_total": ("Cromo total", "mg/L", "<=", 0.05),
    "selenio": ("Selenio", "mg/L", "<=", 0.04),
    "cianeto": ("Cianeto", "mg/L", "<=", 0.07),
}

# --------------------------------------------------------------------------------------
# Mapas / cartografia
# --------------------------------------------------------------------------------------

DPI_MAPAS = 300
LARGURA_MAPA_POL = 11.69   # A4 paisagem
ALTURA_MAPA_POL = 8.27

#: Provedores de basemap testados em ordem; o primeiro que responder e usado.
BASEMAPS = [
    ("ESRI World Imagery", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"),
    ("OpenStreetMap", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
]

# --------------------------------------------------------------------------------------
# Versao
# --------------------------------------------------------------------------------------

VERSAO = "1.0.0"
NOME_SISTEMA = "outorgasys"
TITULO_SISTEMA = "OutorgaSys - Automacao de Outorgas de Agua Subterranea (SIOUT RS)"

AGENTES = {
    1: ("Triagem, Cadastro e Validacao Documental", "SIOUT RS / ABNT NBR 12212:2017 e 12244:2006"),
    2: ("Inteligencia Espacial e Automacao GIS", "SIRGAS 2000, UTM 22S, geoprocessamento"),
    3: ("Processamento Hidrogeologico e Graficos", "Theis / Cooper-Jacob / Jacob-Lohman"),
    4: ("Balanco Hidrico, Restricoes e Equipamentos", "Quadro de Vazao da Intervencao"),
    5: ("Emissao de Relatorio Tecnico Final e Minuta SIOUT", "Laudo + Memorial Descritivo"),
    6: ("Triagem de Defeitos e Engenharia de Correcoes", "observabilidade e auto-correcao"),
}
