# Revisão técnica e roadmap de melhorias

Última revisão: 2026-10-01 (retomada no mesmo dia). A de 2026-09-28 está no fim
deste arquivo.

**O que mudou nesta revisão.** A lista de 2026-09-28 ficou quase toda resolvida
na revisão da manhã; a retomada da tarde fechou o que faltava e que dava para
fechar sem o responsável técnico: o exemplo versionado foi regenerado offline,
os erros que caíam em silêncio agora avisam, o lock reprodutível existe e os
pisos de versão são exercitados pela CI. O que depende de decisão humana
(contraprova assinada, LGPD, login individual) continua em *Pendente*.

## Em números

| | 2026-09-28 | 2026-10-01 (manhã) | retomada |
|---|---|---|---|
| Testes | 7 (só `theis`) | 148 | 169 |
| Cobertura de linha | não medida | 82% | idem |
| CI de testes | nenhum | ruff, pytest, dois smoke | + job `piso` (versões mínimas) |
| Lock reprodutível | nenhum | tetos de major | `requirements.lock` com SHA-256 |
| Smoke `smoke_exemplo.py` | 6 de 7, reescrevia o JSON | 7 de 7, cópia temporária | 7 de 7 |

## Aplicado na retomada de 2026-10-01

### Exemplo versionado desatualizado (era Alto 1)

| Problema | Evidência | Correção |
|---|---|---|
| O JSON commitado mostrava a contraprova antiga e um total que não fechava | `Q_jacob_lohman_m3h` = 4,14 (2π) e volume anual 37.521,87 contra 37.521,84 das linhas | `scripts/semente_campo_bom.py --sem-mapas` refaz cálculos, laudo e PDF reaproveitando as pranchas; o JSON saiu com 8,29 m³/h e 37.521,84 |
| Caminhos gravados no formato Windows quebravam no Linux | `data\\processos\\...` com barra invertida no JSON | `caminho_relativo`/`caminho_absoluto` normalizam para `/` na regravação |
| Não dava para regenerar o exemplo sem tiles | as pranchas JPG dependem de imagem de base baixada da Esri/OSM | `agente2.analisar` ganhou `gerar_pranchas`: o mapa interativo (que só embute URLs) é redesenhado offline e as pranchas ficam intocadas; `--limpar --sem-mapas` é recusado para não apagar as pranchas boas |
| Nada impedia o exemplo de ficar para trás de novo | a correção da manhã não tocou no JSON | `tests/test_exemplo_versionado.py` recomputa a contraprova com 4π, confere o total com as linhas e os caminhos; falhou antes da regeneração (4,14 ≠ 8,29) e passa depois |

### Erros que caíam em silêncio (era Médio 4)

| Problema | Evidência | Correção |
|---|---|---|
| `ajustar_reta_recuperacao` ignorava `metodo` e trocava Theil-Sen por MQ sem aviso | sem scipy o laudo dizia "Theil-Sen" e usava outra reta | `metodo` é respeitado; a queda registra `Theil-Sen indisponivel (RuntimeError...)` em `observacao`, e método desconhecido também avisa |
| `except Exception: pass` no Docling engolia tabela e conversão | uma tabela de potabilidade ilegível sumia sem rastro | `DocumentoProcessado.avisos` recebe a falha da tabela e a queda geral; o Agente 1 registra cada aviso no log do processo |

### Vazão e validações (eram Médio 5 e Baixo 11)

| Problema | Evidência | Correção |
|---|---|---|
| Jacob-Lohman como "último recurso" da vazão adotada | o ramo só é alcançável sem Q_estavel, mas a estimativa só existe com Q_estavel | ramo removido; a justificativa cita a estimativa como contraprova, sem virar vazão do quadro |
| `validar_reservacao` nunca emitia RES-002 e numerava pelo filtro | `_num(0)` é falso, então capacidade 0 saía da lista antes do laço | índice vem da lista informada; capacidade 0 ou ilegível gera RES-002 no número certo |
| EQP-020 misturava inglês e cedilha | "...evitar cavitation e sucção de ar." | "cavitacao e succao de ar", ASCII como o resto das mensagens |

### Infraestrutura (eram Médio 7, Médio 8 e Baixo 13)

| Problema | Evidência | Correção |
|---|---|---|
| Cada sondagem de fontes empurrava um commit | `data/.probe.log` versionado; fluxo com `contents: write` | o resultado vai para o sumário da execução e um artefato de 30 dias; `permissions: contents: read` e arquivo no `.gitignore` |
| Lock e pisos não existiam | tetos de major reduzem variação, mas não a eliminam; os pisos nunca eram testados | `requirements.lock` (uv, `--generate-hashes --universal`) instala com `pip --require-hashes`, conferido num venv limpo; `requirements-piso.txt` + job `piso` na CI: 168 passaram, 1 pulado (st.iframe) |
| Nada acusava lock fora dos limites de `requirements.txt` | divergência passaria em silêncio | `tests/test_lock_requisitos.py`; verificado trocando o piso do numpy para `>=2.5` e vendo o teste acusar `numpy==2.4.6 fora de >=2.5,<3` |
| `novo_id` com 24 bits | `uuid4().hex[:6]` para um id que aparece na URL | `secrets.token_hex(5)` (40 bits), formato `AAAAMMDD-XXXXXXXXXX` dentro do `validar_pid` |
| `proc` sem tipo nos agentes | 19 assinaturas públicas sem anotação | `proc: Processo` sob `TYPE_CHECKING` nos seis agentes |

## Pendente (priorizado)

### Alto
1. **Conferência pelo responsável técnico**, que o código não resolve sozinho:
   - contraprova de Jacob-Lohman com `4π` e premissas S = 1e-4, t = 365 d (o valor
     de 8,29 m³/h do exemplo segue sendo uma estimativa de ordem de grandeza);
   - regra do SIOUT para dias de operação fracionários (31 × 5 / 7 = 22,14);
   - faixa de pH (6,0 a 9,5) em `water_quality.py` e `config.py`: o trecho da
     Portaria 888/2021 consultado não traz essa recomendação;
   - cianeto (0,07 mg/L) saiu do Anexo 9 em 2021 e continua nas tabelas como
     referência.
2. **Acesso por pessoa.** O portão `OUTORGASYS_SENHA` é compartilhado e sem
   trilha de auditoria. Para usuários individuais: `st.login` (OIDC) ou proxy
   autenticado.

### Médio
3. Os JSONs de processo guardam CPF/CNPJ e endereço em texto no disco. Definir
   retenção e acesso (LGPD) antes de dados reais.

### Baixo
4. Histórico dominado por `chore(auto-sync)`; usar commits descritivos nas
   mudanças de código. (Os commits desta revisão seguem essa convenção; o
   histórico antigo fica como está.)
5. `skill_bridge` sobe um processo Python por operação geométrica. Chamar o
   shapely em memória seria mais rápido, mas a integração por skill faz parte
   do desenho.
6. Tipagem: `proc` foi anotado, mas os retornos públicos dos agentes ainda são
   `dict`; `TypedDict`/dataclass fica para uma próxima passada.

## Como verificar

```bash
pip install -r requirements-dev.txt
python -m pytest                       # 169 testes, cerca de 40 s
python tests/smoke_ui.py               # paginas com processo vazio
python tests/smoke_exemplo.py          # paginas com o exemplo (copia temporaria)
ruff check .
```

Ambiente sem tiles (CI, rede restrita) regenera o exemplo com:

```bash
python scripts/semente_campo_bom.py --sem-mapas
```

Ambiente com os pisos declarados e com o lock:

```bash
pip install -r requirements-piso.txt   # o que o job piso da CI roda
pip install --require-hashes -r requirements.lock
```

## Revisão de 2026-09-28 (histórico)

Feita com agentes ECC (`python-reviewer`, `security-reviewer`).

| Área | Correção |
|---|---|
| Segurança | Path traversal em uploads: nome reduzido ao basename (`state.nome_arquivo_seguro`) em `state.py`, `pages/2_*` e `pages/3_*` |
| Segurança | Injeção de comando no workflow `build-vetorial-data.yml`: `inputs.only` passa por `env:` e é citado |
| Cálculo | Desalinhamento t'/s' na recuperação (`theis.calcular`): mesma máscara nos dois vetores; tamanhos diferentes geram aviso |
| Cálculo | Faixa de transmissividade: o código testava 1e-4 a 1,0 m²/s e a mensagem dizia 1e-5 a 1e-1; unificado em `T_M2S_MIN/MAX` |
| Robustez | `agente4_balanco`: soma da reservação usa `rules._num` |
| Limpeza | Código morto em `identificar_q_estavel` (`... if False else ...`) |
| Testes | `tests/test_theis.py`: primeiros testes unitários com resultado analítico |
