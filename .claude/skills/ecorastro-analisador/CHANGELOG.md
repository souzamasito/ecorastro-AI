# Changelog: ecorastro-analisador

## 0.3.1 (07/11/2026, Etapas 7 e 8)

Versões: skill 0.3.1 · schema 1.2.0 · matriz 1.1.0 · taxonomia 1.0.0 (sem mudança de contrato nem de matriz).

- **Rótulo do órgão em relatório público** (pendência 1 da 0.3.0). Com `texto_relato_publicavel = false`, `org_acessibilidade_inclusao` aparece como "Acessibilidade e inclusão". Motivo: o rótulo completo ("Direitos da pessoa com deficiência…") indicava o tipo de condição mascarada (critério 04 do caso `dado-sensivel-terceiro`, iteração 3). Arquivos: `references/relatorio.md` (seção 5 e lista de verificação) e `SKILL.md`.
- **Entrega acadêmica**, sem funcionalidade nova:
  - `README.md` na raiz do projeto;
  - `docs/integracao-django.md`;
  - `exemplos/` com três demonstrações.
- Política de retenção: continua como proposta para o Django.

## 0.3.0 (07/11/2026, complemento da Etapa 6)

Versões: skill 0.3.0 · schema **1.2.0** · matriz **1.1.0** · taxonomia 1.0.0 (códigos inalterados).
Cópia da 0.2.0 para comparação: `.claude/skills/ecorastro-analisador-workspace/skill-snapshot-0.2.0/`. Schemas anteriores: `assets/historico/`.

### Alterações e justificativas

1. **Matriz 1.1.0** (`references/priorizacao.md`, `scripts/calcular_prioridade.py`). Pesos (30/20/15/15/10/10) e faixas preservados.
   - Âncoras:
     - **A1**: risco à saúde, com a distinção explícita entre **risco potencial** (até 2) e **dano ocorrido relatado** (3), e entre dano relatado e comprovado (`verificado`);
     - **A2**: falha do próprio serviço essencial;
     - **A3**: acesso à moradia só quando bloqueado, sem reduzir barreiras de acessibilidade a serviço essencial;
     - **A4**: abrangência de serviços prestados por rua.
     - Motivo: os casos de esgoto e de dado sensível variavam entre execuções por falta de âncora (proposta de calibração, seção 3).
   - Regras:
     - **`ex06_falha_controle_trafego`**: só semáforo (`mob_semaforo`). É uma afirmação da análise, como `ex01`. O script recusa a regra sem abrangência e risco ≥ 2 sustentados por evidência literal;
     - **`ex07_barreira_acesso_servico_essencial`**: vulnerabilidade 3 e serviço ≥ 2, os dois `relatado`, calculada pelo script.
     - As duas são mínimos (`alta`) e só valem com evidência suficiente (seção 6.3).
   - Exemplos calculados novos: esgoto (9.5), semáforo (9.6) e escola (9.7).
2. **Classificação** (`references/categorias.md`).
   - Seção 5.1: **obra de adequação**. Um equipamento em uso que não cumpre exigência obrigatória, como a escola sem rampa, é `problema_existente` com `requer_obra_adequacao: true`, e não necessidade de infraestrutura.
   - Casos de fronteira para escola ou prédio sem acesso, semáforo inoperante e esgoto.
3. **Contrato 1.2.0** (`assets/analise.schema.json`).
   - Campos obrigatórios novos:
     - `ocorrencia.requer_obra_adequacao`, sempre `false` em necessidade;
     - `dados_pessoais.texto_relato_publicavel`, sempre `false` na interna e com `dado_sensivel`.
   - Regras `ex06`/`ex07` no enum.
   - Compatibilidade e conversão de documentos antigos (proposta): `docs/compatibilidade-versoes.md`.
4. **Proteção contra reidentificação** (`categorias.md` 11.1, `references/relatorio.md`, `SKILL.md`, `scripts/validar_analise.py`). Na versão pública, com dado sensível de pessoa identificável:
   - um único `[DADO_SENSIVEL]` por pessoa (erro do validador para dois seguidos);
   - menção coletiva à mesma característica mascarada (aviso do validador);
   - texto do relato não publicável: relatórios e painéis usam só o resumo anonimizado;
   - `descricao_neutra` sem ligação com a pessoa.

   Opções 1, 2 e 3 do documento de privacidade.
5. **Retenção** (`docs/politica-retencao-proposta.md`): proposta para o Django, não implementada. Inclui:
   - inventário dos dados;
   - prazos sugeridos, a validar com o encarregado de dados e a tabela de temporalidade;
   - anonimização no lugar de exclusão;
   - pedido do titular.
6. **Resposta curta no lote** (`SKILL.md`): uma linha por ocorrência, sem fatores nem justificativas; o detalhe fica nos arquivos. As demais melhorias de desempenho ficam para a integração (ver Pendências).
7. **Testes.**
   - `scripts/tests`: 111 → **133**, todos passando. Cobrem:
     - pesos e faixas inalterados;
     - exemplos 9.5 a 9.7;
     - `ex06` recusada sem evidência;
     - `ex07` só com fatores relatados;
     - interação com `ex04`/`ex01`;
     - campos do schema 1.2.0;
     - schemas históricos;
     - reidentificação.
   - Casos de avaliação: `dado-sensivel-terceiro` 04 reescrito (reidentificação); a checagem antiga virou o critério 08, que agora exige o singular. `lote-csv-misto` ganhou os critérios 11 a 14. Total: 82 critérios.
   - `avaliar.py` passa a carregar o validador e a matriz da versão anterior isolados (a matriz mudou). A versão usada na iteração 2 está em `avaliar_iteration-2.py`.
8. **Documentos de decisão atualizados**, sem apagar o texto original: `docs/proposta-calibracao-matriz.md` (seção 8) e `docs/questao-privacidade-reidentificacao.md` (Decisão).

### Resultados: iteração 3

Foram reavaliados 5 casos afetados: lote, dado sensível, e as regressões buraco, calçada e passarela. Nas saídas da 0.2.0, 4 casos são cópias da iteração 2, reavaliadas com os critérios novos; a iteração 2 não foi alterada. A calçada rodou de novo com a cópia da 0.2.0.

| | 0.3.0 | 0.2.0 |
|---|---|---|
| Critérios aprovados | **42/43** | 38/43 |
| Erro na primeira validação | **0 de 5 execuções** | 1 (calçada, 2 erros de schema) |
| Tokens (soma) | 502 mil | 463 mil (+8% na 0.3.0) |
| Tempo (soma) | 839 s | 788 s (+6%) |

| Caso | 0.3.0 | 0.2.0 | O que mudou |
|---|---|---|---|
| Lote | 14/14 | 10/14 | Escola: alta por `ex07`, obra de adequação (antes: média, necessidade). Esgoto: média 47 (antes: média 32, com fatores ausentes). Semáforos: alta por `ex06` (antes: média 33). Resposta com as 8 ocorrências, 9% menor |
| Dado sensível | 7/8 | 7/8 | Critério 04 (reidentificação): a 0.2.0 falha em tudo. A 0.3.0 cumpre marcador único, menção coletiva mascarada, texto não publicável e relatório só com resumo, mas falha pelo rótulo do órgão "Direitos da pessoa com deficiência" no relatório público. Prioridade alta 70 (antes: crítica 75), efeito da A3 |
| Sem skill (dado sensível) | 3/8 | | Reavaliação da saída da iteração 2 |
| Buraco, calçada, passarela | 7/7 cada | 7/7 cada | Mesmos níveis e pontuações (47, 45, 73): sem regressão |

- **Resposta curta e custo:** a resposta do lote ficou menor e mais completa, mas o lote custou mais (144 mil × 127 mil tokens; 324 s × 294 s). O custo está na análise e na validação de cada relato, não na resposta.
- **Onde ver:**
  - `.claude/skills/ecorastro-analisador-workspace/revisao-iteration-3.html`, com a iteração 2 como saída anterior;
  - `iteration-3/benchmark.md` e `iteration-3/benchmark.json`, com as notas do analista.

### Pendências de decisão

1. **Rótulo do órgão em relatório público com pessoa identificável.** "Direitos da pessoa com deficiência e acessibilidade" indica o tipo de condição. Opções:
   - usar um rótulo curto ("Acessibilidade e inclusão") nas versões públicas com `texto_relato_publicavel = false`;
   - ou aceitar o rótulo e ajustar o critério 04.
2. **Prazos de retenção** e marcador estruturado de condição mantida na interna (`docs/politica-retencao-proposta.md`, decisões 1 a 4).
3. **Conversão de documentos 1.1.0 → 1.2.0 no Django** (`docs/compatibilidade-versoes.md`): confirmar os valores padrão propostos.
4. **Desempenho**, deixado para a integração com o Django:
   - deduplicação por `hash_texto`;
   - análise de lotes em paralelo, com validação individual;
   - cache das instruções da skill;
   - avaliar a geração da versão pública por script, que mexe na arquitetura;
   - repetir casos 3 vezes para medir variação.
5. O critério 08 do dado sensível não diferencia a 0.2.0 da 0.3.0: fica como teste de regressão.

## 0.2.0 (07/11/2026, Etapa 6)

Versões: skill 0.2.0 · schema **1.1.0** · taxonomia 1.0.0 (códigos inalterados) · matriz 1.0.0 (inalterada).
Cópia da 0.1.0 para comparação: `.claude/skills/ecorastro-analisador-workspace/skill-snapshot-0.1.0/`.

### Alterações e justificativas

1. **Datas relativas sem data de referência** (contradição apontada na Etapa 5; causou erro na primeira validação em 5 execuções).
   - `assets/analise.schema.json` (1.1.0):
     - `data_ocorrencia` ausente passa a aceitar a expressão temporal literal em `evidencia`. A regra "ausente sem evidência" foi isolada em `$defs/ausente_sem_evidencia` e continua valendo para os demais campos e para os fatores.
     - `schema_version` passa a ser `"1.1.0"`.
     - Motivo: guardar a expressão permite ao Django converter a data quando souber o `recebido_em`.
   - `SKILL.md` e `references/categorias.md` (seção 1): mesma regra, no mesmo texto.
   - `scripts/validar_analise.py`: dois avisos novos para data ausente com expressão temporal: quando existe `recebido_em` (a data poderia ser inferida) e quando falta o `raciocinio`.
2. **Obra nova × manutenção** (falha da passarela 07 na Etapa 5).
   - `SKILL.md`: linha "Tipo de demanda" na resposta individual; no modo lote, separação entre manutenção e obra ou serviço novo; item na lista de verificação.
   - `references/relatorio.md`: rótulos com o fluxo de cada natureza.
3. **Dados sensíveis de pessoas identificáveis.**
   - `references/categorias.md`: nova seção 11.1, que define:
     - as características sensíveis;
     - quando uma pessoa é identificável;
     - o tratamento interna × pública, com a exceção da condição que sustenta um fator;
     - a regra para criança ou adolescente;
     - a linguagem genérica a usar na conversa.
   - `SKILL.md`: resumo da regra e itens na lista de verificação.
   - `scripts/validar_analise.py`: AVISO de termo sensível no singular na versão pública (`PADRAO_SENSIVEL`); falsos positivos e negativos documentados no próprio script.
4. **Processamento de lotes.**
   - `scripts/gerar_metadados.py lote --arquivo <csv|json> [--coluna-texto]`, num só comando:
     - mapeia as colunas;
     - gera os IDs e o hash de cada linha;
     - normaliza `canal` e `recebido_em` (só aceita data e hora ISO com fuso; nada é completado);
     - lista as linhas ignoradas e os avisos.
   - `scripts/calcular_prioridade.py --atualizar` aceita vários arquivos; um arquivo com erro não é gravado e não interrompe os outros.
   - Cada relato continua sendo analisado e validado individualmente.
5. **Testes.**
   - `scripts/tests`: 97 → **111** testes, todos passando. Cobrem: data ausente com expressão, versão do schema, lote por CSV e JSON, múltiplos arquivos e dado sensível.
   - Novo caso `evals/dado-sensivel-terceiro`, com 7 critérios.
   - `evals/README.md`: finalidade dos 8 critérios que passam com e sem a skill (mantidos como testes de regressão) e histórico de iterações.
6. **Documentos de decisão** (nada aplicado):
   - `docs/proposta-calibracao-matriz.md`;
   - `docs/questao-privacidade-reidentificacao.md`.

### Relatório da Etapa 6: iteração 2

Os 6 casos afetados foram executados com a 0.2.0 e comparados com a 0.1.0. O caso novo também rodou sem a skill.

| | 0.2.0 | 0.1.0 |
|---|---|---|
| Critérios aprovados | **45/45** | 44/45 |
| Erro na primeira validação | **0 execuções** | 5 execuções |
| Tempo médio | 144 s | 146 s |
| Tokens médios | 90 mil | 86 mil (+5% na 0.2.0) |

- **Passarela 07:** a 0.2.0 corrige esse critério. A resposta agora explica que é obra nova, para o planejamento.
- **Caso novo:**
  - 0.2.0 e 0.1.0 tiveram 7/7. As duas protegem o nome e a sorologia; a 0.2.0 mantém "cadeirante" na versão interna, como a seção 11.1 prevê.
  - Sem a skill, 3/7: privacidade boa, mas sem o contrato JSON.
  - O critério 04 não distingue as duas versões; melhorá-lo é uma pendência.
- **Lote:** o comando novo funcionou, mas o custo não caiu (294 s e 127 mil tokens, contra 285 s e 118 mil). O custo vem da análise de cada relato.
- **Variação entre execuções, com a mesma matriz:**
  - 9 de 15 ocorrências tiveram pontuação idêntica.
  - O nível mudou em 2: dado sensível, alta 70 → crítica 75; esgoto, baixa 27 → média 32.
  - As diferenças vêm de fatores inferidos e são tratadas na proposta de calibração (âncoras A2 a A4).
- **Escola sem rampa e semáforos:** a pontuação não mudou (52 e 33). A causa está na matriz, não na execução.
- **Onde ver:**
  - `.claude/skills/ecorastro-analisador-workspace/revisao-iteration-2.html`: visualizador, com a iteração 1 como saída anterior;
  - `iteration-2/benchmark.md` e `iteration-2/benchmark.json`, com as notas do analista;
  - `grading.json` de cada execução.

### Pendências de decisão

1. Calibração da matriz (`docs/proposta-calibracao-matriz.md`): âncoras A1 a A4, regras `ex06`/`ex07`, tratamento do esgoto, natureza da escola sem rampa e número da versão.
2. Reidentificação pela menção coletiva (`docs/questao-privacidade-reidentificacao.md`): recomendação 2 + 3, e retenção do `texto_original` com dado sensível sem relação com o problema.
3. Critério 04 do caso `dado-sensivel-terceiro`.
4. Custo dos lotes: avaliar processar relatos em paralelo ou um formato de resposta mais curto.

## 0.1.0 (Etapas 1 a 5)

Versão inicial: taxonomia 1.0.0, matriz 1.0.0, schema 1.0.0, 3 scripts, 97 testes e 10 casos de avaliação (iteração 1: 69/70 com a skill, 12/70 sem).
