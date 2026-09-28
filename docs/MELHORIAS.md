# Revisão técnica e roadmap de melhorias — 2026-09-28

Revisão feita com agentes ECC (`python-reviewer`, `security-reviewer`) sobre o
código e a documentação. Smoke tests (`smoke_ui`, `smoke_exemplo`) passavam antes
e continuam passando após as correções.

## ✅ Aplicado nesta revisão

| Área | Correção |
|---|---|
| Segurança | **Path traversal em uploads**: nome do arquivo reduzido ao basename (`state.nome_arquivo_seguro`) em `state.py`, `pages/2_*` e `pages/3_*` |
| Segurança | **Injeção de comando no workflow** `build-vetorial-data.yml`: `inputs.only` agora passa por `env:` e é citado |
| Cálculo | **Desalinhamento t'/s'** na recuperação (`theis.calcular`): a mesma máscara é aplicada aos dois vetores; tamanhos diferentes geram aviso |
| Cálculo | Faixa de transmissividade: código testava 1e-4..1,0 m²/s e a mensagem dizia 1e-5..1e-1. Unificado em constantes `T_M2S_MIN/MAX` |
| Robustez | `agente4_balanco`: soma da reservação usa `rules._num` (aceita vírgula decimal, não derruba com `"1,5"`) |
| Limpeza | Código morto em `identificar_q_estavel` (`... if False else ...`) |
| Testes | `tests/test_theis.py`: primeiros testes unitários com resultado analítico (Cooper-Jacob, Q_estável, recuperação, traversal) |

## 🔜 Pendente (priorizado)

### Alto
1. **Autenticação**: o serviço no Render é público; qualquer visitante lista, abre
   e envia arquivos para processos. Antes de usar dados reais: `st.login`/senha
   ou proxy autenticado. Manter só dados fictícios no repositório.
2. **XSS / HTML sem escape**: `ui.py` (`chip`, `fonte`) e `pages/6_Agente_Dev.py`
   interpolam texto livre (defeitos manuais, logs) em `unsafe_allow_html`.
   Aplicar `html.escape()`.
3. **Popups do Folium**: atributos de camadas enviadas pelo usuário vão sem escape
   para o HTML exibido via `components.html`. Escapar antes de gerar o popup.
4. **Cobertura de testes**: estender `test_theis.py` para `agente4_balanco`
   (quadro de vazão, escolha da vazão adotada) e `rules.py`; adotar `pytest` +
   `pytest-cov` e rodar no GitHub Actions.

### Médio
5. Erros silenciados: `docreader/engine.py` (`except Exception: pass` nas
   tabelas do Docling; fallback para PyMuPDF sem log) e `theis.py` (fallback
   Theil-Sen → mínimos quadrados sem avisar; `except` genérico no Jacob-Lohman).
6. Jacob-Lohman usa `S = 1e-4`, `t = 365 d` e `r = 0,10 m` fixos sem aviso ao
   usuário; o ramo "último recurso" em `agente4.escolher_vazao_adotada` é quase
   inalcançável. Declarar as premissas no laudo ou remover o ramo.
7. `agente4`: docstring fala em "dias úteis" mas o cálculo é fracionário sobre
   dias corridos; total anual soma valores não arredondados enquanto a coluna
   exibe arredondados. Confirmar a regra do SIOUT e alinhar.
8. `agente4`: origem da vazão decidida por igualdade de float (`adotada == q_ot`);
   trocar por `q_ot <= q_est`.
9. Skills duplicadas: `skills/gis-multicamadas` e `skills/gis_multicamadas`.
   Manter uma só e fixar o caminho em `gis/multicamadas.py`.
10. Workflows: fixar actions por SHA, revisar `contents: write` com push direto,
    parar de versionar `data/.probe.log`.
11. Fixar versões em `requirements.txt` (ou lock com hashes) para builds
    reprodutíveis no Render.

### Baixo
12. `theis.py`: o laço "amplia a janela" em `identificar_q_estavel` é redundante.
13. `_arr` usa `x == x` como teste de NaN; preferir `math.isnan`.
14. Tipagem: anotar `proc: Processo` nos agentes; `TypedDict`/dataclass nos
    retornos públicos.
15. Histórico do git dominado por `chore(auto-sync)`; usar commits convencionais
    descritivos nas mudanças de código.
