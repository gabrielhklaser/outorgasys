---
name: gis-multicamadas
description: >-
  Criação e manipulação avançada de mapas GIS em camadas distintas (Geologia, Hidrogeologia,
  Solos, Drenagem, Corpos d'água, Vias, Raio de Segurança e Poço). Suporta exportação interativa
  Folium com LayerControl (ligar/desligar camadas), alternância de mapa base (Satélite Esri, OSM,
  CartoDB, Topografia), régua métrica de medição de distâncias, inspeção de atributos e pranchas cartográficas.
---

# GIS Multicamadas (Layer Master)

Esta skill capacita os agentes de geoprocessamento e inteligência espacial a construir mapas temáticos com **camadas distintas independentes** (`FeatureGroup` e `LayerControl`), permitindo análise espacial profunda, auditoria de distâncias e inspeção interativa de atributos vetoriais.

## Capacidades

1. **Estruturação por Camadas Distintas**:
   - **Camada Poço e Raio de Segurança**: Marcador temático com dados construtivos + buffer circular métrico (ex: 500 m).
   - **Camada Propriedade / Terreno**: Polígono cadastral com hachura e transparência.
   - **Camada Geologia Local**: Unidades litológicas com cores padronizadas (CPRM) e tooltips informativos.
   - **Camada Hidrogeologia**: Sistemas aquíferos com tipos e vulnerabilidade.
   - **Camada Pedologia**: Classes de solo e susceptibilidade à infiltração.
   - **Camada Hidrografia / Drenagem**: Rios, arroios e massas d'água com cálculo de proximidade.
   - **Camada Malha Viária / Acessos**: Eixos rodoviários e estradas locais.

2. **Mapas Base Alternáveis**:
   - Satélite de Alta Resolução (Esri World Imagery)
   - OpenStreetMap Standard
   - CartoDB Positron (Fundo claro analítico)
   - OpenTopoMap (Relevo e curvas de nível)

3. **Ferramental Interativo Integrado**:
   - `LayerControl`: Ativar/desativar cada camada de dados de forma independente.
   - `MeasureControl`: Régua interativa para medição métrica de distâncias e áreas no mapa.
   - `MousePosition`: Exibição contínua de coordenadas sob o cursor.
   - `Fullscreen`: Modo tela cheia para inspeção técnica e apresentações.

4. **Tratamento Vetorial Robusto**:
   - Reparo topológico automático (`make_valid`, `buffer(0)`).
   - Reprojeção segura de datums e sistemas de coordenadas (SIRGAS 2000, UTM 22S, Web Mercator).
   - Recorte espacial por raio de interesse ou bounding box.

---

## Estrutura de Arquivos

- `scripts/multicamadas_map.py`: Motor de composição de mapas Folium multicamadas.
- `scripts/layer_manipulation.py`: Utilitários de carregamento, validação e reparo topológico de camadas.

---

## Exemplo de Uso em Python

```python
from outorgasys.skills.gis_multicamadas.scripts.multicamadas_map import criar_mapa_multicamadas, salvar_mapa_html

mapa = criar_mapa_multicamadas(
    lat=-29.6842,
    lon=-51.0531,
    zoom_inicial=15,
    raio_seguranca_m=500.0,
    camadas_vetoriais={
        "geologia": gdf_geo,
        "hidrogeologia": gdf_hidro,
        "solos": gdf_solos,
        "drenagem": gdf_dren,
    },
    dados_poco={"nome": "PT-01", "profundidade_total_m": 82.0}
)

salvar_mapa_html(mapa, "mapa_interativo_camadas.html")
```
