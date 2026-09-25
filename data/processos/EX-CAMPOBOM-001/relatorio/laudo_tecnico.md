# LAUDO TECNICO DE CARACTERIZACAO HIDROGEOLOGICA
## MEMORIAL DESCRITIVO PARA OUTORGA DE AGUA SUBTERRANEA - SIOUT/RS

**Processo:** EX-CAMPOBOM-001  
**Data de emissao:** 25/09/2026  
**Sistema:** outorgasys v1.0.0


## 1. IDENTIFICACAO DO REQUERENTE E DA PROPRIEDADE

### 1.1 Requerente
| Item | Valor |
|---|---|
| Nome / Razao social | Metalurgica Sinos Ltda. |
| CPF / CNPJ | 00.000.000/0001-00 |
| RG / Inscricao estadual | 000/0000000 |
| Telefone | (51) 3597-0000 |
| E-mail | meioambiente@example.com.br |

### 1.2 Imovel e localizacao
| Item | Valor |
|---|---|
| Denominacao | Parque Industrial - Galpao 3 |
| Endereco | Rua das Aguas, 1250 |
| Bairro / Localidade | Operaria |
| Municipio / UF | Campo Bom / RS |
| CEP | 93700-000 |
| Coordenadas (SIRGAS 2000) | -29.6842, -51.0531 |
| Coordenadas UTM | E 494.862,5 m / N 6.716.205,8 m - fuso 22S (EPSG:31982) |
| Bacia hidrografica | Bacia Hidrografica do Rio dos Sinos |
| Regiao hidrografica | Regiao Hidrografica do Guaiba |
| Area do terreno (ha) | 1.8 |

### 1.3 Documentacao de posse e terra
| Documento | Situacao |
|---|---|
| Certidao de registro de imoveis / matricula atualizada | Anexado |


## 2. CARACTERIZACAO CONSTRUTIVA E GEOLOGICA

### 2.1 Poco
| Item | Valor |
|---|---|
| Tipo de poco | Opcao B - Poco tubular profundo |
| Classe SIOUT | poco_tubular_profundo |
| Diametro util (pol) | 6,00 |
| Profundidade total (m) | 82,00 |
| Diametro da perfuracao (mm) | 250 |
| Diametro do revestimento (mm) | 152 |
| Espaco anular (mm) | 49,0 |
| Profundidade do selo sanitario (m) | 22,00 |
| Posicao do crivo (m) | 40,00 a 78,00 |
| Formacao geologica | Depósitos aluviais e coluviais |
| Litologia predominante | Areia, Sedimento elúvio-coluvionar |
| Classe de solo | Podzólico Vermelho-Amarelo álico |
| Sistema aquifer | L2 |
| Tipo de aquifer | poroso livre (sedimentos aluviais) |

### 2.2 Laje de protecao sanitaria
| Item | Valor |
|---|---|
| Espessura (cm) | 15,0 |
| Area (m2) | 1,44 |
| Cota do rebordo (cm) | 35,0 |

_Referencias: espessura minima 10 cm, area minima 1 m2, rebordo minimo 30 cm; espaco anular minimo 75 mm; selo sanitario minimo recomendado 20 m._

### 2.3 Corpo hidrico mais proximo e raio de seguranca
| Item | Valor |
|---|---|
| Corpo hidrico mais proximo | Rio dos Sinos |
| Distancia (m) | 358,9 |


**Ocorrencias no raio de seguranca de 500 m:**
- vias: 114 feicao(oes)


## 3. PARAMETROS HIDRAULICOS E RESULTADOS DO ENSAIO

| Parametro | Valor | Criterio / Formula |
|---|---|---|
| Nivel estatico (NE) | 8,00 m | Medido a partir da boca do tubo |
| Nivel dinamico estabilizado (ND) | 10,87 m | Fim do bombeamento continuo |
| Rebaixamento maximo (s_max = ND - NE) | 2,87 m | Rebaixamento maximo observado |
| Vazao estabilizada (Q_estavel) | 11,99 m3/h | patamar terminal (CV <= 10%) |
| Δs' (reta de recuperacao) | 0,3671 m/ciclo | s' = +0.3671·log10(t/t') +0.0031   (R² = 0.9917) |
| Transmissividade (T) | 5,979 m2/h | T = 0,183 · Q_estavel / Δs' |
| Transmissividade (T) | 0,001661 m2/s | T(m2/h) / 3600 |
| Capacidade especifica do poco (q) | 4,176 m3/h/m | q = Q_estavel / s_max |
| Capacidade especifica de longo prazo (q(t)) | 4,783 m3/h/m | q(t) = 0,8 · T  (fator 0.8) |
| Vazao otima de explotacao (Q_ot) | 13,74 m3/h | Q_ot = q(t) · s_max |
| Contraprova Jacob-Lohman | 4,14 m3/h | Estimativa independente de longo prazo |
| Duracao do ensaio | 24,0 h | 1.440 min |

### 3.1 Graficos do ensaio
![Graficos do ensaio](data\processos\EX-CAMPOBOM-001\graficos\graficos_ensaio.png)


## 4. DESCRICAO DOS EQUIPAMENTOS INSTALADOS

### 4.1 Motobomba submersa
| Item | Valor |
|---|---|
| Fabricante | Exemplo Bombas |
| Modelo | Submersa 4" 5 estagios |
| Numero de serie | B2024-000345 |
| Diametro (pol) | 4,00 |
| Potencia (HP/CV) | 3,00 |
| Numero de estagios | 5 |
| Profundidade de instalacao (m) | 36,00 |
| Vazao nominal (m3/h) | 12,00 |
| Altura manometrica (m.c.a.) | 62,0 |

### 4.2 Hidrometro
| Item | Valor |
|---|---|
| Fabricante | Exemplo Hidrometros |
| Modelo | Volumetrico DN32 |
| Numero de serie | H2024-001122 |
| Diametro nominal (DN) | 32 |
| Vazao nominal (m3/h) | 2,50 |
| Classe metrologica | Classe B (horizontal) |

### 4.3 Reservacao
| Item | Valor |
|---|---|
| Quantidade de reservatorios | 2 |
| Capacidade total (L) | 7.000 |
| Capacidade total (m3) | 7,000 |

| Reservatorio | Capacidade | Local |
|---|---|---|
| Reservatorio 1 | 5.000 L | Casa de maquinas |
| Reservatorio 2 | 2.000 L | Reservatorio elevado |
### 4.4 Auditoria tecnica dos equipamentos
- **MED-010** - Hidrometro abaixo da vazao de operacao: Vazao adotada de 11.9939 m3/h excede a vazao nominal do hidrometro (2.5 m3/h). O instrumento operara acima da faixa de trabalho, com perda de precisao metrologica e desgaste acelerado.
- **MED-020** - Velocidade excessiva no hidrometro: Velocidade media estimada de 4.14 m/s no hidrometro DN32. Recomenda-se ate 3 m/s para preservar a classe de precisao.


## 5. FLUXOGRAMA E MEMORIAL DO SISTEMA DE ABASTECIMENTO

### 5.1 Memorial descritivo do percurso da agua
- **1. Captacao** - Agua subterranea captada no poco tubular PT-01, perfurado na Depósitos aluviais e coluviais, sistema aquifer L2, a 82,0 m de profundidade.
- **2. Automacao / recalque** - Motobomba submersa Exemplo Bombas Submersa 4" 5 estagios, 3,0 HP/CV, instalada a 36,0 m, com 5 estagio(s). Partida por quadro de comando com protecao termica e nivel.
- **3. Medicao** - Hidrometro Exemplo Hidrometros Volumetrico DN32, DN 32 mm, vazao nominal 2,50 m3/h, instalado em cavalete na saida do poco.
- **4. Reservacao superior** - Reservacao total de 7.000 L distribuida em 2 reservatorio(s), instalada em cota superior aos pontos de consumo.
- **5. Rede de distribuicao** - Rede interna de distribuicao por gravidade a partir da reservacao superior, atendendo exclusivamente as finalidades declaradas.

### 5.2 Fluxograma esquematico em bloco
```
  [ POCO TUBULAR ]
        |
        v
  [ MOTOBOMBA SUBMERSA ] ---- [ QUADRO DE COMANDO / PROTECAO ]
        |
        v
  [ CAVALETE + HIDROMETRO ]
        |
        v
  [ RESERVATORIO SUPERIOR (caixa d'agua) ]
        |
        v
  [ REDE DE DISTRIBUICAO INTERNA / EXTERNA ]
        |
        v
  [ PONTOS DE CONSUMO (finalidades declaradas) ]
```

## 6. QUADRO DE VAZAO HOMOLOGADO DO SIOUT

### 6.1 Regime operacional
| Item | Valor |
|---|---|
| Horas por dia | 12,00 h/dia |
| Dias por semana | 5 dias/semana |
| Vazao adotada | 11,994 m3/h |
| Origem da vazao | Q_estavel |
| Justificativa | Adota-se o menor valor entre Q_ot (vazao otima de campo, que ja incorpora o fator de seguranca de longo prazo de 0.8) e Q_estavel, por criterio de seguranca hidrogeologica e preservacao do aquifero. |
| Repouso diario | 12,00 h |
| Repouso minimo exigido | 4 h/dia (SIOUT RS) |

### 6.2 Quadro de Vazao da Intervencao
| Mes | Dias/Mes | Horas/Dia | Vazao (m3/h) | Volume (m3/mes) |
|---|---|---|---|---|
| Janeiro | 22.14 | 12.0 | 11.994 | 3186.55 |
| Fevereiro | 20.0 | 12.0 | 11.994 | 2878.55 |
| Marco | 22.14 | 12.0 | 11.994 | 3186.55 |
| Abril | 21.43 | 12.0 | 11.994 | 3084.36 |
| Maio | 22.14 | 12.0 | 11.994 | 3186.55 |
| Junho | 21.43 | 12.0 | 11.994 | 3084.36 |
| Julho | 22.14 | 12.0 | 11.994 | 3186.55 |
| Agosto | 22.14 | 12.0 | 11.994 | 3186.55 |
| Setembro | 21.43 | 12.0 | 11.994 | 3084.36 |
| Outubro | 22.14 | 12.0 | 11.994 | 3186.55 |
| Novembro | 21.43 | 12.0 | 11.994 | 3084.36 |
| Dezembro | 22.14 | 12.0 | 11.994 | 3186.55 |

**Volume anual total:** 37.522 m3/ano

**Vazao diaria maxima:** 143,93 m3/dia


## 7. PARECER CONCLUSIVO E RECOMENDACOES

### 7.1 Conclusoes
- O poco enquadra-se como Opcao B - Poco tubular profundo. Exige ensaio de bombeamento continuo de 24 horas acompanhado do ensaio de recuperacao, o qual foi apresentado e analisado.
- O ponto de captacao localiza-se no municipio de Campo Bom/RS, na Bacia Hidrografica do Rio dos Sinos, integrando a Regiao Hidrografica do Guaiba.
- A captacao ocorre na Depósitos aluviais e coluviais (Areia, Sedimento elúvio-coluvionar), integrando o L2.
- A vazao otima de explotacao de campo calculada e de 13,74 m3/h, obtida a partir da vazao estabilizada de 11,99 m3/h e do rebaixamento maximo de 2,87 m, com transmissividade de 5,979 m2/h (0,001661 m2/s).
- Recomenda-se a vazao de explotacao de 11,99 m3/h (Q_estavel), resultando em volume anual estimado de 37.522 m3/ano.
- O regime operacional proposto reserva 12,0 h/dia de repouso ao aquifero, atendendo ao repouso minimo de 4 h/dia exigido pelo SIOUT RS.
- O imovel e atendido por rede publica de abastecimento de agua. Declara-se a SEPARACAO FISICA DAS REDES HIDRAULICAS, sem qualquer interconexao, cross-connection ou by-pass entre a rede publica e a rede alimentada pelo poco, ficando a agua subterranea restrita as finalidades nao destinadas ao consumo humano direto.
- A distancia ao corpo hidrico superficial mais proximo ('Rio dos Sinos') e de 358,9 m, acima do limiar de 50 m que exigiria estudo de interferencia especifico.

### 7.2 Recomendacoes
- Manter sinalizacao permanente e distinta nas duas redes (padrao de cores diferenciado) e submeter o sistema a inspecao periodica, de modo a comprovar a ausencia de interconexao.
- Dentro do raio de seguranca de 500 m foram identificadas as seguintes ocorrencias: vias (114 feicao/feicoes). Recomenda-se vistoria de campo para avaliacao e mitigacao das fontes potenciais de poluicao, com prioridade para postos de combustivel, estacoes de tratamento de esgoto, tanques e areas industriais.
- [MED-010] Vazao adotada de 11.9939 m3/h excede a vazao nominal do hidrometro (2.5 m3/h). O instrumento operara acima da faixa de trabalho, com perda de precisao metrologica e desgaste acelerado.
- [MED-020] Velocidade media estimada de 4.14 m/s no hidrometro DN32. Recomenda-se ate 3 m/s para preservar a classe de precisao.
- Instalar e manter lacre e/ou sinalizacao no hidrometro, com leitura mensal registrada em planilha propria para fins de fiscalizacao da outorga.
- Manter a laje de protecao sanitaria integra, com tampa de acesso vedada e cercamento de protecao em bom estado de conservacao.
- Repetir a analise fisico-quimica e bacteriologica da agua em periodicidade minima semestral, conforme os parametros da Portaria GM/MS n. 888/2021.
- Em caso de rebaixamento anomalo, turbidez persistente ou reducao de vazao, suspender a operacao e comunicar o orgao gestor.

### 7.3 Declaracoes
- Imovel atendido por rede publica de abastecimento: **Sim**
- **Atestado de separacao de redes:** declara-se a separacao fisica integral das redes hidraulicas, sem interconexao entre a rede publica e a rede alimentada pelo poco.
- **Repouso diario minimo do aquifero:** 12,00 h (minimo exigido: 4 h/dia)

---

## RESPONSAVEL TECNICO

**Ana Paula Exemplo**  
Geologo  
Registro: CREA-RS 0000000000  
ART: ART RS2024 0000000  

____________________, 25/09/2026

_______________________________________________
Assinatura do Responsavel Tecnico

_Conforme a norma CEGM/CREA-RS n. 08/2022, o presente laudo deve ser assinado por profissional habilitado (Geologo ou Engenheiro de Minas) com a respectiva Anotacao de Responsabilidade Tecnica (ART)._

---

## APENDICE A - PROVENIENCIA DAS BASES GEOESPACIAIS

| Camada | Status | Origem | Feicoes |
|---|---|---|---|
| cursos_dagua_rs | ausente | ANA - Base Hidrografica Ottocodificada 2017 (cursos d'agua) | 0 |
| drenagem_rs | ok | IBGE - Base Cartografica Continua 1:250.000 (2021) / ANA BHO 2017 | 8 |
| geologia_rs | ok | Google Drive do projeto - 'Geologico Rio Grande do Sul.kmz' | 4 |
| hidrogeologia_rs | ok | Google Drive do projeto - 'Hidrogelogia_RS.kmz' | 1 |
| municipios_rs | ok | IBGE - Malha Municipal 2022 | 2 |
| osm | ok | OpenStreetMap (Overpass) - cache local | 1722 |
| otto_nivel_1 | ausente | ANA - BHO 2017 Otto nivel 1 | 0 |
| otto_nivel_2 | ausente | ANA - BHO 2017 Otto nivel 2 | 0 |
| otto_nivel_3 | ausente | ANA - BHO 2017 Otto nivel 3 | 0 |
| ottobacias_rs | ausente | ANA - BHO 2017 (areas de contribuicao hidrografica) | 0 |
| regioes_hidrograficas | ausente | ANA/SNIRH - 12 Regioes Hidrograficas definidas pelo CNRH | 0 |
| solos_rs | ok | Google Drive do projeto - 'Mapa de solos.kmz' | 2 |
| uph | ausente | ANA/SNIRH - Unidades de Planejamento Hidrico | 0 |