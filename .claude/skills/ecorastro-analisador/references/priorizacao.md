# Matriz de priorização — EcoRastro AI

**versao_matriz_prioridade: 1.1.0**

## Aviso sobre a natureza desta escala

Esta é uma **escala heurística de triagem operacional**. Ela serve para ordenar uma fila de atendimento com critérios explícitos e auditáveis. Os pesos e limites foram definidos por julgamento de projeto e **não foram validados cientificamente nem calibrados com dados reais**.

Ela não substitui avaliação técnica (engenharia, Defesa Civil, vigilância sanitária) nem o acionamento de serviços de emergência. Relatórios e interfaces devem chamar o resultado de "prioridade de triagem", nunca de "nível de risco" ou "avaliação de risco".

**Status desta versão:** os pesos e faixas são **provisórios**. Foram aprovados para a fase de testes e serão avaliados e ajustados com base nos resultados. Quando houver dados reais de atendimento, devem ser revisados novamente. Qualquer mudança gera uma nova `versao_matriz_prioridade`.

**Versão 1.1.0 (Etapa 6, complemento).** Pesos e faixas iguais aos da 1.0.0. Mudaram as âncoras de três fatores (A1 risco à saúde, A2 falha do próprio serviço essencial, A3 acesso à moradia só quando bloqueado, A4 abrangência de serviços prestados por rua) e entraram duas regras de exceção (`ex06`, `ex07`). A compatibilidade com análises feitas na 1.0.0 está em `docs/compatibilidade-versoes.md`.

## Sumário

1. [Visão geral do cálculo](#1-visão-geral-do-cálculo)
2. [Os seis fatores](#2-os-seis-fatores)
3. [Ausente não é zero](#3-ausente-não-é-zero)
4. [Fórmula, piso, teto e completude](#4-fórmula-piso-teto-e-completude)
5. [Faixas de nível](#5-faixas-de-nível)
6. [Regras de exceção](#6-regras-de-exceção)
7. [Situações especiais](#7-situações-especiais)
8. [Justificativa rastreável](#8-justificativa-rastreável)
9. [Exemplos calculados](#9-exemplos-calculados)
10. [Versionamento e calibração](#10-versionamento-e-calibração)

---

## 1. Visão geral do cálculo

A prioridade é calculada **por ocorrência**, depois da classificação (`categorias.md`).

1. Avaliar cada um dos 6 fatores com nota 0 a 3, ou marcar como `ausente`.
2. Registrar para cada fator o status (`relatado`, `inferido`, `ausente`), a evidência literal quando houver e o raciocínio.
3. Calcular `pontuacao` (piso), `pontuacao_teto` e `completude` (seção 4).
4. Converter a pontuação em `nivel_base` (seção 5).
5. Aplicar as regras de exceção na ordem definida para obter `nivel` (seção 6).
6. Calcular `nivel_teto` e decidir pendências.
7. Escrever a `justificativa` (seção 8).

A divisão de trabalho é intencional. O julgamento qualitativo fica na nota de cada fator, onde é visível e contestável. A aritmética é fixa e reproduzível, e pode ser executada por script e, no futuro, pelo Django com a mesma fórmula.

## 2. Os seis fatores

Os pesos somam 100.

| Código | Peso | Pergunta |
|---|---|---|
| `risco_integridade_fisica` | 30 | Alguém pode se machucar? |
| `abrangencia` | 20 | Quantas pessoas ou que área é afetada? |
| `vulnerabilidade_afetados` | 15 | Atinge grupos mais vulneráveis? |
| `impacto_servico_essencial` | 15 | Impede ou dificulta acesso a serviço essencial? |
| `persistencia` | 10 | Há quanto tempo o problema existe ou se repete? |
| `risco_agravamento` | 10 | O problema tende a piorar ou a causar outro dano? |

Por que estes pesos: o dano físico a pessoas é o critério mais difícil de reverter, então pesa mais. Abrangência vem em seguida porque define quantas pessoas a solução beneficia. Persistência e agravamento pesam menos porque, sozinhos, não indicam gravidade: um problema antigo e inofensivo não deve passar à frente de um recente e perigoso.

### 2.1 `risco_integridade_fisica` (peso 30)

| Nota | Âncora | Exemplos |
|---|---|---|
Desde a 1.1.0, o fator mede o risco de **lesão** e também o risco à **saúde** (A1).

| Nota | Âncora | Exemplos |
|---|---|---|
| 0 | Nenhum risco físico ou à saúde plausível. | Pichação, atraso de ônibus, falta de vaga em creche. |
| 1 | Risco baixo: desconforto, lesão improvável ou incômodo sanitário pontual. | Calçada com pequeno desnível; poste apagado sem outro agravante; lixo ensacado acumulado há poucos dias. |
| 2 | Risco **potencial** plausível de lesão ou de agravo à saúde para quem passa, usa ou mora perto. | Buraco em via; bueiro sem tampa; ciclistas dividindo pista com ônibus; esgoto a céu aberto na via; lixo em decomposição; água parada com foco de mosquito relatado. |
| 3 | Dano **já ocorrido** (lesão ou adoecimento atribuído ao problema), ou risco elevado de lesão grave ou morte. | "Um motoqueiro caiu"; fio soltando faísca; barranco cedendo atrás de casas; "as crianças da rua ficaram doentes"; esgoto chegando à água de consumo; animal peçonhento em área de circulação. |

#### Risco potencial × dano ocorrido

| Situação | Nota | Status | Efeito |
|---|---|---|---|
| Risco potencial deduzido da natureza do problema ("esgoto na via expõe moradores a contaminação") | até 2 | `inferido` | Soma pontos. |
| Risco potencial descrito no relato ("as crianças brincam nessa água") | até 2 | `relatado` | Soma pontos; com vulnerabilidade ≥ 2, aciona `ex03`. |
| Dano ocorrido descrito no relato ("caiu e se machucou", "ficaram doentes") | 3 | `relatado` | Aciona `ex02` (mínimo `alta`). |
| Dano comprovado por vistoria, laudo ou registro oficial | 3 | `verificado` | Só o sistema ou um revisor atribui. |

Duas confusões a evitar:
- tratar risco potencial como dano: "pode causar doença" é nota 2, não 3;
- chamar dano relatado de comprovado: o relato não foi verificado em campo. Na justificativa, escreva "relatado".

### 2.2 `abrangencia` (peso 20)

| Nota | Âncora | Exemplos |
|---|---|---|
| 0 | Uma pessoa ou um imóvel. | Calçada em frente a uma única casa, sem fluxo relevante. |
| 1 | Poucos imóveis ou um trecho de rua local. | Um poste apagado; um buraco numa rua residencial. |
| 2 | Rua inteira, quarteirões, equipamento de bairro ou via de grande circulação. | Semáforo em cruzamento de avenida; praça do bairro. |
| 3 | Bairro inteiro, vários bairros ou serviço que atende grande população. | "O bairro todo está sem água"; linha de ônibus suspensa. |

**Serviços prestados por rua** (A4): coleta de lixo, varrição, iluminação de um trecho contínuo. "A coleta não passa na rua", "a rua toda está escura" valem 2 (rua inteira). Um ponto isolado (um poste, uma lixeira) continua 1.

### 2.3 `vulnerabilidade_afetados` (peso 15)

Grupos considerados: crianças, idosos, gestantes, pessoas com deficiência ou mobilidade reduzida, pessoas em situação de rua, pacientes.

| Nota | Âncora |
|---|---|
| 0 | O relato indica que o local não tem esse público. (Raro: em geral o texto é silencioso, e então o fator é `ausente`.) |
| 1 | Presença eventual desses grupos. |
| 2 | Local frequentado regularmente por esses grupos: escola, creche, unidade de saúde, instituição de longa permanência. |
| 3 | Grupo vulnerável **diretamente** afetado e mencionado. "As crianças estão saindo da escola agora"; "o cadeirante não consegue passar". |

Os ajustes da 1.1.0 não mudam este fator. A condição de uma pessoa identificável continua sustentando a nota, com o tratamento de privacidade da seção 11.1 de `categorias.md`.

### 2.4 `impacto_servico_essencial` (peso 15)

Serviços essenciais: água, esgoto, energia, saúde, educação, coleta de resíduos, transporte coletivo e o acesso físico a moradia ou trabalho.

| Nota | Âncora |
|---|---|
| 0 | Não afeta serviço essencial. |
| 1 | Dificulta o acesso, mas há alternativa. |
| 2 | Interrompe parcialmente, ou interrompe para parte da população. |
| 3 | Interrompe totalmente, sem alternativa razoável. |

**Quando a ocorrência é a própria falha do serviço** (A2): esgoto vazando ou extravasando, coleta que não passa, falta de água, ônibus que não circula, falta de energia. O fator mede essa falha:
- 2: falha parcial ou localizada (um trecho, uma rua);
- 3: falha total no local, sem alternativa razoável (o bairro sem água, a linha suspensa).

A falha está descrita no relato, então o fator não fica `ausente` por falta de outra informação.

**Acesso físico à moradia ou ao trabalho** (A3): vale 2 ou mais só quando o relato diz que o acesso está **bloqueado ou impedido** ("não consigo sair de casa", "o entulho fechou a entrada"). Dificuldade, mesmo com quedas, vale 1. O perigo da queda já é medido em `risco_integridade_fisica`.

**Acessibilidade.** Quando uma barreira impede uma pessoa com deficiência ou mobilidade reduzida de entrar num serviço essencial (escola, unidade de saúde, transporte), ou de sair de casa, é acesso **impedido** para ela: 2 se afeta parte do público, 3 se não há alternativa. A3 não reduz essas situações; "não consegue entrar" é impedimento, não dificuldade.

### 2.5 `persistencia` (peso 10)

| Nota | Âncora |
|---|---|
| 0 | Surgiu há menos de 24 horas, ou é a primeira vez. |
| 1 | Dias até cerca de 2 semanas, ou indícios de que já existe há algum tempo sem duração informada. |
| 2 | Semanas a 3 meses. |
| 3 | Mais de 3 meses, ou recorrente com reclamações anteriores não atendidas. |

### 2.6 `risco_agravamento` (peso 10)

| Nota | Âncora |
|---|---|
| 0 | Condição estável, sem tendência de piora pela própria natureza. |
| 1 | Pode piorar lentamente. |
| 2 | Piora relatada ou previsível em dias ou semanas (chuva, erosão, uso intenso). |
| 3 | Piora rápida, em horas, ou risco de desencadear outro dano (curto-circuito, desabamento, contaminação de água). |

## 3. Ausente não é zero

Esta distinção é o ponto mais importante da matriz. Zero é uma **afirmação**: "avaliamos e não há impacto". Ausente é uma **lacuna**: "o relato não permite avaliar".

| Situação | Registro |
|---|---|
| O texto diz que não há impacto ("ninguém passa por ali, é uma rua sem saída") | nota 0, `relatado`, com evidência |
| A natureza do problema permite afirmar que não há impacto (pichação não fere ninguém) | nota 0, `inferido`, com raciocínio |
| O texto não fala do assunto e a natureza do problema não permite concluir | `nota: null`, `ausente`, raciocínio dizendo o que falta |

Status do fator:
- `relatado`: o fato que sustenta a nota está escrito no relato. A `evidencia` é o trecho literal (do texto mascarado).
- `inferido`: a nota depende de uma dedução além do que está escrito. O `raciocinio` explica a dedução; a `evidencia` é opcional e, se houver, continua literal.
- `ausente`: `nota` é `null`; o `raciocinio` diz o que seria preciso saber.
- `verificado`: reservado ao sistema ou a revisor humano, com bloco `verificacao`. A skill nunca atribui.

Na dúvida entre nota baixa inferida e ausente, prefira **ausente**. A ausência fica visível no teto e gera pendência. Uma nota baixa inventada esconde a lacuna e pode deixar um problema grave no fim da fila.

## 4. Fórmula, piso, teto e completude

Com nᵢ ∈ {0, 1, 2, 3} e pesos wᵢ:

```
soma(n) = 30·n_risco + 20·n_abrangencia + 15·n_vulnerabilidade
        + 15·n_servico + 10·n_persistencia + 10·n_agravamento

pontuacao       = arredonda( soma(n com ausentes = 0) / 3 )
pontuacao_teto  = arredonda( soma(n com ausentes = 3) / 3 )
completude      = (fatores não ausentes) / 6, com 2 casas decimais
```

- `arredonda` é o inteiro mais próximo, com 0,5 arredondado para cima. A soma é dividida por 3 antes de arredondar, então o máximo é exatamente 100.
- `pontuacao` é o **piso**: o mínimo que os dados disponíveis sustentam. É ela que define o nível.
- `pontuacao_teto` é o **máximo possível** se todos os fatores ausentes fossem confirmados no grau mais alto. Mostra quanto a falta de informação pode estar escondendo.
- Quando não há fatores ausentes, piso e teto são iguais.

O piso define o nível porque a matriz só pode afirmar o que foi relatado ou inferido com base. As regras de exceção (seção 6) evitam que lacunas deixem casos evidentemente graves com nível baixo.

## 5. Faixas de nível

| Nível | Pontuação | Leitura operacional |
|---|---|---|
| `baixa` | 0–29 | Atendimento na rotina. |
| `media` | 30–54 | Programar atendimento. |
| `alta` | 55–74 | Atendimento preferencial. |
| `critica` | 75–100 | Atendimento imediato; avaliar acionamento de emergência. |

`nivel_base` = faixa de `pontuacao`.

## 6. Regras de exceção

As regras cobrem situações que a soma ponderada trata mal: perigos imediatos com poucos fatores informados, danos já ocorridos e o limite natural das necessidades de infraestrutura. Toda regra cuja condição foi atendida entra em `regras_aplicadas`, mesmo que não altere o nível. Assim fica registrado que ela foi considerada.

| Código | Condição | Efeito |
|---|---|---|
| `ex01_risco_iminente` | Perigo **atual**, **concreto**, **relatado** (não inferido) e com potencial de lesão grave ou morte. | `nivel = critica`. Preencher `alerta_emergencia`. Pendência `revisao_humana_recomendada`. |
| `ex02_risco_fisico_grave_relatado` | `risco_integridade_fisica` = 3 com status `relatado`. | Nível mínimo `alta`. |
| `ex03_risco_com_vulnerabilidade` | `risco_integridade_fisica` ≥ 2 **e** `vulnerabilidade_afetados` ≥ 2 (ambos não ausentes). | Nível mínimo `alta`. |
| `ex04_teto_necessidade_infraestrutura` | `natureza` = `necessidade_infraestrutura` e `ex01` não se aplica. | Nível máximo `alta`. |
| `ex05_informacao_insuficiente` | `completude` < 0,67 (menos de 4 dos 6 fatores avaliados). | `pontuacao_provisoria = true`. Pendências `complementar_dados_prioridade` e `revisao_humana_recomendada`. Não altera o nível. |
| `ex06_falha_controle_trafego` | Semáforo **inoperante** relatado (apagado, desligado, piscando em amarelo ou sem funcionar), subcategoria `mob_semaforo`, `abrangencia` ≥ 2 e `risco_integridade_fisica` ≥ 2, os dois com evidência literal. | Nível mínimo `alta`. |
| `ex07_barreira_acesso_servico_essencial` | `vulnerabilidade_afetados` = 3 **e** `impacto_servico_essencial` ≥ 2, os dois com status `relatado`. | Nível mínimo `alta`. |

**Ordem de aplicação**:
1. `nivel_base`.
2. Mínimos: `ex02`, `ex03`, `ex06`, `ex07`.
3. Máximo: `ex04`.
4. `ex01`, que prevalece sobre todas as outras.
5. Marcação `ex05`.

Se `ex02` e `ex04` coincidirem ("falta faixa de pedestre aqui, já atropelaram duas pessoas"), mínimo e máximo coincidem e o resultado é `alta`. O mesmo vale para `ex07` numa necessidade de infraestrutura.

Como `ex01`, a regra `ex06` é uma **afirmação da análise**: a análise a coloca em `regras_aplicadas` quando o relato descreve o semáforo inoperante, e o script confere as demais condições. Se faltar alguma, o script recusa a entrada; a análise deve retirar a regra ou corrigir a avaliação, nunca forçar. As outras regras são calculadas pelo script.

### 6.1 O que conta como risco iminente (`ex01`)

Conta, quando relatado:
- fio energizado caído, faiscando ou ao alcance de pessoas;
- fogo ativo;
- estrutura, encosta ou árvore cedendo agora;
- cheiro forte de gás;
- alagamento subindo com pessoas ilhadas;
- pessoa ferida no local;
- crime em andamento.

Não conta:
- buraco antigo onde já houve acidente (isso é `ex02`);
- "um dia isso vai matar alguém" (previsão genérica, não perigo atual);
- risco que só a análise deduziu sem descrição concreta no texto.

Serviços para `alerta_emergencia.servicos`, conforme o caso:

| Situação | Serviços |
|---|---|
| Fio ou equipamento elétrico | `emergencia_concessionaria_energia`, `bombeiros_193` |
| Incêndio, gás | `bombeiros_193` |
| Deslizamento, desabamento, enchente com pessoas em risco | `defesa_civil_199`, `bombeiros_193` |
| Pessoa ferida ou passando mal | `samu_192` |
| Crime em andamento | `policia_190` |
| Rompimento de adutora ou esgoto com risco | `emergencia_concessionaria_saneamento` |

A skill **orienta** o acionamento; ela não aciona nenhum serviço.

### 6.2 `nivel_teto`

```
nivel_teto = faixa(pontuacao_teto)
se ex04 se aplica: nivel_teto = mínimo(nivel_teto, alta)
nivel_teto = máximo(nivel_teto, nivel)
```

Se `nivel_teto` for maior que `nivel`, adicione a pendência `complementar_dados_prioridade`: obter as informações que faltam pode mudar a prioridade.

### 6.3 Evidência suficiente para `ex06` e `ex07`

As duas regras elevam o nível sem mudar a pontuação. Por isso só valem com base no texto.

| Regra | Conta | Não conta |
|---|---|---|
| `ex06` | "Semáforo apagado no cruzamento da Av. Paraná com a Rua 3"; "o sinal da avenida está piscando amarelo desde cedo" | Semáforo com tempo curto ou dessincronizado (funciona; use os fatores normais); semáforo apagado em rua local (abrangência 1); cruzamento deduzido sem nome de via nem referência no relato |
| `ex07` | "Um aluno cadeirante não consegue entrar na escola"; "os idosos não conseguem subir no ônibus, o elevador está quebrado" | Vulnerabilidade deduzida ("deve passar idoso ali"); "é difícil entrar" (dificuldade vale 1); barreira em local que não presta serviço essencial |

## 7. Situações especiais

- **Obras de adequação** (problema existente com `requer_obra_adequacao = true`, como a escola sem rampa): o equipamento existe, mas não cumpre uma exigência obrigatória. Não se aplica o teto `ex04`, e o encaminhamento vai para o responsável pelo equipamento como obra de adequação.
- **Necessidades de infraestrutura** usam os mesmos fatores, com teto `alta` (`ex04`). Elas seguem para planejamento, e o nível `critica` é reservado a respostas imediatas. Uma necessidade cuja ausência causa perigo imediato relatado continua podendo ser `critica` via `ex01`.
- **Alegações de irregularidade** não somam pontos. Avalie apenas os efeitos físicos descritos. "A fábrica joga efluente no córrego" pontua pela poluição do córrego, não pela acusação.
- **Várias ocorrências no mesmo relato** têm prioridades independentes. O relatório pode destacar a maior, mas não soma.
- **Relatos repetidos**: a persistência vem apenas do texto ("já reclamei três vezes"). Contagens de relatos semelhantes poderão, no futuro, ser registradas pelo Django como `verificado`.
- **Mesma evidência em dois fatores** é permitida quando o trecho sustenta os dois ("faísca no chão molhado" sustenta risco físico e agravamento). O raciocínio de cada fator deve explicar o seu uso.

## 8. Justificativa rastreável

A `justificativa` deve permitir que uma pessoa refaça o cálculo sem abrir o JSON. Ela precisa citar:

1. nível final e pontuação, indicando se é provisória;
2. cada fator com nota maior que zero: nota, status e evidência curta ou raciocínio;
3. os fatores ausentes;
4. as regras que alteraram o nível (de qual para qual);
5. o teto, quando diferente do nível.

Modelo:

> Prioridade **alta** (47 pts; faixa base média). risco_integridade_fisica 3 (relatado: "um motoqueiro caiu ali e se machucou"); risco_agravamento 2 (relatado: "com a chuva o buraco tá ficando cada vez maior"); abrangencia 1 (inferido: via pública, fluxo não informado); persistencia 1 (inferido: o crescimento indica que existe há algum tempo). Ausentes: vulnerabilidade_afetados, impacto_servico_essencial. ex02 elevou de média para alta. Pode chegar a crítica (77 pts) se os fatores ausentes forem confirmados no grau máximo.

## 9. Exemplos calculados

Os exemplos são fictícios e servem de calibração para a análise e de casos de teste para os scripts.

### 9.1 Buraco com acidente (problema existente)

> "Tem um buraco enorme na Rua das Flores, perto do nº 120. Ontem um motoqueiro caiu ali e se machucou. Com a chuva o buraco tá ficando cada vez maior."

| Fator | Nota | Status | Base |
|---|---|---|---|
| risco_integridade_fisica | 3 | relatado | "um motoqueiro caiu ali e se machucou" |
| abrangencia | 1 | inferido | Via pública; fluxo não informado. |
| vulnerabilidade_afetados | — | ausente | O relato não diz quem circula no local. |
| impacto_servico_essencial | — | ausente | Não diz se o buraco bloqueia acesso. |
| persistencia | 1 | inferido | "tá ficando cada vez maior" indica que já existe há algum tempo. |
| risco_agravamento | 2 | relatado | "Com a chuva o buraco tá ficando cada vez maior" |

- soma = 90 + 20 + 0 + 0 + 10 + 20 = 140 → **pontuacao 47** (nível base `media`)
- teto: 140 + 45 + 45 = 230 → **77**
- completude 0,67
- `ex02` → **nivel `alta`**; `nivel_teto` = `critica` → pendência `complementar_dados_prioridade`

### 9.2 Fio elétrico caído na saída da escola (risco iminente)

> "Caiu um fio do poste na esquina da Av. Brasil com a Rua 7, tá soltando faísca no chão molhado e as crianças tão saindo da escola agora."

| Fator | Nota | Status | Base |
|---|---|---|---|
| risco_integridade_fisica | 3 | relatado | "tá soltando faísca no chão molhado" |
| abrangencia | 2 | inferido | Esquina de avenida em horário de saída escolar. |
| vulnerabilidade_afetados | 3 | relatado | "as crianças tão saindo da escola agora" |
| impacto_servico_essencial | — | ausente | Não diz se há falta de energia. |
| persistencia | — | ausente | Não diz quando o fio caiu. |
| risco_agravamento | 3 | relatado | "soltando faísca no chão molhado" |

- soma = 90 + 40 + 45 + 0 + 0 + 30 = 205 → **pontuacao 68** (nível base `alta`)
- teto: 205 + 45 + 30 = 280 → **93**
- completude 0,67
- `ex02` e `ex03` (mínimo alta), `ex01` → **nivel `critica`**
- `alerta_emergencia`: `emergencia_concessionaria_energia`, `bombeiros_193`

### 9.3 Pedido de ciclovia (necessidade de infraestrutura)

> "Seria muito bom ter uma ciclovia na Avenida Central. Muita gente vai de bicicleta pro trabalho e tem que dividir a pista com os carros e ônibus."

| Fator | Nota | Status | Base |
|---|---|---|---|
| risco_integridade_fisica | 2 | inferido | Dividir a pista com ônibus expõe ciclistas a colisão. Evidência: "tem que dividir a pista com os carros e ônibus". |
| abrangencia | 2 | relatado | "Muita gente vai de bicicleta pro trabalho" |
| vulnerabilidade_afetados | — | ausente | Não menciona o público. |
| impacto_servico_essencial | 1 | inferido | Afeta o deslocamento ao trabalho, mas há alternativa. |
| persistencia | — | ausente | Não informada. |
| risco_agravamento | 0 | inferido | A falta de ciclovia é uma condição estável. |

- soma = 60 + 40 + 0 + 15 + 0 + 0 = 115 → **pontuacao 38** (`media`)
- teto: 115 + 45 + 30 = 190 → 63 (`alta`)
- completude 0,67
- `ex04` aplicada (sem efeito, teto alta) → **nivel `media`**; `nivel_teto` = `alta` → pendência `complementar_dados_prioridade`

### 9.4 Relato curto (prioridade provisória)

> "Tem um poste apagado na Rua Ipê."

| Fator | Nota | Status | Base |
|---|---|---|---|
| risco_integridade_fisica | 1 | inferido | Trecho escuro aumenta o risco de queda à noite. Evidência: "poste apagado". |
| abrangencia | 1 | inferido | Um poste ilumina um trecho de rua. |
| vulnerabilidade_afetados | — | ausente | — |
| impacto_servico_essencial | — | ausente | — |
| persistencia | — | ausente | Não diz desde quando. |
| risco_agravamento | 0 | inferido | Lâmpada apagada não piora sozinha. |

- soma = 30 + 20 = 50 → **pontuacao 17** (`baixa`)
- teto: 50 + 45 + 45 + 30 = 170 → 57 (`alta`)
- completude 0,50 → `ex05`: **`baixa` provisória**; pendências `complementar_dados_prioridade`, `revisao_humana_recomendada` (e `localizacao_imprecisa`, pela classificação)

### 9.5 Esgoto vazando na via (A1 e A2)

> "Tem esgoto vazando na Rua Bahia há 2 semanas, o cheiro está insuportável."

| Fator | Nota | Status | Base |
|---|---|---|---|
| risco_integridade_fisica | 2 | inferido | Risco potencial à saúde (A1): exposição contínua a esgoto na via. Evidência: "esgoto vazando na Rua Bahia". Não há adoecimento relatado, então não é 3. |
| abrangencia | 1 | inferido | Trecho de rua; extensão não informada. |
| vulnerabilidade_afetados | — | ausente | O relato não diz quem circula ou mora no trecho. |
| impacto_servico_essencial | 2 | relatado | A ocorrência é a falha localizada do próprio serviço de esgoto (A2): "esgoto vazando". |
| persistencia | 1 | relatado | "há 2 semanas" (limite entre 1 e 2; na dúvida, a nota menor). |
| risco_agravamento | 2 | inferido | Vazamento tende a aumentar e a se espalhar. |

- soma = 60 + 20 + 0 + 30 + 10 + 20 = 140 → **pontuacao 47** (`media`)
- teto: 140 + 45 = 185 → 62 (`alta`); completude 0,83
- nenhuma regra → **nivel `media`**; pendência `complementar_dados_prioridade`
- Sobe para `alta` só com evidência: público vulnerável relatado no local (`ex03`, com risco 2 e vulnerabilidade ≥ 2) ou adoecimento e esgoto na água de consumo relatados (risco 3 relatado, `ex02`).

### 9.6 Semáforo apagado em cruzamento de avenida (`ex06`)

> "Semáforo apagado na Av. Paraná x Rua 3 desde manhã, quase vi uma batida."

| Fator | Nota | Status | Base |
|---|---|---|---|
| risco_integridade_fisica | 2 | relatado | "quase vi uma batida" (quase-acidente: risco, não dano) |
| abrangencia | 2 | inferido | Cruzamento de avenida. Evidência: "Av. Paraná x Rua 3". |
| vulnerabilidade_afetados | — | ausente | Não menciona o público. |
| impacto_servico_essencial | — | ausente | Não diz se afeta transporte coletivo. |
| persistencia | 0 | relatado | "desde manhã" |
| risco_agravamento | 0 | inferido | O semáforo apagado não piora sozinho; o risco é constante enquanto durar. |

- soma = 60 + 40 = 100 → **pontuacao 33** (`media`); teto 190 → 63 (`alta`); completude 0,67
- a análise registra `ex06` (semáforo apagado relatado); o script confere `mob_semaforo`, abrangência 2 e risco 2 com evidência → **nivel `alta`**

### 9.7 Escola sem rampa (`ex07`, obra de adequação)

> "A escola municipal do bairro Santa Luzia não tem rampa na entrada, as mães com carrinho de bebê e um aluno cadeirante não conseguem entrar."

Natureza `problema_existente`, com `requer_obra_adequacao = true`: a escola existe e não cumpre a acessibilidade obrigatória (seção 5 de `categorias.md`).

| Fator | Nota | Status | Base |
|---|---|---|---|
| risco_integridade_fisica | 1 | inferido | Sem rampa, há risco baixo de queda ao tentar entrar. |
| abrangencia | 2 | inferido | Equipamento de bairro. |
| vulnerabilidade_afetados | 3 | relatado | "um aluno cadeirante" (versão interna; na pública, `[DADO_SENSIVEL]`) |
| impacto_servico_essencial | 2 | relatado | "não conseguem entrar": educação impedida para parte do público. |
| persistencia | 1 | inferido | Falta estrutural, sem duração informada. |
| risco_agravamento | 0 | inferido | Condição estável. |

- soma = 30 + 40 + 45 + 30 + 10 + 0 = 155 → **pontuacao 52** (`media`); completude 1,00
- `ex07` (vulnerabilidade 3 e serviço 2, ambos relatados) → **nivel `alta`**; sem `ex04`, porque não é necessidade de infraestrutura

## 10. Versionamento e calibração

- Qualquer mudança em peso, âncora, faixa ou regra gera nova `versao_matriz_prioridade` (semver: mudança de faixa ou peso → versão maior; ajuste de âncora ou exemplo → versão menor).
- Cada análise grava a versão usada, para que o Django possa recalcular ocorrências antigas sem reler o relato: as notas e os status dos fatores ficam armazenados e só a aritmética muda.
- Histórico: 1.0.0 (Etapas 1 a 6); 1.1.0 (âncoras A1 a A4 e regras `ex06`/`ex07`; pesos e faixas iguais). Análises das duas versões não são diretamente comparáveis, porque as âncoras mudam as notas; veja `docs/compatibilidade-versoes.md`.
- Sinais de que a matriz precisa de calibração: muitos casos `critica` sem `ex01`; necessidades acumuladas no teto; revisores humanos alterando o nível com frequência na mesma direção.
