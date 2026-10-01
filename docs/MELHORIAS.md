# Revisão técnica e roadmap de melhorias

Última revisão: 2026-10-01. A anterior (2026-09-28) está registrada no fim deste
arquivo.

**O que mudou neste documento.** Dos 15 itens da lista de 2026-09-28, 9 foram
resolvidos, 3 resolvidos em parte (1, 4 e 10) e 3 seguem abertos (5, 14 e 15).
A revisão de hoje achou mais 25 problemas, todos corrigidos com teste que falhava
antes. Os títulos perderam os emojis, a tabela de aplicados ganhou a evidência
de cada defeito, e o que continua aberto ficou separado do que foi resolvido.

## Em números

| | 2026-09-28 | 2026-10-01 |
|---|---|---|
| Testes | 7 (só `theis`) | 148 |
| Cobertura de linha | não medida | 82% (47% antes do teste de caminho completo) |
| CI de testes | nenhum | `tests.yml`: ruff, pytest, os dois smoke tests |
| Smoke `smoke_exemplo.py` em Linux | 6 de 7 páginas, e reescrevia o JSON versionado | 7 de 7, em cópia temporária |

## Aplicado em 2026-10-01

Cada linha corresponde a um commit com o mesmo assunto; o corpo do commit traz a
reprodução.

### Quebrava no Render (Linux)

| Problema | Evidência | Correção |
|---|---|---|
| O JSON do exemplo guarda `data\processos\...` (gerado no Windows) | 35 caminhos com `\`; Agente 5 levantava `FileNotFoundError`; nenhuma imagem do exemplo aparecia | `caminho_absoluto` aceita os dois separadores; `caminho_relativo` grava `/`; o PDF também usa essa função |
| A página do Agente 3 trocava o ensaio salvo pelo resultado de uma leitura que falhou | Rodar o smoke apagou cerca de 690 linhas do JSON versionado (`ensaio.ok` virou `false`) | Só substitui quando a leitura funciona; senão avisa e mantém o salvo |
| `DataFrame` salvo em JSON voltava como dict | A página só funcionava porque relia a planilha a cada execução | `_restaurar_json` fecha o ciclo salvar/carregar |
| `import outorgasys.docreader` falhava (`No module named 'fitz'`) | PyMuPDF não está no `requirements.txt` | `pypdf` como padrão; PyMuPDF e Docling opcionais. Os 12 parâmetros do laudo de exemplo saem iguais aos do Docling |
| Coluna Q vazia ou com lacunas derrubava o Agente 3 | `ValueError` de broadcast, shapes `(59,)` e `(0,)` | Pares (t, Q) válidos; `identificar_q_estavel` não levanta mais |
| `st.components.v1.html` removido "após 2026-06-01" | Aviso a cada abertura do mapa | `st.iframe` quando existe |
| `streamlit>=1.30` | `width="stretch"` só existe em `st.button` a partir do 1.48 e em `st.image` do 1.49 | Piso 1.49, conferido rodando a suíte com `streamlit==1.49.0` |

### Segurança

| Problema | Evidência | Correção |
|---|---|---|
| `remover_upload` apagava fora do diretório | O registro guardava `uploaded.name` cru; com `../../x.json` o teste apagou o arquivo-alvo | O registro usa o nome saneado e `remover_upload` sanea antes do `unlink` |
| `pid` sem validação | `Processo(pid="../x")` apontava para fora de `data/processos` | `validar_pid`: `[A-Za-z0-9][A-Za-z0-9_-]{0,63}` |
| Texto do usuário em HTML da interface | Nome de arquivo `<img onerror=...>` virava markup na Triagem | `ui.escapar` em chips, pendências, cabeçalho, rodapé e nos pontos dinâmicos |
| Atributos de camadas no mapa Folium | O tooltip usa `innerHTML` num iframe com scripts e acesso same-origin (a docstring de `st.iframe` avisa) | Escape de colunas e valores antes de chamar a skill; skill vendorizada intacta |
| Texto livre no `Paragraph` do ReportLab | `<img src="caminho">` embutiu um mapa de outro processo no PDF; `<Sul>` sumia do laudo | `_dado()` escapa; o comentário de `_sanitize` dizia que escapava e não escapava |
| JSON com BOM ou corrompido virava "processo inexistente" | O próximo `salvar()` sobrescrevia o original | Lê `utf-8-sig`; JSON ilegível é renomeado para `.corrompido-<data>` |
| App público, sem senha | Qualquer visitante lista e baixa qualquer processo | Portão opcional `OUTORGASYS_SENHA` (ver limites em `outorgasys/auth.py`) |
| Actions por tag mutável, com `contents: write` | `@v4`, `@v5` | Fixadas por SHA; Dependabot mantém. `contents: write` fica porque os fluxos de dados fazem push |

### Resultado numérico

| Problema | Evidência | Correção |
|---|---|---|
| Contraprova de Jacob-Lohman pela metade | `2π` onde Cooper-Jacob invertido pede `4π`; contra Theis exato (`4πTs / W(u)`) o código dava 4,23 contra 8,47 m³/h | `4π`; as premissas (S, t, r) aparecem na tabela do laudo |
| Vazão manual não entrava no cálculo de `T` | Sem Q na planilha, `T` e `Q_ot` ficavam vazios | A vazão manual entra em `calcular` |
| Limites de potabilidade desatualizados | Cádmio 0,005, dureza 500 e STD 1000 são do Anexo XX da PRC 5/2017 | 0,003, 300 e 500 mg/L ([Portaria GM/MS 888/2021](https://bvsms.saude.gov.br/bvs/saudelegis/gm/2021/prt0888_07_05_2021.html), Anexos 9 e 11); teste garante que as duas tabelas do código não divergem |
| E. coli "Presente" saía como conforme | Só reprovava se achasse um número maior que zero | Interpreta presença, positivo, detectado, ausência e `< 1,0 NMP/100 mL` |
| Laudo sem parâmetros lidos saía "conforme" | `conforme_geral` começava em `True` | Devolve `None` e um aviso; a Triagem mostra o aviso |
| `_num("nan")` e `_num("inf")` passavam | `validar_padrao_explotacao("nan", 3)` não gerava pendência | Só números finitos |
| Total anual do quadro não fechava com as linhas | 1735 de 2000 regimes testados; no exemplo 37.521,87 contra 37.521,84 | Cada linha é arredondada antes de somar |

### Interface, qualidade e testes

- A seção "Parecer conclusivo" da página 5 mostrava um chip vermelho com "-": lia
  chaves que o laudo não grava. Agora lista `conclusoes` e `recomendacoes`.
- O botão de download do relatório do Agente 6 ficava sempre desabilitado
  (apontava para uma pasta `out/` que não existe).
- Cada rerun do Streamlit regravava o upload e somava uma linha ao log do
  processo; o registro agora é idempotente (nome saneado e SHA-256).
- `_arr` aceita texto, `None` e `pd.NA`; o laço "amplia a janela" que nunca
  executava saiu (teste de equivalência com 300 séries aleatórias).
- `requirements.txt`: tetos no próximo major, três pacotes sem uso removidos,
  instalação limpa conferida. `skills/gis_multicamadas` (cópia antiga) removida.
- Testes de caminho completo sobre o exemplo (`test_pipeline_exemplo.py`, cerca
  de 20 s), de escape, de autenticação e de cada módulo alterado. Os smoke tests
  contam imagens de verdade e passam em Streamlit 1.49 e 1.64.

## Pendente (priorizado)

### Alto
1. **Regenerar o exemplo versionado.** O JSON, o laudo e o PDF em
   `data/processos/EX-CAMPOBOM-001*` ainda mostram a contraprova antiga (4,14
   m³/h) e o volume anual de 37.521,87 m³. Rode
   `python scripts/semente_campo_bom.py --limpar` numa máquina com rede (os mapas
   baixam tiles) e faça commit. Não regenerei aqui porque, sem rede, os mapas
   sairiam sem imagem de fundo.
2. **Conferência pelo responsável técnico**, que o código não resolve sozinho:
   - contraprova de Jacob-Lohman com `4π` e premissas S = 1e-4, t = 365 d;
   - regra do SIOUT para dias de operação fracionários (31 × 5 / 7 = 22,14);
   - faixa de pH (6,0 a 9,5) em `water_quality.py` e `config.py`: o trecho da
     Portaria 888/2021 consultado não traz essa recomendação;
   - cianeto (0,07 mg/L) saiu do Anexo 9 em 2021 e continua nas tabelas como
     referência.
3. **Acesso por pessoa.** O portão por senha é compartilhado e sem trilha de
   auditoria. Para usuários individuais: `st.login` (OIDC) ou proxy autenticado.

### Médio
4. Erros silenciados: `docreader/engine.py` (`except Exception: pass` nas tabelas
   do Docling), `theis.ajustar_reta_recuperacao` (cai de Theil-Sen para mínimos
   quadrados sem aviso e ignora o parâmetro `metodo`).
5. `agente4.escolher_vazao_adotada`: o ramo "último recurso" com Jacob-Lohman não
   é alcançável (a contraprova só existe quando há `Q_estável`) e, se fosse,
   adotaria uma estimativa informativa como vazão do quadro. Remover.
6. Os JSONs de processo guardam CPF/CNPJ e endereço em texto no disco. Definir
   retenção e acesso (LGPD) antes de dados reais.
7. Lock com hashes para build reprodutível. Os tetos de major reduzem a variação,
   mas não a eliminam. O piso das bibliotecas numéricas (pandas 2.1, numpy 1.26)
   não é exercitado pela CI, que instala as versões mais novas.
8. `data/.probe.log` continua versionado a cada execução do `probe-fontes`.

### Baixo
9. Tipagem: anotar `proc: Processo` nos agentes; `TypedDict` ou dataclass nos
   retornos públicos.
10. Histórico dominado por `chore(auto-sync)`; usar commits descritivos nas
    mudanças de código.
11. `rules`: a mensagem EQP-020 mistura português e inglês; em
    `validar_reservacao` o índice da mensagem refere-se à lista já filtrada.
12. `skill_bridge` sobe um processo Python por operação geométrica. Chamar o
    shapely em memória seria mais rápido, mas a integração por skill faz parte
    do desenho.
13. `novo_id()` usa 24 bits aleatórios; com o portão de senha ativo o risco cai.

## Como verificar

```bash
pip install -r requirements-dev.txt
python -m pytest                       # 148 testes, cerca de 40 s
python tests/smoke_ui.py               # páginas com processo vazio
python tests/smoke_exemplo.py          # páginas com o exemplo (cópia temporária)
ruff check .
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
