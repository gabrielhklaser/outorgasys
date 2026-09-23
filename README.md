# OutorgaSys

Plataforma de automação de processos de **outorga de água subterrânea no Rio
Grande do Sul** (SIOUT RS), com orquestrador e seis agentes encadeados: da
triagem documental até o laudo técnico assinável e a minuta de transcrição no
SIOUT.

```
OutorgaSys · v1.0.0 · SIOUT RS
ABNT NBR 12212:2017 · ABNT NBR 12244:2006 · Portaria GM/MS n. 888/2021
CEGM/CREA-RS n. 08/2022 · CNRH Res. 32/2003
```

---

## Início rápido

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# (opcional) gerar o processo de exemplo já completo, do Agente 1 ao 6
.venv/bin/python scripts/semente_campo_bom.py

# subir a aplicação
.venv/bin/python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Na tela inicial, use **"▶️ Abrir exemplo"** para carregar o processo
`EX-CAMPOBOM-001` (poço tubular de 6″ em Campo Bom/RS) com os seis agentes já
executados.

---

## Arquitetura

| Agente | Nome | O que faz |
|:---:|---|---|
| **1** | Triagem e Validação Documental | Enquadramento binário do poço, modelo `.xlsx` do ensaio, *uploads* obrigatórios, cadastro, equipamentos, padrão de explotação e finalidades |
| **2** | Inteligência Espacial (GIS) | Coordenadas SIRGAS 2000 → UTM 22S, cruzamento vetorial, raio de segurança de 500 m e as três pranchas cartográficas a 300 DPI |
| **3** | Processamento Hidrogeológico | Theis / Cooper-Jacob / Jacob-Lohman sobre a planilha de ensaio, com dois gráficos de alta resolução |
| **4** | Balanço Hídrico e Equipamentos | Auditoria de motobomba, hidrômetro e reservação; Quadro de Vazão da Intervenção (12 meses) |
| **5** | Relatório Técnico e Minuta SIOUT | Laudo + Memorial Descritivo (Markdown e PDF) e minuta de transcrição |
| **6** | Triagem de Defeitos | Coleta, classifica e propõe correções para todos os defeitos do fluxo |

O **orquestrador** (`app.py`) mostra o estado de cada agente, o inventário das
bases vetoriais e o acesso rápido às etapas.

```
outorgasys/
├─ agents/          agente1..agente6
├─ gis/             geo.py, layers.py, cartografia.py, overpass.py, skill_bridge.py
│  └─ data/         tabela de bacias curada (bacias_rs.json)
├─ hydro/           theis.py (memória de cálculo), planilha.py, graficos.py,
│                   sintetico.py (gerador de ensaio para validação)
├─ report/          laudo.py, pdf.py, documentos_exemplo.py
├─ rules.py         regras de negócio do SIOUT RS
├─ state.py         Processo (persistência em data/processos/<id>.json)
└─ config.py        constantes normativas e caminhos
```

---

## Decisões técnicas do domínio

### Agente 1 — enquadramento e travas

- **Opção A** (⌀ útil < 4″): dispensa o ensaio de 24 h.
- **Opção B** (⌀ útil ≥ 4″): exige ensaio de bombeamento contínuo de 24 h
  **acompanhado do ensaio de recuperação**.
- **Repouso do aquífero**: o SIOUT RS exige no mínimo **4 h/dia**; a plataforma
  bloqueia acima de **18 h/dia** de bombeamento.
- **Rede pública**: se o imóvel é atendido por rede pública, ficam
  **proibidas** as finalidades de consumo humano direto, higiene/sanitários e
  cozinha. Restam industrial, limpeza geral, irrigação e recirculação — com
  declaração de **separação física das redes** e comprovante anexo.

### Agente 2 — geodesia e cartografia

- Entrada em **graus decimais**; conversão **SIRGAS 2000 (EPSG:4674)** →
  **UTM 22S (EPSG:31982)**.
- Interseção com bases vetoriais locais: geologia/litologia, hidrogeologia,
  solos, municípios, drenagem, massas d'água e malha viária (OSM/Overpass).
- **Raio de segurança de 500 m** gerado pela skill `shapely-compute` e cruzado
  com poços vizinhos e fontes de poluição.
- Três pranchas **JPG a 300 DPI**, todas com título padronizado, coordenadas do
  poço, norte geográfico, escala gráfica métrica e legenda:

  | Arquivo | Conteúdo |
  |---|---|
  | `mapa_situacao.jpg` | base cartográfica/OSM, limite da propriedade, buffer de 500 m, vias |
  | `mapa_geologico.jpg` | polígonos geológicos, contatos e fraturas |
  | `mapa_hidrologico.jpg` | drenagem, corpos d'água no raio, sistema aquífero |

- Emite um **JSON estruturado** consumido pelos Agentes 4 e 5.

### Agente 3 — memória de cálculo

| Grandeza | Expressão |
|---|---|
| Rebaixamento | `s = ND − NE` |
| Rebaixamento residual | `s' = NA − NE`, com `t = t_total + t'` |
| Transmissividade | `T = 0,183 · Q_estável / Δs'` (m²/h e ÷ 3600 → m²/s) |
| Capacidade específica | `q = Q_estável / s_máx` |
| Capacidade de longo prazo | `q(t) = 0,8 · T` |
| Vazão ótima | `Q_ot = q(t) · s_máx` |

A **vazão de explotação adotada é o menor valor entre `Q_ot` e `Q_estável`**, de
modo que o poço nunca opere acima da vazão efetivamente testada.

**Gráfico 1** — rebaixamento × tempo (semilog), eixo vertical esquerdo com a
profundidade absoluta de 0 a 150 m invertido (NE e ND marcados), eixo direito
com `s` e linha de tendência.
**Gráfico 2** — recuperação residual `s' × log₁₀(t/t')` com a equação da reta e
o valor de `Δs'` por ciclo logarítmico.

### Agente 4 — balanço e equipamentos

- Quadro de Vazão da Intervenção: `Dias/Mês`, `Dias de operação`,
  `Horas/Dia`, `Vazão (m³/h)`, `Volume (m³/mês)` — 12 meses + total anual.
- Dias de operação por mês = `dias do mês × (dias por semana / 7)`.
- Motobomba: vazão na faixa de **0,8 a 1,1 ×** a vazão ótima e submersão do
  rotor entre **6 e 10 m** abaixo do nível dinâmico (evitar cavitação).
- Hidrômetro: vazão nominal e DN compatíveis com a vazão de explotação.
- Reservação: capacidade total deve superar o volume por ciclo (evitar
  *short-cycling*).

### Agente 5 — laudo

Laudo + Memorial com as sete seções obrigatórias, parecer conclusivo (repouso
≥ 4 h, atestado de separação de redes) e bloco de assinatura com ART, para
Geólogo ou Engenheiro de Minas (norma CEGM/CREA-RS n. 08/2022). Saídas:
`laudo_tecnico.md`, `laudo_tecnico.pdf` e `minuta_siout.md`.

### Agente 6 — triagem de defeitos

Recolhe erros, avisos, pendências e degradações dos Agentes 1–5, cruza com o
estado do ambiente (skills, pacotes, bases vetoriais) e devolve um plano
priorizado por severidade (`critico`, `alto`, `medio`, `baixo`, `info`) com
passos concretos e corpo de issue pronto.

**Nada é executado fora do processo**: nenhuma issue é aberta e nenhum commit é
enviado sem decisão do operador.

---

## Habilidades integradas (3)

Vendorizadas em `skills/` (cópia dos repositórios públicos, sem CLI nem contas):

| Skill | Uso no OutorgaSys |
|---|---|
| `shapely-compute` | buffer do raio de segurança, distâncias euclidianas métricas, predicados `contains`/`within`, validade de geometrias |
| `geopandas` | preflight de qualidade vetorial (`vector_inventory`, `geometry_validity_report`, `crs_reprojection_plan`, `spatial_join_audit`) |
| `geomaster` | referência normativa de geodesia, projeções e métodos, citada nas escolhas SIRGAS 2000 / UTM 22S |

---

## Bases vetoriais e origem declarada

A política adotada é **híbrida com fallback local**: tenta-se a fonte oficial
aberta e, em caso de falha, usa-se base local/sintética/derivada **declarando
sempre a origem no laudo**.

| Situação | Base | Origem declarada |
|---|---|---|
| Geologia, hidrogeologia, solos | KMZ do projeto convertidos para GeoPackage | Google Drive do projeto |
| Drenagem, massas d'água, ferrovias | `BC250 2021` (IBGE) | IBGE — Base Cartográfica Contínua |
| Vias, drenagem fina, nascentes | OpenStreetMap (Overpass) | OSM, com cache local |
| Bacia/região hidrográfica | tabela curada `outorgasys/gis/data/bacias_rs.json` | **não** é interseção com ottobacias da ANA |

As camadas oficiais da ANA (ottobacias, UPH, regiões hidrográficas, BHO)
**não estão disponíveis neste ambiente** (`metadados.snirh.gov.br` bloqueado).
Por isso:

- a classificação de bacia/região vem da tabela curada, e o laudo registra
  expressamente que **não** foi obtida por interseção vetorial com a ANA;
- o corpo hídrico mais próximo é tomado pela `drenagem_rs` do IBGE;
- a sigla do sistema aquífero (ex.: `L2`) é reportada literalmente — quando a
  base não traz a legenda, a plataforma **declara a ausência do nome em vez de
  interpretá-lo**;
- o Agente 6 lista cada camada ausente já com o **substituto aplicado**.

---

## Processo de exemplo

```bash
.venv/bin/python scripts/semente_campo_bom.py            # cria/atualiza
.venv/bin/python scripts/semente_campo_bom.py --limpar    # apaga e refaz
```

Poço tubular de 6″ em Campo Bom/RS (-29,6842; -51,0531 → UTM 22S
E 494.862,5 / N 6.716.205,8). Resultados esperados:

| Item | Valor |
|---|---|
| Município / bacia | Campo Bom / Bacia Hidrográfica do Rio dos Sinos |
| Corpo hídrico mais próximo | Rio dos Sinos — trecho de drenagem sem denominação a 358,95 m; o nome vem do trecho *denominado* mais próximo, a 1.073 m |
| Formação geológica | Depósitos aluviais e coluviais |
| `s_máx` / `Q_estável` | 2,872 m / 11,994 m³/h |
| `T` | 5,979 m²/h (1,661 × 10⁻³ m²/s) |
| `Q_ot` / vazão adotada | 13,738 m³/h / **11,994 m³/h** |
| Volume anual | 37.521,87 m³ |
| Saídas | 3 pranchas, 3 gráficos, laudo PDF de 10 páginas, minuta |

### Sobre os anexos do exemplo

Os anexos do processo de exemplo (**matrícula do imóvel, análise laboratorial,
declaração de separação de redes e as quatro fotos**) são **gerados pela
plataforma** e marcados como *"DOCUMENTO DE EXEMPLO — NÃO VÁLIDO PARA
PROTOCOLO"*. Existem apenas para permitir a validação ponta a ponta. Em uso
real cada um é substituído pelo documento original (cartório de registro de
imóveis, laboratório acreditado, responsável técnico).

O ensaio de bombeamento do exemplo é **sintético**, construído pela solução
direta de Cooper-Jacob e Theis/Jacob-Lohman, de modo que o Agente 3 deve
recuperar a transmissividade de entrada (erro de ~0,3 %).

---

## Testes

```bash
.venv/bin/python tests/smoke_ui.py       # todas as páginas com processo vazio
.venv/bin/python tests/smoke_exemplo.py  # todas as páginas com o exemplo carregado
.venv/bin/python tests/test_agents.py    # regras e memória de cálculo (se presente)
```

Ambos usam `streamlit.testing.v1.AppTest` e falham se qualquer página levantar
exceção (incluindo erro de sintaxe). O `smoke_ui.py` isola `data/processos` em
um diretório temporário para não poluir o repositório.

---

## Limitações conhecidas

- As camadas poligonais oficiais da ANA (ottobacias, UPH, regiões
  hidrográficas) permanecem indisponíveis neste ambiente (`metadados.snirh.gov.br`
  bloqueado); a classificação de bacia vem da tabela curada e é declarada como tal.
- `rodovias_rs` e `nascentes_rs` **não foram localizadas** no geopackage da
  BC250 2021 nesta execução. O script `scripts/fetch_data.py` passou a registar
  explicitamente essa ausência (antes a camada simplesmente desaparecia do
  manifesto) e a usar correspondência por substring em vez de prefixo. As vias e
  as nascentes dos mapas vêm do OpenStreetMap, o que está declarado no laudo.
  Reexecute o workflow `build-vetorial-data` para nova tentativa.
- A camada de solos do projeto não cobre toda a mancha urbana: quando o ponto
  cai fora de um polígono, adota-se a unidade mais próxima e o laudo registra a
  aproximação.
- A consulta ao Overpass (OSM) depende de rede; sem ela, a plataforma segue com
  as bases estatais e as camadas enviadas pelo usuário.
- O Agente 6 **não** abre issues nem executa `git push`: prepara os artefatos e
  deixa a decisão para o operador.
