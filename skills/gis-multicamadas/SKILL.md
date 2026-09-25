---
name: gis-multicamadas
description: >-
  Criação e manipulação avançada de mapas GIS em camadas distintas (Geologia, Hidrogeologia,
  Solos, Drenagem, Corpos d'água, Vias, Raio de Segurança e Poço). Suporta exportação interativa
  Folium com LayerControl (ligar/desligar camadas), alternância de mapa base (Satélite Esri, OSM,
  CartoDB, Topografia), régua métrica de medição de distâncias, inspeção de atributos e pranchas
  cartográficas. Integra QGIS MCP (renderização profissional via PyQGIS), geoai-py (imagens de
  satélite, SAM segmentation, leafmap), e delegação de tarefas pesadas ao Arena AI.
---

# GIS Multicamadas (Layer Master) — v2.0

Esta skill capacita os agentes de geoprocessamento e inteligência espacial a construir mapas
temáticos com **camadas distintas independentes**, integração com **QGIS via MCP**, análise de
imagens de satélite com **geoai-py**, e delegação de processamento pesado ao **Arena AI**.

---

## 1. Capacidades do Motor Folium (multicamadas_map.py)

1. **Estruturação por Camadas Distintas**:
   - **Camada Poço e Raio de Segurança**: Marcador temático + buffer circular métrico (500 m).
   - **Camada Propriedade / Terreno**: Polígono cadastral com hachura e transparência.
   - **Camada Geologia Local**: Unidades litológicas (CPRM) com tooltips informativos.
   - **Camada Hidrogeologia**: Sistemas aquíferos, tipos e vulnerabilidade.
   - **Camada Pedologia**: Classes de solo e susceptibilidade à infiltração.
   - **Camada Hidrografia / Drenagem**: Rios, arroios, distância ao corpo hídrico mais próximo.
   - **Camada Malha Viária / Acessos**: Eixos rodoviários e estradas locais.

2. **Mapas Base Alternáveis**:
   - Satélite de Alta Resolução (Esri World Imagery)
   - OpenStreetMap Standard
   - CartoDB Positron (fundo claro analítico)
   - OpenTopoMap (relevo e curvas de nível)

3. **Ferramental Interativo**:
   - `LayerControl`: Ativar/desativar cada camada independentemente.
   - `MeasureControl`: Régua interativa de distâncias e áreas.
   - `MousePosition`: Coordenadas sob o cursor.
   - `Fullscreen`: Modo tela cheia.

---

## 2. QGIS MCP — Renderização Profissional com PyQGIS

O QGIS MCP conecta Antigravity ao QGIS 3.40+ em execução via socket `localhost:9876`.

### Pré-requisito
```
1. Abrir QGIS 3.40+ em C:\Program Files\QGIS 3.40.7\bin\qgis-ltr-bin.exe
2. Plugins → QGIS MCP → Start Server  (porta 9876)
```

### Iniciar o MCP Server
```bash
python "C:\Users\Gabriel\.gemini\antigravity\scratch\qgis_mcp\src\qgis_mcp\qgis_mcp_server.py"
```

### Ferramentas MCP disponíveis (lazy tools em C:\Users\Gabriel\.gemini\antigravity\mcp\qgis-mcp\)

| Ferramenta | Descrição |
|---|---|
| `ping` | Verifica se QGIS está respondendo |
| `get_qgis_info` | Versão, plugins, projeto atual |
| `load_project` | Abre projeto .qgs/.qgz |
| `add_vector_layer` | Carrega .gpkg/.shp no projeto |
| `add_raster_layer` | Carrega GeoTIFF/Sentinel-2 |
| `get_layers` | Lista todas as camadas |
| `get_layer_features` | Atributos + geometria WKT |
| `render_map` | Exporta PNG/JPG a alta resolução |
| `execute_processing` | Roda algoritmos (buffer, clip, dissolve…) |
| `execute_code` | Executa PyQGIS arbitrário |
| `save_project` | Salva o projeto |

### Uso via QgisMCPClient (Python direto)
```python
import sys
sys.path.insert(0, r"C:\Users\Gabriel\.gemini\antigravity\scratch\qgis_mcp\src\qgis_mcp")
from qgis_socket_client import QgisMCPClient

with QgisMCPClient() as qgis:
    qgis.add_vector_layer(r"C:\...\outorgasys\data\vetoriais\geologia.gpkg", name="Geologia")
    qgis.add_vector_layer(r"C:\...\outorgasys\data\vetoriais\hidrogeologia.gpkg", name="Hidrogeologia")
    qgis.zoom_to_layer(qgis.get_layers()[0]["id"])
    # Renderiza prancha A4 a 300 DPI
    qgis.render_map(r"C:\tmp\prancha_qgis.png", width=2480, height=3508)
    # Tematização PyQGIS
    qgis.execute_code("""
from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSymbol
layer = QgsProject.instance().mapLayersByName("Geologia")[0]
# ... aplicar simbologia por atributo SIGLA
""")
```

### Casos de uso no Outorgasys
- **Pranchas profissionais**: `render_map` substitui matplotlib a 300 DPI com simbologia QGIS completa
- **Buffer de segurança**: `execute_processing("native:buffer", {"INPUT": id, "DISTANCE": 500})`
- **Choropleth litológico**: `execute_code` com `QgsCategorizedSymbolRenderer`
- **Verificação topológica**: `execute_processing("native:checkvalidity", {...})`

---

## 3. GeoAI-py — Imagens de Satélite e Segmentação

Instalado em: `pip install geoai-py` (versão 0.43.1, PyTorch incluso)

### Download de Imagens de Satélite
```python
import geoai

# Sentinel-2 via Microsoft Planetary Computer
geoai.download_sentinel2(
    bbox=[-51.08, -29.72, -51.00, -29.65],  # [lon_min, lat_min, lon_max, lat_max]
    output_dir="C:/tmp/sentinel2_campo_bom",
    time_range=("2024-01-01", "2024-12-31"),
    cloud_cover=20
)

# NAIP (alta resolução, EUA — para referência de metodologia)
geoai.download_naip(bbox=..., output_dir="...")
```

### Mapa Interativo com Leafmap (substitui Folium simples)
```python
import leafmap

m = leafmap.Map(center=[-29.69, -51.05], zoom=14)
m.add_basemap("SATELLITE")
m.add_vector("data/vetoriais/geologia.gpkg", layer_name="Geologia")
m.add_raster("C:/tmp/sentinel2.tif", layer_name="Sentinel-2", colormap="RdYlGn")
m.to_html("mapa_leafmap.html")
```

### Segmentação com Segment Anything (SAM)
```python
from geoai import SamGeo

sam = SamGeo(model_type="vit_h", checkpoint="sam_vit_h.pth")
sam.generate("C:/tmp/sentinel2.tif", output="C:/tmp/segmentos.gpkg")
# Extrai feições como corpos d'água, pastagens, edificações
```

### Extração de Edificações (Overture Maps)
```python
import geoai
buildings = geoai.get_overture_buildings(
    bbox=[-51.08, -29.72, -51.00, -29.65]
)
buildings.to_file("C:/tmp/edificacoes.gpkg")
```

### Uso no Agente GIS (agente2_gis.py)
- Baixar Sentinel-2 da área do poço → adicionar como basemap no mapa multicamadas
- Segmentar corpos d'água com SAM → validar distâncias do raio de segurança
- Usar `localtileserver` para servir GeoTIFF localmente como tile layer no Folium/leafmap

---

## 4. Arena AI como Executor — Antigravity como Orquestrador

**Resposta à dúvida do usuário**: ✅ SIM — você PODE usar o Arena AI com nossos agentes GabeBrain e suas skills.

### Fluxo: Antigravity (orquestrador) → Arena AI (executor)

```
Antigravity:
  1. Compõe um prompt estruturado usando skills GabeBrain
  2. Envia via arena_agent.py para Arena AI Agent Mode + repo outorgasys
  3. Arena AI executa o código (GIS, geoai, QGIS) com acesso ao repo GitHub
  4. Arena AI commita as alterações na branch ativa
  5. Antigravity puxa as mudanças via VCS agent
```

### Como delegar tarefa de mapas ao Arena AI
```bash
python "C:\Users\Gabriel\.gemini\config\skills\arena-ai-controller\scripts\arena_agent.py" send \
  --repo "gabrielhklaser/outorgasys" \
  --branch "main" \
  --prompt "Revise o arquivo outorgasys/gis/multicamadas_map.py e adicione suporte a leafmap como alternativa ao Folium. Adicione também um método para baixar e exibir imagens Sentinel-2 via geoai-py na área do poço. Commit as mudanças."
```

### Quando usar Arena AI vs Antigravity local

| Tarefa | Usar Arena AI | Usar Antigravity local |
|---|---|---|
| Renderizar mapa Folium simples | ❌ | ✅ Mais rápido |
| Download Sentinel-2 (lento, pesado) | ✅ Salva tokens | ❌ |
| SAM segmentation (GPU-heavy) | ✅ Salva tokens | ❌ |
| Refatoração de código GIS | ✅ Commit direto | ✅ (edições pontuais) |
| Debug de erros em tempo real | ❌ | ✅ Mais ágil |
| Análise de múltiplas camadas vetoriais | ✅ | ✅ |
| Execução de algoritmos QGIS Processing | ✅ (via QGIS MCP) | ✅ (via QGIS MCP) |

### Recover/Push quando Arena perde conexão
```bash
python "C:\Users\Gabriel\.gemini\config\skills\arena-ai-controller\scripts\arena_agent.py" \
  recover-push --repo "gabrielhklaser/outorgasys" --branch "main"
```

---

## 5. Estrutura de Arquivos

```
skills/gis-multicamadas/
├── SKILL.md                          # Este arquivo
└── scripts/
    ├── multicamadas_map.py           # Motor Folium multicamadas
    └── layer_manipulation.py         # Utilidades vetoriais (reparo, reprojeção, clip)

C:\Users\Gabriel\.gemini\antigravity\mcp\qgis-mcp\
├── instructions.md                   # Pré-requisitos e comandos MCP
├── ping.json                         # Ferramentas MCP (schemas)
├── get_qgis_info.json
├── load_project.json
├── add_vector_layer.json
├── add_raster_layer.json
├── get_layers.json
├── get_layer_features.json
├── render_map.json
├── execute_processing.json
├── execute_code.json
└── save_project.json
```

---

## 6. Exemplo de Uso Completo (Python)

```python
# Motor Folium (multicamadas_map.py)
from outorgasys.gis.multicamadas import gerar_mapa_multicamadas

html_path = gerar_mapa_multicamadas(
    lat=-29.6842, lon=-51.0531,
    raio_seguranca_m=500.0,
    camadas_vetoriais={
        "geologia": gdf_geo,
        "hidrogeologia": gdf_hidro,
        "solos": gdf_solos,
        "drenagem": gdf_dren,
    },
    dados_poco={"nome": "PT-01", "profundidade_total_m": 82.0},
    destino="data/relatorio/mapa_interativo_camadas.html"
)
```

---

## 7. Tratamento Vetorial Robusto (layer_manipulation.py)

- `reparar_geometrias(gdf)`: `make_valid` + `buffer(0)` para geometrias corrompidas
- `reprojetar_seguro(gdf, crs_alvo)`: reprojeção com fallback para EPSG:4326
- `recortar_por_raio(gdf, lat, lon, raio_m)`: clip espacial por buffer centrado no poço
