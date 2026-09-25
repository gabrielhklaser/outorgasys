# RELATORIO DE DEFEITOS E PLANO DE CORRECAO

**Processo:** EX-CAMPOBOM-001  
**Gerado em:** 25/09/2026 17:54:05  
**Sistema:** outorgasys v1.0.0

## 1. Resumo

- Total de achados: **11**
- Bloqueantes (criticos): **1**

| Severidade | Quantidade |
|---|---|
| critico | 1 |
| info | 10 |

| Agente | Quantidade |
|---|---|
| - - Ambiente | 1 |
| 2 - Inteligencia Espacial e Automacao GIS | 10 |

| Categoria | Quantidade |
|---|---|
| Base geoespacial | 10 |
| Ambiente e dependencias | 1 |

## 2. Ambiente

```json
{
  "python": "3.14.7",
  "plataforma": "Windows-11-10.0.26200-SP0",
  "skills": {
    "shapely-compute": true,
    "geopandas": true,
    "geomaster": true,
    "gis-multicamadas": true,
    "python": "C:\\Users\\Gabriel\\AppData\\Local\\Programs\\Python\\Python314\\python.EXE"
  }
}
```

## 3. Achados e plano de correcao

### D010 - [CRITICO] Dependencias ausentes

- **Categoria:** Ambiente e dependencias
- **Agente responsavel:** N/A
- **Origem:** diagnostico de ambiente
- **Detalhe:** Pacotes nao importaveis: fiona
- **Sugestao:** Reinstale com: pip install -r requirements.txt

**Passos de correcao:**
1. Reinstalar as dependencias: pip install -r requirements.txt.
2. Reiniciar a aplicacao.

### D001 - [INFO] Camada oficial ausente, com substituto declarado: regioes_hidrograficas

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** Agente 2 / registro de camadas
- **Detalhe:** status=ausente; arquivo regioes_hidrograficas.gpkg nao encontrado em data/vetoriais. Execute o workflow 'build-vetorial-data' no GitHub Actions. | Substituto aplicado: tabela de referencia curada do outorgasys (outorgasys/gis/data/bacias_rs.json) - CNRH Res. 32/2003 e CRH-RS UGRH. A origem alternativa esta declarada no laudo, conforme a politica de fallback local adotada para este ambiente.
- **Sugestao:** Se desejar a base oficial, deposite o arquivo em data/vetoriais/regioes_hidrograficas.gpkg.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

### D002 - [INFO] Camada oficial ausente, com substituto declarado: uph

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** Agente 2 / registro de camadas
- **Detalhe:** status=ausente; arquivo uph.gpkg nao encontrado em data/vetoriais. Execute o workflow 'build-vetorial-data' no GitHub Actions. | Substituto aplicado: nao ha substituto direto; a UPH nao e determinada quando a base da ANA esta indisponivel (campo fica em branco no laudo). A origem alternativa esta declarada no laudo, conforme a politica de fallback local adotada para este ambiente.
- **Sugestao:** Se desejar a base oficial, deposite o arquivo em data/vetoriais/uph.gpkg.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

### D003 - [INFO] Camada oficial ausente, com substituto declarado: ottobacias_rs

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** Agente 2 / registro de camadas
- **Detalhe:** status=ausente; arquivo ottobacias_rs.gpkg nao encontrado em data/vetoriais. Execute o workflow 'build-vetorial-data' no GitHub Actions. | Substituto aplicado: tabela de referencia curada do outorgasys. A origem alternativa esta declarada no laudo, conforme a politica de fallback local adotada para este ambiente.
- **Sugestao:** Se desejar a base oficial, deposite o arquivo em data/vetoriais/ottobacias_rs.gpkg.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

### D004 - [INFO] Camada oficial ausente, com substituto declarado: otto_nivel_3

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** Agente 2 / registro de camadas
- **Detalhe:** status=ausente; arquivo otto_nivel_3.gpkg nao encontrado em data/vetoriais. Execute o workflow 'build-vetorial-data' no GitHub Actions. | Substituto aplicado: tabela de referencia curada do outorgasys. A origem alternativa esta declarada no laudo, conforme a politica de fallback local adotada para este ambiente.
- **Sugestao:** Se desejar a base oficial, deposite o arquivo em data/vetoriais/otto_nivel_3.gpkg.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

### D005 - [INFO] Camada oficial ausente, com substituto declarado: otto_nivel_2

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** Agente 2 / registro de camadas
- **Detalhe:** status=ausente; arquivo otto_nivel_2.gpkg nao encontrado em data/vetoriais. Execute o workflow 'build-vetorial-data' no GitHub Actions. | Substituto aplicado: tabela de referencia curada do outorgasys. A origem alternativa esta declarada no laudo, conforme a politica de fallback local adotada para este ambiente.
- **Sugestao:** Se desejar a base oficial, deposite o arquivo em data/vetoriais/otto_nivel_2.gpkg.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

### D006 - [INFO] Camada oficial ausente, com substituto declarado: otto_nivel_1

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** Agente 2 / registro de camadas
- **Detalhe:** status=ausente; arquivo otto_nivel_1.gpkg nao encontrado em data/vetoriais. Execute o workflow 'build-vetorial-data' no GitHub Actions. | Substituto aplicado: tabela de referencia curada do outorgasys. A origem alternativa esta declarada no laudo, conforme a politica de fallback local adotada para este ambiente.
- **Sugestao:** Se desejar a base oficial, deposite o arquivo em data/vetoriais/otto_nivel_1.gpkg.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

### D007 - [INFO] Camada oficial ausente, com substituto declarado: cursos_dagua_rs

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** Agente 2 / registro de camadas
- **Detalhe:** status=ausente; arquivo cursos_dagua_rs.gpkg nao encontrado em data/vetoriais. Execute o workflow 'build-vetorial-data' no GitHub Actions. | Substituto aplicado: drenagem_rs (IBGE BC250 2021) - mesma rede hidrografica, em formato de eixos, ja usada no calculo de distancia. A origem alternativa esta declarada no laudo, conforme a politica de fallback local adotada para este ambiente.
- **Sugestao:** Se desejar a base oficial, deposite o arquivo em data/vetoriais/cursos_dagua_rs.gpkg.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

### D008 - [INFO] Camada do inventario ausente, com substituto declarado: nascentes_rs

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** Agente 2 / inventario de bases
- **Detalhe:** status=ausente;  | Substituto aplicado: nascentes do OpenStreetMap (natural=spring) - ja usadas no Mapa 3 (hidrografico e hidrogeologico)
- **Sugestao:** Deposite o arquivo em data/vetoriais/nascentes_rs.gpkg.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

### D009 - [INFO] Camada do inventario ausente, com substituto declarado: rodovias_rs

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** Agente 2 / inventario de bases
- **Detalhe:** status=ausente;  | Substituto aplicado: vias do OpenStreetMap (highway) - ja usadas no Mapa 1 (localizacao e situacao)
- **Sugestao:** Deposite o arquivo em data/vetoriais/rodovias_rs.gpkg.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

### D011 - [INFO] Camadas obrigatorias ausentes, porem com substituto declarado

- **Categoria:** Base geoespacial
- **Agente responsavel:** 2
- **Origem:** diagnostico de ambiente
- **Detalhe:** regioes_hidrograficas. Mitigacao: regioes_hidrograficas -> tabela de referencia curada do outorgasys (outorgasys/gis/data/bacias_rs.json) - CNRH Res. 32/2003 e CRH-RS UGRH
- **Sugestao:** Nenhuma acao obrigatoria: a origem alternativa e declarada no laudo.

**Passos de correcao:**
1. Confirmar se o arquivo da camada existe em data/vetoriais/.
2. Se ausente, executar o workflow 'build-vetorial-data' no GitHub Actions.
3. Se o servidor de origem estiver bloqueado, converter a base no ambiente do usuario e depositar o .gpkg em data/vetoriais/.
4. Reprocessar o Agente 2 para o ponto informado.

---

## 4. Como registrar

O corpo da issue do GitHub para cada achado pode ser gerado pela interface do Agente 6 (botao de copia). Nenhuma acao externa e executada automaticamente: a abertura de issues e a submissao de commits ficam a cargo do operador.