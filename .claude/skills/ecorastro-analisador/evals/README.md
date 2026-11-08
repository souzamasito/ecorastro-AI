# Casos de teste — ecorastro-analisador

11 casos e 82 critérios, no formato de pastas do skill-creator (o mesmo lido por `claude plugin eval`). Cada pasta tem:

- `prompt.md`: configurações da execução e o pedido, como um usuário real escreveria;
- `case.yaml`: nome e descrição do resultado esperado;
- `graders/NN-*.md`: um critério verificável por arquivo;
- `files/` e `place-files.sh`: só no caso com arquivo de entrada.

## Cobertura

| Caso | Tipo de relato | O que testa principalmente |
|---|---|---|
| `buraco-acidente-simples` | Simples | Classificação direta, `ex02`, não inventar local, "ontem" sem data de referência |
| `fio-caido-emergencia` | Emergência | `ex01`, alerta antes de tudo, evidência literal de texto sem acentos |
| `calcada-cadeirante-ambigua` | Ambíguo | Caso de fronteira, `rd01`, categoria secundária, `ex03` |
| `multiplos-problemas-mesma-rua` | Múltiplos problemas | Segmentação em 3 ocorrências, efeito que não vira ocorrência, persistência |
| `relato-vago-sem-informacao` | Incompleto | `informacao_insuficiente`, não chutar categoria, perguntas ao cidadão |
| `dados-pessoais-versao-publica` | Dados pessoais | Interna × pública, residência que é o local do problema, arquivo protegido |
| `passarela-necessidade-infraestrutura` | Necessidade de infraestrutura | `natureza`, `ex02` + `ex04` = alta, "urgente" não é `ex01` |
| `ocupacao-irregular-alegacao` | Alegação de irregularidade | Pendente de verificação, linguagem neutra, `[NOME]`/`[EMPRESA]`, propina não pontua |
| `lote-csv-misto` | Lote (11 linhas) | Todos os resultados de triagem, linha vazia, data com referência, resumo, relatório consolidado, falso positivo de protocolo. Desde a 0.3.0 (critérios 11 a 14): escola como obra de adequação com `ex07`, esgoto em média pelos novos critérios, semáforos com `ex06` e resposta curta |
| `pessoa-desmaiada-fora-escopo` | Fora do escopo com perigo | `fora_escopo` com alerta de origem `triagem` (SAMU) |
| `dado-sensivel-terceiro` | Dado sensível de terceiro (desde a 0.2.0) | Seção 11.1: condição que sustenta fator × condição sem relação, `[DADO_SENSIVEL]`. Desde a 0.3.0, o critério 04 mede a proteção contra reidentificação (marcador único, menção coletiva mascarada, texto não publicável, relatório só com resumo); a checagem antiga do 04 virou o 08, mais estrita (singular) |

## Como vamos executar (Etapa 5)

1. **Execuções pareadas.** Para cada caso, duas execuções independentes e simultâneas, com o mesmo pedido:
   - `with_skill`: tem acesso à skill;
   - `without_skill`: sem a skill (comparação de base).

   Cada execução trabalha numa pasta própria, que faz o papel da raiz do projeto (as `saidas/` ficam dentro dela). No caso de lote, o CSV é copiado para essa pasta.
2. **Local dos resultados.** `.claude/skills/ecorastro-analisador-workspace/iteration-1/<caso>/{with_skill,without_skill}/`, com `outputs/`, `timing.json` e `grading.json`. A pasta já está no `.gitignore`, porque as saídas internas contêm o texto original dos relatos.
3. **Avaliação dos critérios.**
   - Os critérios objetivos são checados por script: `validar_analise.py`, leitura dos campos do JSON e busca de trechos proibidos nos arquivos públicos.
   - Os demais (conteúdo da resposta, linguagem de alegação) são avaliados lendo a resposta e o registro da execução.
   - Cada critério recebe aprovado ou reprovado, com a evidência.
4. **Consolidação.** O skill-creator gera `benchmark.json` com taxa de aprovação, tempo e tokens de cada configuração, e o visualizador abre as saídas lado a lado para a sua revisão.

Opcional, para repetir os mesmos testes pela linha de comando ou em integração contínua (execuções reais, cobradas):

```bash
cd .claude/skills/ecorastro-analisador && claude plugin eval . --allow-tools Write,Edit,Bash --scaffold
```

## Como interpretar

- **Dois tipos de critério.**
  - Critérios de **contrato** exigem os códigos e o formato do EcoRastro (`inf_pavimento`, `ex02`, validador sem erro). Sem a skill, a comparação de base deve falhar neles. Isso mostra o valor da padronização, não a "inteligência" da resposta.
  - Critérios de **comportamento** qualquer boa resposta poderia cumprir: não expor dados pessoais, não inventar endereço, priorizar a emergência, não afirmar alegação como fato, pedir o que falta.

  A diferença entre com e sem skill nos critérios de comportamento é o sinal mais importante.

  São de comportamento: buraco 05–07, fio 05, calçada 07, múltiplos 03 e 07, vago 03 e 05, dados 02, 05 e 08, passarela 05 e 07, ocupação 04–06, lote 07, 09 e 14, desmaiada 04 e 05, dado sensível 02, 04 (exceto o campo `texto_relato_publicavel`) e 07.
- **Critério que nunca discrimina.** Se passa com e sem skill sempre, provavelmente é fácil demais. Não é descartado automaticamente: veja a seção abaixo.
- **Falha só com a skill.** Indica instrução confusa ou que atrapalha. Leia o registro da execução, não só o resultado.
- **Variação.** Começamos com uma execução por configuração. Se um caso tiver resultado instável, repetimos 3 vezes antes de concluir.
- **Custo.** Tempo e tokens entram na comparação. A skill pode custar mais (scripts, validação); a pergunta é se o ganho compensa.
- **Pesos e faixas provisórios.** Quando uma nota de fator for razoável e ainda assim o nível parecer errado, o problema provavelmente está na matriz, não na análise. Esses casos serão anotados como candidatos a calibração.
- **Privacidade.** Cada falso positivo do validador (ex.: protocolo de 11 dígitos acusado como CPF) e cada falso negativo (ex.: nome que escapou do mascaramento) será registrado nas notas do benchmark e acrescentado às limitações documentadas em `scripts/validar_analise.py`.

## Critérios que passam nas duas configurações (mantidos de propósito)

Na iteração 1, estes 8 critérios passaram com e sem a skill. Eles não medem o ganho da skill, mas ficam no conjunto como **testes de regressão de comportamento**. Cada um protege algo que um modelo sem instrução já faz bem e que uma instrução nova da skill poderia estragar sem que ninguém notasse. Se algum passar a falhar só com a skill, a mudança mais recente atrapalhou.

| Critério | O que protege | Por que poderia regredir |
|---|---|---|
| `calcada-cadeirante-ambigua` 07 | Explicar em linguagem simples por que o caso é acessibilidade | Respostas cheias de códigos (`rd01`) sem explicação para quem não conhece a taxonomia |
| `multiplos-problemas-mesma-rua` 03 | Um problema com vários efeitos continua sendo uma ocorrência | Regras de segmentação mais rígidas poderiam separar "mosquito" do buraco |
| `multiplos-problemas-mesma-rua` 07 | Cada ocorrência apresentada com nível e motivo próprios | Um formato de resposta mais curto poderia fundir as ocorrências |
| `relato-vago-sem-informacao` 05 | Perguntas concretas ao cidadão | Pendências em código (`descricao_insuficiente`) no lugar de perguntas legíveis |
| `passarela-necessidade-infraestrutura` 05 | "Urgente" e acidente passado não viram emergência | Uma regra de emergência mais sensível dispararia alertas falsos |
| `ocupacao-irregular-alegacao` 06 | A alegação não pesa na prioridade | Fatores novos ligados a "gravidade da denúncia" |
| `pessoa-desmaiada-fora-escopo` 04 | Orientar o SAMU antes de tudo | Fluxo de triagem que começa pelo JSON |
| `pessoa-desmaiada-fora-escopo` 05 | Não tratar a pessoa como problema de calçada | Classificação forçada nas 7 categorias |

Revisão: se um destes passar com folga por várias iterações, um caso mais difícil sobre o mesmo comportamento pode substituí-lo. A troca é registrada aqui.

## Histórico de iterações

| Iteração | Skill | Casos | Resultado |
|---|---|---|---|
| 1 | 0.1.0 | 10 casos, com e sem skill | Com skill 69/70; sem skill 12/70 (comportamento: 20/21 × 12/21) |
| 2 | 0.2.0 | 6 casos afetados, comparados com a 0.1.0 (e o caso novo sem skill) | 0.2.0 45/45; 0.1.0 44/45; erro na 1ª validação: 0 × 5 execuções. Detalhes em `CHANGELOG.md` |
| 3 | 0.3.0 | 5 casos afetados, comparados com a 0.2.0 (saídas da iteração 2 reavaliadas com os critérios novos; calçada executada de novo) | 0.3.0 42/43; 0.2.0 38/43; sem skill 3/8 no dado sensível; erro na 1ª validação: 0 × 1. Detalhes em `CHANGELOG.md` |
